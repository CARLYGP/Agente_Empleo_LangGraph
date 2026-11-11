"""Agente multiagente de búsqueda y postulación de empleo (LangGraph).

Uso:
    python main.py                 corrida diaria: busca, evalúa, redacta, te manda el resumen y queda
                                   en pausa esperando tu aprobación para postularse
    python main.py --prueba        igual, pero no envía nada a nadie ni marca ofertas como vistas;
                                   las postulaciones aprobadas se escriben como .eml en data/salida
    python main.py --demo          ofertas de ejemplo, sin internet (implica --prueba)
    python main.py --aprobar       muestra las postulaciones pendientes y pregunta cuáles enviar
    python main.py --aprobar 1,3   envía la 1 y la 3   (también: todas | ninguna)
    python main.py --grafo         imprime el diagrama del grafo (Mermaid)
"""
import json
import sqlite3
import sys
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", message="Core Pydantic V1")

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from agente import config, grafo, llm
from agente.config import DATOS

PENDIENTE = DATOS / "pendiente.json"


def armar(cfg, demo=False):
    fuentes = detalle = None
    if demo:
        from tests.ofertas_demo import FUENTES_DEMO
        fuentes, detalle = FUENTES_DEMO, {}
    conn = sqlite3.connect(DATOS / "checkpoints.sqlite", check_same_thread=False)
    return grafo.construir(cfg, modelo=llm.crear(cfg), fuentes=fuentes, detalle=detalle,
                           gmail=config.gmail(cfg), checkpointer=SqliteSaver(conn))


def informar(app, hilo, estado):
    pendientes = app.get_state({"configurable": {"thread_id": hilo}}).interrupts
    for p in estado.get("postulaciones", []):
        print(f"  Postulación #{p['id']} {p['titulo'][:60]}: {p['estado']} ({p.get('canal', p.get('error', ''))})")
    if pendientes:
        PENDIENTE.write_text(json.dumps({"hilo": hilo}), encoding="utf-8")
        info = pendientes[0].value
        print(f"\n{len(info['pendientes'])} postulaciones esperan tu aprobación (cupo de hoy: {info['cupo']}):")
        for c in info["pendientes"]:
            canal = f"correo a {c['correo']}" if c["correo"] else "portal (manual)"
            aviso = "  << REVISAR A MANO" if c["requiere_revision"] else ""
            print(f"  #{c['id']} [{c['puntaje']}] {c['titulo'][:60]} | {c['empresa'] or '-'} | {canal}{aviso}")
        print(f"\nCartas en {DATOS / 'cartas' / hilo}. Para enviar: python main.py --aprobar 1,3")
    else:
        PENDIENTE.unlink(missing_ok=True)
    tokens = sum(m.get("tokens", 0) for m in estado.get("metricas", []))
    print(f"Tokens usados en total: {tokens:,}. Resumen en {DATOS / 'ultimo_resumen.html'}")


def correr(prueba, demo):
    cfg = config.cargar()
    app = armar(cfg, demo)
    hilo = f"{'demo' if demo else 'corrida'}-{datetime.now():%Y%m%d-%H%M%S}"
    print(f"Hilo {hilo} | modelo: {cfg['modelo'] if cfg['groq_api_key'] else 'SIN LLM (plan B por reglas)'} | "
          f"modo: {cfg['modo_postulacion']}{' | PRUEBA' if prueba else ''}")
    estado = app.invoke({"prueba": prueba, "hilo": hilo}, {"configurable": {"thread_id": hilo}, "recursion_limit": 100})
    informar(app, hilo, estado)


def aprobar(args):
    if not PENDIENTE.exists():
        print("No hay postulaciones pendientes.")
        return
    hilo = json.loads(PENDIENTE.read_text(encoding="utf-8"))["hilo"]
    cfg = config.cargar()
    app = armar(cfg, demo=hilo.startswith("demo"))
    conf = {"configurable": {"thread_id": hilo}}
    info = app.get_state(conf).interrupts[0].value
    if args:
        respuesta = args[0]
    else:
        for c in info["pendientes"]:
            print(f"  #{c['id']} [{c['puntaje']}] {c['titulo'][:60]} | {c['correo'] or 'portal'} | {c['archivo']}")
        respuesta = input("¿Cuáles envío? (ej. 1,3 | todas | ninguna): ").strip()
    if respuesta.lower() == "todas":
        ids = [c["id"] for c in info["pendientes"]]
    elif respuesta.lower() in ("ninguna", ""):
        ids = []
    else:
        ids = [int(x) for x in respuesta.replace(" ", "").split(",") if x.isdigit()]
    estado = app.invoke(Command(resume=ids), conf)
    informar(app, hilo, estado)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--grafo" in a:
        print(armar(config.cargar(), demo=True).get_graph(xray=True).draw_mermaid())
    elif "--aprobar" in a:
        aprobar(a[a.index("--aprobar") + 1:])
    else:
        correr(prueba="--prueba" in a or "--demo" in a, demo="--demo" in a)
