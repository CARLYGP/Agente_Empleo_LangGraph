"""Pruebas del grafo sin red ni LLM real: un modelo falso controla qué responde cada agente."""
import email
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="Core Pydantic V1")

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agente import config, correo, grafo
from agente.llm import Afirmacion, Carta, Evaluacion, Revision
from tests.ofertas_demo import FUENTES_DEMO

AQUI = Path(__file__).parent


class ModeloFalso:
    """Primer borrador de cada carta con un marcador sin rellenar: obliga al ciclo redactor ⇄ revisor."""

    def __init__(self, cita_falsa=None):
        self.cita_falsa = cita_falsa
        self.llamadas = {"Evaluacion": 0, "Carta": 0, "Revision": 0}

    def estructurado(self, esquema, sistema, usuario, intentos=2):
        self.llamadas[esquema.__name__] += 1
        if esquema is Evaluacion:
            en = "IDIOMA: en" in usuario or "We are looking" in usuario
            return Evaluacion(puntaje=90, encaja=True, razon="Encaja por Python y LLM.", fortalezas=["Python"],
                              brechas=[], idioma="en" if en else "es"), 100, None
        if esquema is Carta:
            en = "IDIOMA: en" in usuario
            base = ("I am applying for the role and will bring my experience with Python. " * 15 + "Candidato Demo") if en else \
                   ("Me postulo a este cargo con mi experiencia en Python. " * 20 + "Candidato Demo")
            marcador = "" if "BORRADOR ANTERIOR" in usuario else " [Empresa] "
            return Carta(asunto="Postulación", cuerpo=base + marcador), 200, None
        if esquema is Revision:
            cita = self.cita_falsa or "detección y conteo de personas en tiempo real con YOLO"
            return Revision(afirmaciones=[Afirmacion(frase="Desplegó detección en tiempo real", cita_cv=cita)],
                            aprobada=True, problemas=[]), 50, None


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setattr(grafo, "DATOS", tmp_path)
    monkeypatch.setattr(grafo, "VISTAS", tmp_path / "vistas.json")
    monkeypatch.setattr(grafo, "REGISTRO", tmp_path / "postulaciones.json")
    c = dict(config.POR_DEFECTO)
    c.update(nombre="Candidato Demo", nombre_corto="Demo", cv_es=str(AQUI / "cv_demo.txt"), cv_en=str(AQUI / "cv_demo.txt"),
             gmail_config=str(tmp_path / "no_existe.json"))
    return c


def correr(cfg, modelo):
    app = grafo.construir(cfg, modelo=modelo, fuentes=FUENTES_DEMO, detalle={}, gmail=None, checkpointer=InMemorySaver())
    conf = {"configurable": {"thread_id": "t1"}}
    estado = app.invoke({"prueba": True, "hilo": "t1"}, conf)
    return app, conf, estado


def test_flujo_completo_con_aprobacion(cfg, tmp_path):
    modelo = ModeloFalso()
    app, conf, estado = correr(cfg, modelo)

    # Filtro: fuera el senior (título) y la de 5 años; quedan 3 que pasan al evaluador con LLM
    assert {o["titulo"] for o in estado["candidatas"]} == {
        "Ingeniero de IA Junior (agentes LLM)", "Analista de Datos Junior - Power BI", "Junior AI Engineer (Computer Vision)"}
    assert modelo.llamadas["Evaluacion"] == 3

    # El grafo se detuvo en la aprobación humana con 3 cartas
    pendientes = app.get_state(conf).interrupts[0].value["pendientes"]
    assert len(pendientes) == 3
    canales = {p["titulo"]: p["correo"] for p in pendientes}
    assert canales["Ingeniero de IA Junior (agentes LLM)"] == "talento@andina-analytics.invalid"
    assert canales["Analista de Datos Junior - Power BI"] is None          # sin correo: postulación por el portal

    # Ciclo redactor ⇄ revisor: el marcador [Empresa] obligó a un segundo borrador en cada carta
    assert all(c["intentos"] == 2 and not c["requiere_revision"] for c in estado["cola"])

    # Aprobar todas: modo prueba => .eml en disco, nada enviado
    final = app.invoke(Command(resume=[p["id"] for p in pendientes]), conf)
    estados = {p["titulo"]: p["estado"] for p in final["postulaciones"]}
    assert estados["Analista de Datos Junior - Power BI"] == "manual"
    assert estados["Junior AI Engineer (Computer Vision)"] == "simulada"
    eml = list((tmp_path / "salida" / "t1").glob("*.eml"))
    assert len(eml) == 2
    msg = email.message_from_bytes(eml[0].read_bytes())
    assert any(p.get_filename() == "CV - Candidato Demo.pdf" for p in msg.walk())
    assert not (tmp_path / "postulaciones.json").exists()                  # en prueba no se registra nada
    assert app.get_state(conf).next == ()                                   # el grafo terminó


def test_ninguna_aprobada_no_postula(cfg):
    app, conf, _ = correr(cfg, ModeloFalso())
    final = app.invoke(Command(resume=[]), conf)
    assert final["postulaciones"] == []


def test_sin_llm_usa_reglas_y_marca_revision(cfg):
    _, _, estado = correr(cfg, None)
    assert all(e["fuente_eval"] == "reglas" for e in estado["evaluaciones"])
    assert all(c["requiere_revision"] for c in estado.get("cola", []))


def test_modo_apagado_no_pide_aprobacion(cfg):
    cfg["modo_postulacion"] = "apagado"
    app, conf, estado = correr(cfg, ModeloFalso())
    assert "cola" not in estado or not estado["cola"]
    assert app.get_state(conf).next == ()


def test_extraer_correo_exige_contexto():
    assert correo.extraer_correo("Envía tu hoja de vida a rh@empresa.co") == "rh@empresa.co"
    assert correo.extraer_correo("Política de datos: privacidad@empresa.co") is None
    assert correo.extraer_correo("Contacto general: info@empresa.co. Horario de 8 a 5.") is None
    assert correo.extraer_correo("Apply at jobs@linkedin.com with your CV") is None


def test_revisor_rechaza_afirmacion_sin_respaldo(cfg):
    """Aunque el LLM revisor apruebe, una cita que no está en la hoja de vida tumba la carta."""
    _, _, estado = correr(cfg, ModeloFalso(cita_falsa="cinco años liderando equipos de Kubernetes"))
    assert all(c["requiere_revision"] and c["intentos"] == cfg["max_intentos_carta"] for c in estado["cola"])
    assert all("Sin respaldo literal" in c["observaciones"][0] for c in estado["cola"])


def test_cita_valida_tolera_cortes_de_linea():
    cv = "Desarrollé y desplegué un sistema de detección y conteo de personas en tiempo\nreal usando las cámaras"
    assert grafo.cita_valida("conteo de personas en tiempo real", cv)
    assert not grafo.cita_valida("extensive Python scripting", cv)
