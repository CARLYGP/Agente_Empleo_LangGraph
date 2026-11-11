"""Ofertas ficticias para correr el grafo sin internet (python main.py --demo) y para las pruebas.
Los correos usan el dominio reservado .invalid: aunque algo fallara, nunca llegarían a nadie."""
from agente.portales import oferta

DEMO = [
    oferta("Computrabajo", "Ingeniero de IA Junior (agentes LLM)", "Andina Analytics SAS",
           "https://demo.invalid/oferta/1", local=True, dias=1, detalle=
           "Modalidad 100% remoto. Buscamos ingeniero de IA junior para construir agentes con LLM (LangGraph, RAG) "
           "e integrarlos con APIs REST en Python. Deseable experiencia con Power BI y automatización de procesos. "
           "Experiencia mínima: 1 año. Interesados enviar hoja de vida a talento@andina-analytics.invalid"),
    oferta("Computrabajo", "Analista de Datos Junior - Power BI", "Lácteos del Valle",
           "https://demo.invalid/oferta/2", local=True, dias=2, detalle=
           "Trabajo remoto. Analista de datos junior con Power BI, DAX, SQL y Python para tableros de cartera y ventas. "
           "Automatización con Power Automate. Sin experiencia o hasta 1 año. Postúlate en el portal."),
    oferta("Remotive", "Junior AI Engineer (Computer Vision)", "VisionWorks",
           "https://demo.invalid/oferta/3", ubicacion="LATAM", dias=3, detalle=
           "Remote, LATAM. We are looking for a junior AI engineer with Python, computer vision (YOLO) and machine learning "
           "experience to deploy real-time detection models. 1 year of experience. English B1 or higher. "
           "Please send your resume to jobs@visionworks.invalid"),
    oferta("Computrabajo", "Senior Data Architect", "Big Corp", "https://demo.invalid/oferta/4", local=True,
           detalle="Remoto. Arquitecto de datos senior, 8 años de experiencia en Spark y Databricks."),
    oferta("Remotive", "Data Analyst (Tableau, AWS)", "Cloudy", "https://demo.invalid/oferta/5", ubicacion="Worldwide",
           detalle="Remote. Data analyst with Tableau, AWS, Snowflake and dbt. Minimum 5 years of experience in analytics."),
]

FUENTES_DEMO = [
    ("Computrabajo", lambda: {o["url"]: dict(o) for o in DEMO if o["fuente"] == "Computrabajo"}),
    ("Remotive", lambda: {o["url"]: dict(o) for o in DEMO if o["fuente"] == "Remotive"}),
]
