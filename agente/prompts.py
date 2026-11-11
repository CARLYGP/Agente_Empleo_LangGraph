"""Instrucciones de los agentes con LLM y lectura de la hoja de vida."""
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def cv_texto(ruta: str) -> str:
    """Texto plano de la hoja de vida (PDF). Es la ÚNICA fuente de verdad sobre el candidato."""
    from pypdf import PdfReader
    p = Path(ruta)
    if not p.exists():
        return ""
    if p.suffix.lower() == ".txt":
        return p.read_text(encoding="utf-8").strip()
    return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages).strip()


EVALUADOR = """Eres un reclutador técnico que evalúa ofertas de empleo para un candidato junior concreto.
Compara la oferta con la hoja de vida y califica de 0 a 100 qué tan bien encaja.
Criterios: requisitos técnicos que cumple de verdad, años de experiencia exigidos frente a los que tiene,
nivel de inglés pedido (el candidato tiene B1+), seniority del cargo y relación con IA, datos o automatización.
Reglas:
- Solo cuenta como fortaleza lo que aparece en la hoja de vida. No supongas habilidades.
- Un cargo senior, de liderazgo o que exige 3+ años no pasa de 40.
- La razón va en español, en una o dos frases, sin repetir el título de la oferta."""


def evaluar(cv: str, o: dict) -> str:
    return f"""HOJA DE VIDA DEL CANDIDATO:
{cv[:6000]}

OFERTA:
Título: {o['titulo']}
Empresa: {o['empresa'] or 'no indicada'}
Portal: {o['fuente']}
Años exigidos (detectados por reglas): {o.get('anios') if o.get('anios') is not None else 'no lo dice'}
Descripción:
{o.get('detalle', '')[:5000]}"""


REDACTOR = """Escribes cartas de presentación breves y concretas para postularse a una oferta de empleo.
Reglas que no se negocian:
- Usa SOLO hechos que estén en la hoja de vida. Nunca inventes empresas, cifras, herramientas, títulos ni logros.
- Escribe en el idioma indicado (es = español, en = inglés).
- Entre 150 y 260 palabras. Tres o cuatro párrafos. Sin listas, sin corchetes, sin marcadores para rellenar.
- Conecta dos o tres experiencias reales del candidato con requisitos concretos de la oferta.
- Si la oferta pide algo que el candidato no tiene, no lo afirmes: muestra lo más cercano que sí tiene.
- Tono profesional y directo, sin frases de relleno ("me apasiona", "soy la persona ideal").
- Cierra con el nombre completo del candidato. Menciona que adjunta su hoja de vida."""


def redactar(nombre: str, cv: str, o: dict, idioma: str, observaciones: list, anterior: str | None) -> str:
    txt = f"""IDIOMA: {idioma}
NOMBRE DEL CANDIDATO: {nombre}

HOJA DE VIDA:
{cv[:6000]}

OFERTA:
Título: {o['titulo']}
Empresa: {o['empresa'] or 'no indicada'}
Descripción:
{o.get('detalle', '')[:4000]}"""
    if observaciones and anterior:
        txt += "\n\nBORRADOR ANTERIOR:\n" + anterior + "\n\nEL REVISOR PIDIÓ CORREGIR:\n- " + "\n- ".join(observaciones)
    return txt


REVISOR = """Revisas cartas de presentación antes de que se envíen a un empleador real.
Rechaza la carta si encuentras cualquiera de estos problemas:
1. Afirma algo sobre el candidato que NO está en la hoja de vida (empresa, herramienta, cifra, título, logro, años).
2. Se equivoca de cargo o de empresa respecto a la oferta.
3. Tiene marcadores sin rellenar, corchetes o texto genérico que sirve para cualquier oferta.
4. Está en un idioma distinto al de la oferta.
Para el punto 1, lista TODAS las afirmaciones de la carta sobre el candidato y, para cada una, copia
literalmente el fragmento de la hoja de vida que la respalda. Si no encuentras respaldo literal, deja la cita
vacía: exagerar (decir que construyó lo que solo propuso, «extenso» o «experto» sin respaldo, sumar
herramientas a una experiencia que no las menciona) cuenta como no respaldado.
Si la apruebas, deja la lista de problemas vacía.
Cada problema debe decir exactamente qué frase cambiar y por qué."""


def revisar(cv: str, o: dict, idioma: str, carta: str) -> str:
    return f"""HOJA DE VIDA (única fuente de verdad):
{cv[:6000]}

OFERTA: {o['titulo']} | Empresa: {o['empresa'] or 'no indicada'} | Idioma esperado: {idioma}
{o.get('detalle', '')[:2500]}

CARTA A REVISAR:
{carta}"""


def plantilla(nombre: str, o: dict, idioma: str) -> tuple[str, str]:
    """Plan B sin LLM: carta corta y genérica (queda marcada para revisión humana)."""
    empresa = o["empresa"] or ("su compañía" if idioma == "es" else "your company")
    if idioma == "en":
        return (f"Application: {o['titulo']} - {nombre}",
                f"Dear hiring team,\n\nI am writing to apply for the {o['titulo']} position at {empresa}. "
                "I hold a degree in Applied Mathematics and Computer Science with a minor in Artificial Intelligence, "
                "and I have hands-on experience deploying a real-time computer vision system with YOLO, building "
                "LLM-based applications and automating end-to-end data processes at a multinational company.\n\n"
                "I have attached my resume and would welcome the opportunity to discuss how I can contribute to your team.\n\n"
                f"Best regards,\n{nombre}")
    return (f"Postulación: {o['titulo']} - {nombre}",
            f"Buen día,\n\nMe permito postularme al cargo de {o['titulo']} en {empresa}. Soy matemático aplicado y "
            "científico de la computación con menor en Inteligencia Artificial, con experiencia desplegando un sistema "
            "de visión por computador en tiempo real con YOLO, construyendo aplicaciones con LLM y automatizando "
            "procesos de datos de principio a fin en una multinacional.\n\n"
            "Adjunto mi hoja de vida y quedo atento a la posibilidad de conversar sobre cómo puedo aportar al equipo.\n\n"
            f"Cordialmente,\n{nombre}")
