"""Configuración: config.json en la raíz del proyecto (no se sube a git) + variables de entorno."""
import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"
DATOS.mkdir(exist_ok=True)

POR_DEFECTO = {
    # Modelo de lenguaje (Groq, OpenAI-compatible). La clave también puede venir de GROQ_API_KEY.
    "groq_api_key": "",
    "modelo": "openai/gpt-oss-120b",
    # Credenciales de Gmail: se leen del config del agente v1 para no duplicar la contraseña de aplicación.
    "gmail_config": str(RAIZ.parent / "AgenteEmpleo" / "config.json"),
    # Candidato
    "nombre": "Carlos Andrés Galán Pérez",
    "nombre_corto": "Carlos",
    "cv_es": str(Path.home() / "Desktop" / "Carlos Galan Perez - CV Ingeniero de IA (Español).pdf"),
    "cv_en": str(Path.home() / "Desktop" / "Carlos Galan Perez - CV (English).pdf"),
    # Postulación: "aprobacion" (el grafo se detiene hasta que apruebes), "automatico" o "apagado"
    "modo_postulacion": "aprobacion",
    "puntaje_minimo_carta": 70,    # puntaje final mínimo para preparar carta y postulación
    "max_evaluar": 40,             # ofertas que pasan al evaluador con LLM por corrida (controla tokens)
    "max_cartas": 8,
    "max_postulaciones_dia": 5,    # tope duro, también en modo automático
    "max_intentos_carta": 3,       # ciclos redactor -> revisor
}


def cargar():
    cfg = dict(POR_DEFECTO)
    archivo = RAIZ / "config.json"
    if archivo.exists():
        cfg.update(json.loads(archivo.read_text(encoding="utf-8")))
    cfg["groq_api_key"] = os.environ.get("GROQ_API_KEY") or cfg.get("groq_api_key") or ""
    return cfg


def gmail(cfg):
    """{'gmail', 'contrasena_aplicacion', 'destinatario'} o None si no está configurado."""
    p = Path(cfg["gmail_config"])
    if not p.exists():
        return None
    g = json.loads(p.read_text(encoding="utf-8"))
    if not g.get("gmail") or not g.get("contrasena_aplicacion"):
        return None
    return g
