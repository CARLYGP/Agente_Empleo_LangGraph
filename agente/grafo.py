"""Grafo multiagente de búsqueda y postulación de empleo (LangGraph).

    START ─► buscar_portal ×15 (en paralelo, Send) ─► filtrar ─► evaluar_oferta ×N (en paralelo, LLM)
          ─► priorizar ─► taller_carta ×K (subgrafo redactor ⇄ revisor, LLM) ─► notificar
          ─► aprobar (interrupt: humano en el ciclo) ─► postular ─► END

Las rutas entre agentes son aristas condicionales: si nada pasa los filtros se salta la evaluación,
si nada supera el puntaje mínimo no se redactan cartas, y si no hay cartas el grafo termina sin
pedir aprobación. El estado se guarda en SQLite (checkpointer), así que la corrida de la mañana
puede quedar en pausa y reanudarse horas después con la decisión del candidato.
"""
import json
import operator
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Annotated, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from . import correo, portales as P, prompts
from .config import DATOS
from .llm import Carta, Evaluacion, Revision

VISTAS = DATOS / "vistas.json"
REGISTRO = DATOS / "postulaciones.json"


class Estado(TypedDict, total=False):
    prueba: bool                                      # no envía nada a terceros ni marca vistas
    hilo: str
    ofertas: Annotated[list, operator.add]            # crudas, una lista por portal (reducer: concatena)
    revisadas: int
    candidatas: list
    urls_revisadas: list
    descartes: dict
    evaluaciones: Annotated[list, operator.add]
    priorizadas: list
    cartas: Annotated[list, operator.add]
    cola: list                                        # cartas numeradas, pendientes de aprobación
    aprobadas: list
    postulaciones: Annotated[list, operator.add]
    metricas: Annotated[list, operator.add]           # tiempo y tokens por nodo
    errores: Annotated[list, operator.add]


class EstadoCarta(TypedDict, total=False):
    oferta: dict
    idioma: str
    borrador: Optional[dict]
    observaciones: list
    intentos: int
    aprobada: bool
    tokens: int


def _json(ruta, defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def _clave(o):
    return (re.sub(r"\W+", " ", o["titulo"].lower()).strip(), re.sub(r"\W+", " ", (o["empresa"] or "").lower()).strip())


def verificar_carta(cuerpo: str, idioma: str, nombre: str) -> list[str]:
    """Chequeos deterministas antes del revisor con LLM (gratis y sin falsos negativos)."""
    problemas = []
    palabras = len(cuerpo.split())
    if re.search(r"\[[^\]]*\]|\{[^}]*\}|XXX|<[a-z]+>", cuerpo):
        problemas.append("Tiene marcadores sin rellenar (corchetes, llaves o XXX).")
    if not 120 <= palabras <= 330:
        problemas.append(f"Tiene {palabras} palabras; debe tener entre 150 y 260.")
    if nombre.split()[0].lower() not in cuerpo.lower():
        problemas.append("No cierra con el nombre del candidato.")
    if (idioma == "en") != P.en_ingles(cuerpo):
        problemas.append(f"Está en el idioma equivocado; debe ir en {'inglés' if idioma == 'en' else 'español'}.")
    return problemas


def _normalizar(t: str) -> str:
    t = unicodedata.normalize("NFKC", t or "").lower()          # NFKC deshace ligaduras del PDF («ﬁ» -> «fi»)
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


def cita_valida(cita: str, cv: str) -> bool:
    """La cita existe en la hoja de vida: literal, o casi (85 % de sus pares de palabras, por cortes de línea del PDF)."""
    c, texto = _normalizar(cita), _normalizar(cv)
    if len(c) < 4:
        return False
    if c in texto:
        return True
    palabras = c.split()
    pares = [" ".join(palabras[i:i + 2]) for i in range(len(palabras) - 1)]
    return len(pares) >= 3 and sum(p in texto for p in pares) / len(pares) >= 0.85


def construir(cfg, modelo=None, fuentes=None, detalle=None, gmail=None, checkpointer=None):
    """Arma el grafo. `fuentes`, `detalle`, `modelo` y `gmail` se inyectan para poder probarlo sin red."""
    fuentes = dict(fuentes if fuentes is not None else P.FUENTES)
    detalle = detalle if detalle is not None else P.DETALLE
    nombre = cfg["nombre"]
    cv_es = prompts.cv_texto(cfg["cv_es"])

    def medido(nodo, fn):
        def envoltura(entrada):
            t = time.perf_counter()
            salida = fn(entrada) or {}
            tokens = salida.pop("_tokens", 0)
            salida["metricas"] = salida.get("metricas", []) + [
                {"nodo": nodo, "seg": round(time.perf_counter() - t, 2), "tokens": tokens}]
            return salida
        return envoltura

    # --- Agente buscador: un nodo por portal, en paralelo ----------------------------------------
    def repartir_portales(_):
        return [Send("buscar_portal", {"portal": n}) for n in fuentes]

    def buscar_portal(entrada):
        nombre_portal = entrada["portal"]
        try:
            r = fuentes[nombre_portal]()
            P.log(f"{nombre_portal}: {len(r)} ofertas")
            return {"ofertas": list(r.values())}
        except Exception as ex:
            P.log(f"{nombre_portal}: ERROR {ex}")
            return {"errores": [f"{nombre_portal}: {type(ex).__name__}: {ex}"[:200]]}

    # --- Filtro por reglas (gratis): título, vistas, duplicados, modalidad, país, experiencia ---------
    def filtrar(estado):
        vistas = _json(VISTAS, {})
        ya_postulado = {r["url"] for r in _json(REGISTRO, [])}
        todas = {o["url"]: o for o in estado.get("ofertas", [])}
        unicas = {}
        for u, o in todas.items():
            if u in vistas or u in ya_postulado or not P.TITULO_TEMA.search(o["titulo"]) or P.TITULO_FUERA.search(o["titulo"]):
                continue
            k = _clave(o)
            if k not in unicas or (o["local"] and not unicas[k]["local"]):
                unicas[k] = o
        candidatas = list(unicas.values())

        def ficha(o):
            try:
                return o["_detalle"] if o.get("_detalle") is not None else detalle.get(o["fuente"], lambda x: "")(o)
            except Exception as ex:
                P.log(f"  ! detalle {o['url'][:80]}: {ex}")
                return ""

        with ThreadPoolExecutor(8) as ex:
            fichas = list(ex.map(ficha, candidatas))

        descartes = {"sin ficha": 0, "no remota": 0, "fuera de Colombia/LATAM": 0, "mucha experiencia": 0, "poco afín": 0}
        elegidas = []
        for o, det in zip(candidatas, fichas):
            motivo = None
            if not det:
                motivo = "sin ficha"
            elif not P.es_remoto(o, det):
                motivo = "no remota"
            elif not P.puede_aplicar_desde_colombia(o, det):
                motivo = "fuera de Colombia/LATAM"
            else:
                o["anios"] = P.anios_exigidos(det)
                if o["anios"] is not None and o["anios"] > P.MAX_ANIOS:
                    motivo = "mucha experiencia"
                elif P.afinidad(o, det) < P.AFINIDAD_MINIMA:
                    motivo = "poco afín"
            if motivo:
                descartes[motivo] += 1
                continue
            o["prob"] = P.probabilidad(o, det)
            o["por_que"] = P.por_que(o)
            o["detalle"] = det[:6000]
            o.pop("_detalle", None)
            elegidas.append(o)
        elegidas.sort(key=lambda o: (o["freelance"], -o["prob"]))
        P.log(f"Filtro: {len(todas)} revisadas, {len(candidatas)} por título, {len(elegidas)} pasan | {descartes}")
        return {"revisadas": len(todas), "candidatas": elegidas, "descartes": descartes,
                "urls_revisadas": [o["url"] for o in candidatas]}

    def ruta_evaluar(estado):
        a_evaluar = [o for o in estado["candidatas"] if not o["freelance"]][: cfg["max_evaluar"]]
        if not a_evaluar:
            return "priorizar"
        return [Send("evaluar_oferta", {"oferta": o}) for o in a_evaluar]

    # --- Agente evaluador (LLM): oferta contra hoja de vida, salida estructurada ------------------
    def evaluar_oferta(entrada):
        o = entrada["oferta"]
        if modelo is not None and cv_es:
            ev, tokens, error = modelo.estructurado(Evaluacion, prompts.EVALUADOR, prompts.evaluar(cv_es, o))
            if ev is not None:
                return {"evaluaciones": [{"url": o["url"], "fuente_eval": "llm", **ev.model_dump()}], "_tokens": tokens}
        else:
            tokens, error = 0, None
        plan_b = {"url": o["url"], "fuente_eval": "reglas", "puntaje": o["prob"], "encaja": o["prob"] >= 55,
                  "razon": o["por_que"], "fortalezas": o.get("tiene", []), "brechas": o.get("falta", []),
                  "idioma": "en" if P.en_ingles(o.get("detalle", "")) else "es"}
        salida = {"evaluaciones": [plan_b], "_tokens": tokens}
        if error:
            salida["errores"] = [f"evaluador ({o['titulo'][:40]}): {error}"]
        return salida

    def priorizar(estado):
        evs = {e["url"]: e for e in estado.get("evaluaciones", [])}
        priorizadas = []
        for o in estado["candidatas"]:
            o = dict(o)
            ev = evs.get(o["url"])
            o["eval"] = ev
            if ev and ev["fuente_eval"] == "llm":
                o["puntaje"] = round(0.6 * ev["puntaje"] + 0.4 * o["prob"])   # criterio del LLM + señales del mercado
            else:
                o["puntaje"] = o["prob"]
            o["correo_postulacion"] = correo.extraer_correo(o.get("detalle", ""))
            priorizadas.append(o)
        priorizadas.sort(key=lambda o: (o["freelance"], -o["puntaje"]))
        return {"priorizadas": priorizadas}

    def ruta_cartas(estado):
        if cfg["modo_postulacion"] == "apagado":
            return "notificar"
        elegibles = [o for o in estado["priorizadas"]
                     if not o["freelance"] and o["puntaje"] >= cfg["puntaje_minimo_carta"]
                     and (o["eval"] or {}).get("encaja", True)][: cfg["max_cartas"]]
        if not elegibles:
            return "notificar"
        return [Send("taller_carta", {"oferta": o}) for o in elegibles]

    # --- Subgrafo taller de cartas: redactor ⇄ revisor hasta aprobar o agotar intentos ------------
    def redactar(s: EstadoCarta):
        o, idioma = s["oferta"], s["idioma"]
        cv = prompts.cv_texto(cfg["cv_en"] if idioma == "en" else cfg["cv_es"]) or cv_es
        if modelo is None:
            asunto, cuerpo = prompts.plantilla(nombre, o, idioma)
            return {"borrador": {"asunto": asunto, "cuerpo": cuerpo}, "tokens": s.get("tokens", 0)}
        anterior = (s.get("borrador") or {}).get("cuerpo")
        carta, tokens, _ = modelo.estructurado(
            Carta, prompts.REDACTOR, prompts.redactar(nombre, cv, o, idioma, s.get("observaciones", []), anterior))
        borrador = carta.model_dump() if carta else (s.get("borrador") or dict(zip(("asunto", "cuerpo"), prompts.plantilla(nombre, o, idioma))))
        return {"borrador": borrador, "tokens": s.get("tokens", 0) + tokens}

    def revisar(s: EstadoCarta):
        o, idioma, b = s["oferta"], s["idioma"], s["borrador"]
        problemas = verificar_carta(b["cuerpo"], idioma, nombre)
        tokens = 0
        if modelo is not None and not problemas:
            cv = prompts.cv_texto(cfg["cv_en"] if idioma == "en" else cfg["cv_es"]) or cv_es
            rev, tokens, error = modelo.estructurado(Revision, prompts.REVISOR, prompts.revisar(cv, o, idioma, b["cuerpo"]))
            if rev is None:
                problemas = [f"El revisor no respondió ({error}); revisar a mano."]
            else:
                # Verificación en código: cada afirmación necesita una cita que exista de verdad en la hoja de vida.
                sin_respaldo = [a.frase for a in rev.afirmaciones if not cita_valida(a.cita_cv, cv)]
                problemas = [f"Sin respaldo literal en la hoja de vida, quítala o ajústala a lo que dice: «{f}»"
                             for f in sin_respaldo]
                if not rev.aprobada:
                    problemas += rev.problemas or ["El revisor la rechazó sin detallar."]
                if not rev.afirmaciones:
                    problemas.append("El revisor no listó las afirmaciones de la carta; revisar a mano.")
        if modelo is None:
            problemas = problemas or ["Carta de plantilla (sin LLM): revisar a mano antes de enviar."]
        return {"observaciones": problemas, "aprobada": not problemas,
                "intentos": s.get("intentos", 0) + 1, "tokens": s.get("tokens", 0) + tokens}

    def ruta_revision(s: EstadoCarta):
        if s["aprobada"] or s["intentos"] >= cfg["max_intentos_carta"] or modelo is None:
            return END
        return "redactar"

    sub = StateGraph(EstadoCarta)
    sub.add_node("redactar", redactar)
    sub.add_node("revisar", revisar)
    sub.add_edge(START, "redactar")
    sub.add_edge("redactar", "revisar")
    sub.add_conditional_edges("revisar", ruta_revision, ["redactar", END])
    taller = sub.compile()

    def taller_carta(entrada):
        o = entrada["oferta"]
        idioma = (o["eval"] or {}).get("idioma") or ("en" if P.en_ingles(o.get("detalle", "")) else "es")
        r = taller.invoke({"oferta": o, "idioma": idioma, "intentos": 0, "tokens": 0, "observaciones": []})
        return {"cartas": [{
            "url": o["url"], "titulo": o["titulo"], "empresa": o["empresa"], "puntaje": o["puntaje"],
            "idioma": idioma, "correo": o["correo_postulacion"], "asunto": r["borrador"]["asunto"],
            "cuerpo": r["borrador"]["cuerpo"], "intentos": r["intentos"],
            "requiere_revision": not r["aprobada"], "observaciones": r["observaciones"]}],
            "_tokens": r["tokens"]}

    # --- Notificador: resumen diario + cartas en disco para editarlas ------------------------------
    def notificar(estado):
        cola = sorted(estado.get("cartas", []), key=lambda c: -c["puntaje"])
        carpeta = DATOS / "cartas" / estado["hilo"]
        for i, c in enumerate(cola, 1):
            c["id"] = i
            c["archivo"] = str(carpeta / f"{i:02d}.txt")
            carpeta.mkdir(parents=True, exist_ok=True)
            notas = "".join(f"# REVISOR: {p}\n" for p in c["observaciones"]) if c["requiere_revision"] else ""
            (carpeta / f"{i:02d}.txt").write_text(f"{notas}# {c['titulo']} | {c['empresa']} | {c['url']}\n"
                             f"# Canal: {c['correo'] or 'portal (postulación manual)'}\n"
                             f"ASUNTO: {c['asunto']}\n\n{c['cuerpo']}\n", encoding="utf-8")
        html_ = correo.resumen_html(cfg["nombre_corto"], estado.get("priorizadas", []), cola, estado.get("revisadas", 0),
                                    len(fuentes), estado.get("metricas", []), cfg["modo_postulacion"],
                                    estado.get("prueba"), estado.get("descartes", {}))
        (DATOS / "ultimo_resumen.html").write_text(html_, encoding="utf-8")
        empleos = [o for o in estado.get("priorizadas", []) if not o["freelance"]]
        if not estado.get("prueba"):
            if gmail and (empleos or cola):
                correo.resumen(gmail, f"{len(empleos)} ofertas nuevas, {len(cola)} postulaciones listas", html_)
            vistas = _json(VISTAS, {})
            hoy = datetime.now().strftime("%Y-%m-%d")
            vistas.update({u: hoy for u in estado.get("urls_revisadas", [])})
            VISTAS.write_text(json.dumps(vistas, ensure_ascii=False, indent=0), encoding="utf-8")
        return {"cola": cola}

    def ruta_aprobar(estado):
        return "aprobar" if estado.get("cola") and cfg["modo_postulacion"] != "apagado" else END

    # --- Humano en el ciclo: el grafo se detiene hasta recibir la decisión ---------------------------
    def aprobar(estado):
        cola = estado["cola"]
        hoy = datetime.now().strftime("%Y-%m-%d")
        cupo = max(0, cfg["max_postulaciones_dia"] - sum(1 for r in _json(REGISTRO, []) if r["fecha"].startswith(hoy)))
        if cfg["modo_postulacion"] == "automatico":
            ids = [c["id"] for c in cola if c["correo"] and not c["requiere_revision"]]
        else:
            decision = interrupt({"pendientes": [
                {k: c[k] for k in ("id", "titulo", "empresa", "puntaje", "correo", "requiere_revision", "archivo", "url")}
                for c in cola], "cupo": cupo})
            ids = decision if isinstance(decision, list) else []
        validos = {c["id"] for c in cola}
        return {"aprobadas": [i for i in ids if i in validos][:cupo]}

    # --- Agente postulador -------------------------------------------------------------------------
    def postular(estado):
        resultados, registro = [], _json(REGISTRO, [])
        for c in estado["cola"]:
            if c["id"] not in estado.get("aprobadas", []):
                continue
            asunto, cuerpo = c["asunto"], c["cuerpo"]
            archivo = DATOS / "cartas" / estado["hilo"] / f"{c['id']:02d}.txt"
            if archivo.exists():   # el candidato pudo editarla: manda lo que está en disco
                texto = archivo.read_text(encoding="utf-8")
                lineas = [l for l in texto.splitlines() if not l.startswith("#")]
                m = re.match(r"ASUNTO: (.*)", lineas[0]) if lineas else None
                if m:
                    asunto, cuerpo = m.group(1).strip(), "\n".join(lineas[1:]).strip()
            r = {"id": c["id"], "url": c["url"], "titulo": c["titulo"], "empresa": c["empresa"],
                 "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")}
            if c["correo"]:
                cv = cfg["cv_en"] if c["idioma"] == "en" else cfg["cv_es"]
                salida = DATOS / "salida" / estado["hilo"] / f"{c['id']:02d}.eml" if estado.get("prueba") else None
                try:
                    r["estado"] = correo.postulacion(gmail, c["correo"], asunto, cuerpo, cv, nombre, salida)
                    r["canal"] = c["correo"]
                except Exception as ex:
                    r["estado"], r["error"] = "error", str(ex)[:200]
            else:
                r["estado"], r["canal"] = "manual", "portal: carta lista en " + str(archivo)
            resultados.append(r)
            P.log(f"Postulación #{c['id']} {c['titulo'][:50]}: {r['estado']}")
            if not estado.get("prueba") and r["estado"] in ("enviada", "manual"):
                registro.append(r)
        if not estado.get("prueba"):
            REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"postulaciones": resultados}

    g = StateGraph(Estado)
    g.add_node("buscar_portal", medido("buscador", buscar_portal))
    g.add_node("filtrar", medido("filtro", filtrar))
    g.add_node("evaluar_oferta", medido("evaluador", evaluar_oferta))
    g.add_node("priorizar", medido("priorizar", priorizar))
    g.add_node("taller_carta", medido("redactor+revisor", taller_carta))
    g.add_node("notificar", medido("notificador", notificar))
    g.add_node("aprobar", aprobar)
    g.add_node("postular", medido("postulador", postular))

    g.add_conditional_edges(START, repartir_portales, ["buscar_portal"])
    g.add_edge("buscar_portal", "filtrar")
    g.add_conditional_edges("filtrar", ruta_evaluar, ["evaluar_oferta", "priorizar"])
    g.add_edge("evaluar_oferta", "priorizar")
    g.add_conditional_edges("priorizar", ruta_cartas, ["taller_carta", "notificar"])
    g.add_edge("taller_carta", "notificar")
    g.add_conditional_edges("notificar", ruta_aprobar, ["aprobar", END])
    g.add_edge("aprobar", "postular")
    g.add_edge("postular", END)
    return g.compile(checkpointer=checkpointer)
