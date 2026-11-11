"""Capa delgada sobre el modelo de lenguaje.

Todos los agentes piden salidas estructuradas (esquemas Pydantic). Si la respuesta no valida
contra el esquema se reintenta con el error como retroalimentación; si se agotan los intentos
el nodo que llamó decide su plan B (reglas). Así el grafo nunca se cae por el LLM.
"""
import re
import threading
import time
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- Esquemas de salida de cada agente --------------------------------------------

class Evaluacion(BaseModel):
    """Salida del agente evaluador."""
    puntaje: int = Field(ge=0, le=100, description="Qué tan bien encaja el candidato con la oferta, 0 a 100")
    encaja: bool = Field(description="True si vale la pena postularse")
    razon: str = Field(description="Una o dos frases en español: por qué encaja o no")
    fortalezas: list[str] = Field(default_factory=list, description="Requisitos de la oferta que el candidato cumple, según su hoja de vida")
    brechas: list[str] = Field(default_factory=list, description="Requisitos de la oferta que la hoja de vida no muestra")
    idioma: Literal["es", "en"] = Field(description="Idioma en que está escrita la oferta")


class Carta(BaseModel):
    """Salida del agente redactor."""
    asunto: str = Field(description="Asunto del correo de postulación")
    cuerpo: str = Field(description="Carta de presentación lista para enviar, sin marcadores ni corchetes")


class Afirmacion(BaseModel):
    frase: str = Field(description="Afirmación de la carta sobre el candidato (experiencia, logro, herramienta, nivel, formación)")
    cita_cv: str = Field(description="Fragmento COPIADO LITERALMENTE de la hoja de vida que la respalda (máx. 12 palabras); vacío si no hay respaldo")


class Revision(BaseModel):
    """Salida del agente revisor. Las citas se verifican en código contra el texto de la hoja de vida."""
    afirmaciones: list[Afirmacion] = Field(description="TODAS las afirmaciones de la carta sobre el candidato, cada una con su cita")
    aprobada: bool
    problemas: list[str] = Field(default_factory=list, description="Qué corregir; vacío si está aprobada")


# --- Modelo -----------------------------------------------------------------------

class Modelo:
    """Modelo real vía Groq. `estructurado` devuelve (objeto | None, tokens, error | None)."""

    def __init__(self, api_key: str, modelo: str):
        from langchain_groq import ChatGroq
        self.nombre = modelo
        self._chat = ChatGroq(model=modelo, api_key=api_key, temperature=0.2, max_tokens=1500,
                              reasoning_effort="low", max_retries=2, timeout=60)

    # El plan gratis de Groq da ~8.000 tokens por minuto: pocas llamadas simultáneas y espera ante el 429.
    _cupo = threading.Semaphore(2)
    ESPERAS_429 = 6

    def _invocar(self, esquema, mensajes):
        for n in range(self.ESPERAS_429 + 1):
            try:
                with self._cupo:
                    return self._chat.with_structured_output(esquema, include_raw=True).invoke(mensajes)
            except Exception as e:
                if "429" not in str(e) and "rate limit" not in str(e).lower() or n == self.ESPERAS_429:
                    raise
                m = re.search(r"try again in ([\d.]+)(ms|s)", str(e))
                espera = (float(m.group(1)) / (1000 if m.group(2) == "ms" else 1)) if m else 2 ** n
                time.sleep(min(60, espera + 1 + n))

    def estructurado(self, esquema, sistema: str, usuario: str, intentos: int = 2):
        tokens, error = 0, None
        mensajes = [("system", sistema), ("human", usuario)]
        for _ in range(intentos):
            try:
                r = self._invocar(esquema, mensajes)
            except Exception as e:                       # red, límite de tasa agotado, esquema rechazado...
                error = f"{type(e).__name__}: {e}"[:300]
                continue
            uso = getattr(r["raw"], "usage_metadata", None) or {}
            tokens += uso.get("total_tokens", 0)
            if r.get("parsed") is not None:
                return r["parsed"], tokens, None
            error = str(r.get("parsing_error"))[:300]
            mensajes = mensajes + [("human", f"Tu respuesta anterior no cumplió el formato ({error}). Repite cumpliendo el esquema.")]
        return None, tokens, error


def crear(cfg) -> Optional[Modelo]:
    """None si no hay clave: los agentes con LLM caen a su plan B por reglas."""
    if not cfg.get("groq_api_key"):
        return None
    return Modelo(cfg["groq_api_key"], cfg["modelo"])
