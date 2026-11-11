"""Correo: resumen diario para el candidato y correos de postulación con la hoja de vida adjunta."""
import html
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

DOMINIOS_IGNORADOS = re.compile(
    r"linkedin|computrabajo|elempleo|getonbrd|getonboard|remotive|remoteok|himalayas|jobicy|workingnomads|"
    r"weworkremotely|rocketship|arc\.dev|hiring\.lat|workana|example|sentry|wixpress|googleusercontent|"
    r"no-?reply|privacy|privacidad|datos\.personales|habeas|unsubscribe|soporte|support@|abuse", re.I)
CONTEXTO_POSTULACION = re.compile(
    r"hoja de vida|\bh\.?v\b|\bcv\b|curr[ií]cul|resume|résumé|postul|aplica|apply|applications?|env[ií]a|send|interesad|interested",
    re.I)


def extraer_correo(texto: str) -> str | None:
    """Correo al que la oferta pide enviar la hoja de vida. Solo si el texto alrededor lo dice:
    un correo suelto (privacidad, soporte) nunca se toma como canal de postulación."""
    for m in re.finditer(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", texto or ""):
        correo = m.group(0).rstrip(".")
        if DOMINIOS_IGNORADOS.search(correo):
            continue
        alrededor = texto[max(0, m.start() - 120): m.end() + 60]
        if CONTEXTO_POSTULACION.search(alrededor):
            return correo.lower()
    return None


def _mensaje(remitente, para, asunto, cuerpo, html_=False, adjuntos=(), nombre_remitente=None):
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = f"{nombre_remitente} <{remitente}>" if nombre_remitente else remitente
    msg["To"] = para
    if html_:
        msg.set_content(re.sub(r"<[^>]+>", " ", cuerpo))
        msg.add_alternative(cuerpo, subtype="html")
    else:
        msg.set_content(cuerpo)
    for ruta, nombre in adjuntos:
        msg.add_attachment(Path(ruta).read_bytes(), maintype="application", subtype="pdf", filename=nombre)
    return msg


def enviar(gmail: dict, msg: EmailMessage):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(gmail["gmail"], gmail["contrasena_aplicacion"].replace(" ", ""))
        s.send_message(msg)


def postulacion(gmail: dict | None, para: str, asunto: str, carta: str, cv: str, nombre: str, salida: Path | None):
    """Envía la postulación. Con `salida` (modo prueba) solo escribe el .eml y no envía nada."""
    remitente = gmail["gmail"] if gmail else "candidato@ejemplo.invalid"
    msg = _mensaje(remitente, para, asunto, carta, adjuntos=[(cv, f"CV - {nombre}.pdf")], nombre_remitente=nombre)
    if salida is not None:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_bytes(bytes(msg))
        return "simulada"
    if not gmail:
        raise RuntimeError("Gmail no está configurado")
    enviar(gmail, msg)
    return "enviada"


def resumen(gmail: dict, asunto: str, cuerpo_html: str):
    destino = gmail.get("destinatario") or gmail["gmail"]
    enviar(gmail, _mensaje(gmail["gmail"], destino, asunto, cuerpo_html, html_=True, nombre_remitente="Agente de empleo"))


# --- HTML del resumen diario ------------------------------------------------------

def _meta(o):
    bits = [o.get("empresa"), o.get("salario"), o.get("fuente")]
    d = o.get("dias")
    if d is not None:
        bits.append("publicada hoy" if d == 0 else "ayer" if d == 1 else f"hace {d} días")
    return " · ".join(html.escape(str(b)) for b in bits if b)


def resumen_html(nombre, priorizadas, cola, revisadas, n_portales, metricas, modo, prueba, descartes):
    e = html.escape
    empleos = [o for o in priorizadas if not o.get("freelance")]
    freelance = [o for o in priorizadas if o.get("freelance")]

    def item(o):
        ev = o.get("eval") or {}
        razon = ev.get("razon") or o.get("por_que", "")
        etiqueta = "LLM" if ev.get("fuente_eval") == "llm" else "reglas"
        brechas = ev.get("brechas") or []
        extra = f"<br><span style='color:#80868b;font-size:13px'>Te falta: {e(', '.join(brechas[:3]))}</span>" if brechas else ""
        return (f"<li style='margin:0 0 16px'><a href='{e(o['url'])}' style='color:#1a4fb4;font-weight:600;text-decoration:none'>"
                f"{e(o['titulo'])}</a> <span style='color:#5f6368;font-size:13px'>({o['puntaje']}/100, {etiqueta})</span><br>"
                f"<span style='color:#5f6368;font-size:13px'>{_meta(o)}</span><br><span style='font-size:14px'>{e(razon)}</span>{extra}</li>")

    bloque_cola = ""
    if cola:
        filas = "".join(
            f"<li style='margin:0 0 10px'><b>#{c['id']}</b> {e(c['titulo'])} · {e(c['empresa'] or '')} · "
            f"{'por correo a ' + e(c['correo']) if c['correo'] else 'por el portal (manual)'}"
            f"{' · <b style=\"color:#b3261e\">revisar a mano</b>' if c['requiere_revision'] else ''}</li>" for c in cola)
        if modo == "aprobacion":
            instr = ("Las cartas están en <code>data/cartas</code> (puedes editarlas). Para enviar las que quieras: "
                     "<code>python main.py --aprobar 1,3</code>, todas: <code>--aprobar todas</code>, ninguna: <code>--aprobar ninguna</code>.")
        else:
            instr = "Modo automático: se envían solas las que tienen correo de postulación y pasaron la revisión."
        bloque_cola = (f"<p style='margin:26px 0 4px;font-size:15px;font-weight:600'>Postulaciones preparadas</p>"
                       f"<p style='margin:0 0 12px;color:#5f6368;font-size:13px'>{instr}</p><ol style='margin:0;padding-left:20px;list-style:none'>{filas}</ol>")

    tokens = sum(m.get("tokens", 0) for m in metricas)
    por_nodo = {}
    for m in metricas:
        n = por_nodo.setdefault(m["nodo"], [0, 0.0, 0])
        n[0] += 1; n[1] += m["seg"]; n[2] += m.get("tokens", 0)
    filas_m = "".join(f"<tr><td>{e(k)}</td><td align=right>{v[0]}</td><td align=right>{v[1]:.1f} s</td><td align=right>{v[2]:,}</td></tr>"
                      for k, v in por_nodo.items())
    apertura = (f"Revisé {revisadas} ofertas en {n_portales} portales; {len(empleos)} pasaron los filtros."
                if empleos else "Hoy no apareció ningún empleo nuevo que cumpla los filtros.")
    aviso = "<p style='color:#b3261e'><b>MODO PRUEBA:</b> no se envió ninguna postulación.</p>" if prueba else ""
    lista_f = "".join(f"<li><a href='{e(o['url'])}'>{e(o['titulo'])}</a></li>" for o in freelance[:10])
    return f"""<!doctype html><html><body style="margin:0;background:#fff">
<div style="max-width:640px;margin:0 auto;padding:24px 18px;font-family:'Segoe UI',Roboto,Arial,sans-serif;font-size:15px;line-height:1.5;color:#202124">
<p>Hola {e(nombre)},</p>{aviso}<p>{apertura}</p>
{bloque_cola}
<p style='margin:26px 0 4px;font-size:15px;font-weight:600'>Ofertas priorizadas</p>
<ol style='margin:0;padding-left:20px'>{''.join(item(o) for o in empleos[:25])}</ol>
{f"<p style='margin:20px 0 4px;font-weight:600'>Freelance</p><ul>{lista_f}</ul>" if lista_f else ''}
<p style="margin:30px 0 6px;padding-top:14px;border-top:1px solid #e8eaed;color:#80868b;font-size:12px">
Descartes: {e(', '.join(f'{k}: {v}' for k, v in descartes.items()))}. Tokens usados: {tokens:,}.</p>
<table style="color:#80868b;font-size:12px;border-collapse:collapse" cellpadding=3>
<tr><th align=left>Nodo</th><th>Llamadas</th><th>Tiempo</th><th>Tokens</th></tr>{filas_m}</table>
</div></body></html>"""
