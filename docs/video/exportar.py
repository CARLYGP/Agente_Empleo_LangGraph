"""Exporta a src/datos.json la corrida demo REAL que anima el video.

Lee el estado final del hilo demo en data/checkpoints.sqlite (el checkpointer de LangGraph) y la carta
generada. Solo se exporta la corrida demo, que usa las ofertas ficticias de tests/ofertas_demo.py
(dominio .invalid); nada de las corridas reales sale del equipo.

Uso: .venv/Scripts/python docs/video/exportar.py [hilo]
"""
import json
import sqlite3
import sys
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from tests.ofertas_demo import DEMO  # noqa: E402

HILO = sys.argv[1] if len(sys.argv) > 1 else "demo-20261111-010315"

conn = sqlite3.connect(RAIZ / "data" / "checkpoints.sqlite", check_same_thread=False)
estado = SqliteSaver(conn).get_tuple({"configurable": {"thread_id": HILO}}).checkpoint["channel_values"]

evaluaciones = {e["url"]: e for e in estado["evaluaciones"]}
priorizadas = {p["url"]: p for p in estado["priorizadas"]}
cartas = {c["url"]: c for c in estado["cartas"]}
pasan = {c["url"] for c in estado["candidatas"]}

ofertas = []
for o in DEMO:
    u = o["url"]
    item = {"titulo": o["titulo"], "empresa": o["empresa"], "fuente": o["fuente"], "url": u, "pasa": u in pasan}
    if u in evaluaciones:
        e, p = evaluaciones[u], priorizadas[u]
        item.update(llm=e["puntaje"], fortalezas=e["fortalezas"], idioma=e["idioma"], mercado=p["prob"], final=p["puntaje"])
    if u in cartas:
        c = cartas[u]
        item.update(id=c["id"], correo=c["correo"], intentos=c["intentos"], aprobada=not c["requiere_revision"])
    ofertas.append(item)

# las métricas salen en el orden en que terminaron los nodos
met = estado["metricas"]
por_nodo = lambda n: [m for m in met if m["nodo"] == n]  # noqa: E731

carta_txt = (RAIZ / "docs" / "fuentes" / "carta.txt").read_text(encoding="utf-8").splitlines()
cuerpo = [l for l in carta_txt if l and not l.startswith("#") and not l.startswith("ASUNTO")]

datos = {
    "hilo": HILO,
    "revisadas": estado["revisadas"],
    "descartes": {k: v for k, v in estado["descartes"].items() if v},
    "ofertas": ofertas,
    "evaluador": [{"seg": m["seg"], "tokens": m["tokens"]} for m in por_nodo("evaluador")],
    "taller": [{"seg": m["seg"], "tokens": m["tokens"]} for m in por_nodo("redactor+revisor")],
    "tokens_total": sum(m["tokens"] for m in met),
    "postulaciones": [{"id": p.get("id"), "estado": p.get("estado"), "correo": p.get("correo")} for p in estado.get("postulaciones", [])],
    "carta": {"asunto": next(l for l in carta_txt if l.startswith("ASUNTO")).split(":", 1)[1].strip(), "cuerpo": cuerpo},
}
destino = Path(__file__).parent / "src" / "datos.json"
destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{destino}: {len(ofertas)} ofertas, {sum(o['pasa'] for o in ofertas)} pasan el filtro, {datos['tokens_total']:,} tokens")
