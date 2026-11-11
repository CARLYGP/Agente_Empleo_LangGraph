"""Portales y filtros por reglas (heredados del agente v1, AgenteEmpleo/agente_empleo.py).

El grafo de LangGraph usa FUENTES, DETALLE y las funciones de evaluación por reglas;
main() se conserva para poder correr la versión anterior por separado.

Agente de búsqueda de empleo: remoto total, perfil junior IA / datos.

Barre portales colombianos (Computrabajo, elempleo, Magneto no: ver README), LinkedIn,
Get on Board y portales remotos internacionales; abre la ficha de cada oferta para
confirmar modalidad, experiencia exigida e inglés; estima qué tan probable es que lo
acepten y manda por Gmail solo lo que no se haya enviado antes, de más a menos probable.

Uso:
    python agente_empleo.py                  # busca y envía el correo
    python agente_empleo.py --preview        # deja preview.html, sin enviar ni marcar como vistas
    python agente_empleo.py --ignorar-vistas # incluye también lo ya enviado (para probar el diseño)
"""
import html
import json
import re
import smtplib
import sys
import time
import traceback
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent   # raíz del proyecto
CONFIG = BASE / "config.json"
VISTAS = BASE / "vistas.json"
LOG = BASE / "data" / "agente.log"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

NOMBRE = "Carlos"
MAX_ANIOS = 2           # experiencia máxima exigida que se acepta
AFINIDAD_MINIMA = 8    # qué tan relacionada está con lo que buscas; por debajo no se envía
MAX_POR_CORREO = 35     # lo que no quepa queda para el día siguiente

# --- Perfil (de la hoja de vida) -------------------------------------------------
# Afinidad: qué tanto se parece la oferta a lo que buscas. (patrón, peso, etiqueta)
AFINIDAD = [
    (r"agentes? (?:de |con )?(?:ia|inteligencia artificial)|\bai agents?\b|\bagentic\b|agéntic|multiagente|multi-agent|orquestaci[oó]n de (?:agentes|llm)|langchain|langgraph|crewai|autogen", 4),
    (r"\bmcp\b|model context protocol", 4),
    (r"ia generativa|generative ai|\bgenai\b|\bllms?\b|\bgpt|\bclaude\b|openai|\bprompt|\brag\b", 4),
    (r"copilot", 3),
    (r"consultor[ae]? (?:de |en )?(?:ia|datos|inteligencia|anal[ií]tica)|ai consultant|data consultant", 2),
    (r"inteligencia artificial|\bia\b|\bai\b", 2),
    (r"power ?bi", 3),
    (r"\bdax\b", 2),
    (r"power automate|power platform|power apps", 3),
    (r"\bn8n\b", 3),
    (r"python", 2),
    (r"\bsql\b", 1),
    (r"machine learning|aprendizaje autom[aá]tico", 2),
    (r"visi[oó]n por computador|computer vision|\byolo", 2),
    (r"\bnlp\b|lenguaje natural|natural language", 2),
    (r"automatizaci|\bautomation\b", 2),
    (r"anal[ií]tica|analytics|an[aá]lisis de datos|data analy", 2),
    (r"ciencia de datos|data scien|cient[ií]fico de datos", 2),
]

# Herramientas que la oferta puede pedir. Las que están en la hoja de vida cuentan a favor,
# las que no, en contra (y se le avisan en el correo).
TIENE = {
    "Python": r"python|pandas|scikit|numpy", "Power BI": r"power ?bi", "DAX": r"\bdax\b",
    "Power Automate": r"power automate", "SQL": r"\bsql\b|postgres", "R": r"\bR\b(?= |,|/)",
    "Excel": r"\bexcel\b", "n8n": r"\bn8n\b",
    "Machine Learning": r"machine learning|\bml\b|aprendizaje autom", "Deep Learning": r"deep learning|pytorch|tensorflow|redes neuronales",
    "NLP": r"\bnlp\b|lenguaje natural", "LLMs": r"\bllms?\b|openai|\bgpt|\bclaude\b|ia generativa|generative ai|genai",
    "visión por computador": r"computer vision|visi[oó]n por computador|\byolo", "SharePoint": r"sharepoint",
    "ETL": r"\betl\b", "Power Query": r"power query", "APIs REST": r"\bapis?\b|\brest(?:ful)?\b", "Copilot": r"copilot",
    "SAP": r"\bsap\b", "estadística": r"estad[ií]stic|statistic",
}
NO_TIENE = {
    "Java": r"\bjava\b(?!script)", "TypeScript": r"typescript", "C#/.NET": r"c#|\.net\b", "React": r"\breact\b", "Node.js": r"node\.?js",
    "AWS": r"\baws\b|amazon web services|sagemaker|quicksight", "Azure": r"\bazure\b", "GCP": r"\bgcp\b|google cloud|bigquery",
    "Spark": r"\bspark\b|pyspark", "Databricks": r"databricks", "Snowflake": r"snowflake", "Tableau": r"tableau", "Looker": r"looker",
    "Airflow": r"airflow", "dbt": r"\bdbt\b", "Docker/Kubernetes": r"docker|kubernetes", "Terraform": r"terraform",
    "Salesforce": r"salesforce", "Scala": r"\bscala\b", "Kafka": r"kafka",
    "Power Apps": r"power apps", "UiPath": r"uipath", "MLOps": r"mlops", "Go": r"\bgolang\b",
}

TITULO_FUERA = re.compile(
    r"senior|\bsr\.?\b|\bssr\b|semi ?senior|\blead\b|l[ií]der|manager|gerente|director|jefe|head\b|"
    r"principal|staff|arquitect|architect|expert|coordinador|docente|profesor|teacher|tutor|ventas|"
    r"\bsales\b|comercial|soporte t[eé]cnico|recepcionista|auxiliar|editor de video|dise[ñn]ador|designer|"
    r"assistant|asistente|discapacidad|\bqa\b|odoo|financier|recruit|reclut|closer|setter|\bvp\b|"
    r"werkstudent|\bintern\b|internship|pasant|marketer|marketing|tester|talent|trading|servicenow|geoscien|"
    r"metering|master data|data entry|digitador|labell?ing|annotat|writer|redactor",
    re.I,
)
TITULO_TEMA = re.compile(
    r"dato|data|\bbi\b|power|anal[ií]|intelig|\bia\b|\bai\b|agent|llm|genai|generativ|machine|"
    r"\bml\b|automatiz|automation|copilot|mcp|cient[ií]fic|scien|business intel|insight|prompt|junior|\bjr\b",
    re.I,
)
UBICACION_OK = re.compile(
    r"colombia|latam|latin ?america|latinoam|south america|sudam|americas|worldwide|anywhere|global|"
    r"world|\bremote\b$|^remote$|bogot|medell|cali\b", re.I)

BUSQUEDAS_CT = [
    "inteligencia-artificial-remoto", "ia-generativa-remoto", "agentes-de-ia-remoto",
    "automatizacion-con-ia-remoto", "power-bi-remoto", "analista-de-datos-remoto",
    "ciencia-de-datos-remoto", "analista-bi-remoto", "power-platform-remoto",
    "data-analyst-remoto", "consultor-ia-remoto", "copilot-remoto",
]
BUSQUEDAS_EE = ["inteligencia-artificial", "analista-de-datos", "analista-power-bi", "ciencia-de-datos",
                "automatizacion", "analista-bi", "power-platform"]
BUSQUEDAS_LI = ["AI consultant", "inteligencia artificial", "generative AI", "AI agents", "LLM", "MCP",
                "Copilot Studio", "Power Platform", "Power BI", "data analyst", "analista de datos",
                "data scientist", "automatización IA", "junior data", "junior AI"]
BUSQUEDAS_GOB = ["data analyst", "analista de datos", "power bi", "inteligencia artificial", "AI", "LLM",
                 "machine learning", "data scientist"]
BUSQUEDAS_INTL = ["data analyst", "power bi", "business intelligence", "data scientist", "machine learning",
                  "AI engineer", "LLM", "generative AI", "AI agents", "automation", "junior data"]
ROCKETSHIP = [("colombia", "data-analyst"), ("colombia", "junior-data-analyst"), ("colombia", "data-scientist"),
              ("colombia", "ai-engineer"), ("latin-america", "junior-data-analyst"), ("latin-america", "data-analyst"),
              ("latin-america", "data-scientist"), ("latin-america", "ai-engineer"),
              ("latin-america", "business-intelligence-analyst"), ("latin-america", "machine-learning-engineer"),
              ("latin-america", "artificial-intelligence")]
ARC = ["data-analyst", "data-scientist", "machine-learning", "ai", "python"]
HIRINGLAT = ["data", "ai", "data-analyst", "analyst", "automation"]
WORKANA = ["power bi", "inteligencia artificial", "n8n", "automatizacion", "chatbot", "python datos", "agentes ia"]


def log(msg):
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linea)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def get(url, intentos=2):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-CO,es;q=0.9,en;q=0.8"})
            return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
        except Exception as e:
            if i == intentos - 1:
                log(f"  ! no se pudo leer {url[:100]}: {e}")
                return ""
            time.sleep(3)


def get_json(url):
    try:
        return json.loads(get(url) or "null")
    except ValueError:
        return None


def texto(fragmento):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", str(fragmento or ""), flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def next_data(s):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s, re.S)
    return json.loads(m.group(1)) if m else {}


def oferta(fuente, titulo, empresa, url, publicada="", salario="", detalle=None, ubicacion="", junior=False,
           local=False, freelance=False, dias=None):
    return dict(fuente=fuente, titulo=texto(titulo), empresa=texto(empresa), url=url, publicada=publicada,
                salario=salario, _detalle=detalle, ubicacion=ubicacion, junior=junior, local=local,
                freelance=freelance, dias=dias)


def dias_desde(ts):
    try:
        if isinstance(ts, (int, float)):
            d = datetime.fromtimestamp(ts if ts < 1e11 else ts / 1000, timezone.utc)
        else:
            d = datetime.fromisoformat(str(ts).replace("Z", "+00:00")[:25])
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - d).days)
    except Exception:
        return None


def dias_texto(p):
    """«Hace 3 días», «Ayer», «Hace 1 mes», «Publicado: Ayer»… → días."""
    p = (p or "").lower()
    if re.search(r"hora|minuto|hoy", p):
        return 0
    if "ayer" in p:
        return 1
    m = re.search(r"(\d+)\s*d[ií]a", p)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*semana", p)
    if m:
        return 7 * int(m.group(1))
    if "mes" in p:
        return 30
    return None


# --- Experiencia e inglés ---------------------------------------------------------

def anios_exigidos(t):
    """Menor cantidad de años de experiencia que pide el texto (None si no lo dice)."""
    t = t.lower()
    m = re.search(r"(\d+) años? de experiencia experiencia mínima", t)   # campo fijo de elempleo
    if m:
        return int(m.group(1))
    if "sin experiencia experiencia mínima" in t:
        return 0
    t = t.split(" || ")[0]   # LinkedIn: lo de después es su ficha de criterios («Sin experiencia» = nivel, no requisito)
    if re.search(r"\d+\s*meses\s*(?:y|a|-)\s*\d+\s*años?", t):   # «entre 6 meses y 2 años»
        return 0
    cand = []
    for m in re.finditer(r"(\d{1,2})\s*\+?\s*(?:(?:a|-|–|—|to)\s*\d+\s*\+?\s*)?(?:años?|years?|yrs)(\s+\w+)?", t):
        ctx = t[max(0, m.start() - 70): m.end() + 70]
        sigue = (m.group(2) or "").strip()
        antes = t[max(0, m.start() - 25): m.start()]
        if re.search(r"más de|over|for|trayectoria|durante|hace", antes) and "experien" not in ctx:
            continue   # antigüedad de la empresa, no requisito
        if re.search(r"experien|mínimo|minimum|at least", ctx) or sigue in ("of", "de", "en", "in", "across", "como", "as", "working"):
            n = int(m.group(1))
            if n <= 15:
                cand.append(n)
    if cand:
        return min(cand)
    if re.search(r"sin experiencia|no requiere experiencia|reci[eé]n graduad|new grad|\d+\s*(?:a|-)\s*\d+\s*meses|\d+\s*meses de experiencia", t):
        return 0
    return None


def ingles_alto(t):
    return bool(re.search(r"ingl[eé]s (?:avanzado|fluido|c1|c2|nativo)|(?:advanced|fluent|native|c1|c2)[\w\s-]{0,15}english|"
                          r"english[\w\s:(-]{0,15}(?:advanced|fluent|native|c1|c2)|biling[uü]e|bilingual", t, re.I))


def en_ingles(t):
    t = t.lower()
    return len(re.findall(r"\b(the|and|with|you|will)\b", t)) > len(re.findall(r"\b(el|la|con|para|los)\b", t))


# --- Fuentes colombianas y LinkedIn -----------------------------------------------

def computrabajo():
    ofertas = {}
    for q in BUSQUEDAS_CT:
        s = get(f"https://co.computrabajo.com/trabajo-de-{q}")
        for a in re.split(r"<article ", s)[1:]:
            t = re.search(r'class="js-o-link[^"]*"[^>]*href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', a, re.S)
            if not t:
                continue
            url = "https://co.computrabajo.com" + t.group(1).split("#")[0]
            partes = [p.strip() for p in re.split(r"\|+", html.unescape(re.sub(r"<[^>]+>", "|", a.split("</a>", 1)[1]))) if p.strip()]
            if "Remoto" not in partes:          # «Presencial y remoto» = híbrido, fuera
                continue
            ruido = {"Postulado", "Vista", "Se precisa Urgente", "Empleo destacado"}
            partes = [p for p in partes if p not in ruido and not re.fullmatch(r"\d,\d", p)]
            pub = next((p for p in partes if re.search(r"Hace|Ayer|de \w+$", p)), "")
            ofertas[url] = oferta("Computrabajo", t.group(2), partes[0] if partes else "", url, pub,
                                  next((p.replace(",00", "") for p in partes if p.startswith("$")), ""),
                                  local=True, dias=dias_texto(pub))
        time.sleep(1)
    return ofertas


def computrabajo_detalle(o):
    s = get(o["url"])
    a = s.find("Descripción de la oferta")
    b = s.find("Palabras clave", a)
    return texto(s[a:b if b > 0 else a + 8000]) if a >= 0 else ""


def elempleo():
    ofertas = {}
    for q in BUSQUEDAS_EE:
        s = get(f"https://www.elempleo.com/co/ofertas-empleo/trabajo-{q}/remoto")
        for b in s.split("result-item mb-3 bg-white")[1:]:
            u = re.search(r'href="(/co/ofertas-trabajo/[^"]+)"', b)
            if not u:
                continue
            url = "https://www.elempleo.com" + u.group(1)
            p = [x.strip() for x in re.split(r"\|+", html.unescape(re.sub(r"<[^>]+>", "|", b[:6000]))) if x.strip() and len(x.strip()) < 140]
            p = [x for x in p if not x.startswith('"') and x not in ("COP", "industry", "Salario")]
            pub = p[2] if len(p) > 2 else ""
            sal = p[3] if len(p) > 3 and "confidencial" not in p[3].lower() else ""
            ofertas[url] = oferta("elempleo", p[0].capitalize() if p else "", p[1] if len(p) > 1 else "", url, pub, sal,
                                  local=True, dias=dias_texto(pub))
        time.sleep(1)
    return ofertas


def elempleo_detalle(o):
    t = texto(get(o["url"]))
    a = t.find(o["titulo"][:25]) if o["titulo"] else -1
    return t[max(0, a):][:9000]


def linkedin():
    ofertas = {}
    for q in BUSQUEDAS_LI:
        for start in (0, 25):
            u = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode(
                {"keywords": q, "location": "Colombia", "f_WT": "2", "f_E": "1,2,3", "f_TPR": "r1209600", "start": start})
            s = get(u)
            for li in s.split("<li")[1:]:
                t = re.search(r'base-search-card__title">\s*(.*?)\s*<', li, re.S)
                h = re.search(r'href="(https://[^"?]+)', li)
                if not (t and h):
                    continue
                c = re.search(r'base-search-card__subtitle">.*?>\s*(.*?)\s*<', li, re.S)
                d = re.search(r'datetime="([^"]+)"', li)
                url = re.sub(r"^https://\w+\.linkedin", "https://www.linkedin", h.group(1))
                ofertas[url] = oferta("LinkedIn", t.group(1), c.group(1) if c else "", url,
                                      d.group(1) if d else "", dias=dias_desde(d.group(1)) if d else None)
            time.sleep(1.5)
    return ofertas


def linkedin_detalle(o):
    jid = re.findall(r"(\d{9,})", o["url"])
    if not jid:
        return ""
    s = get("https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/" + jid[-1])
    d = re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", s, re.S)
    crit = " ".join(re.findall(r"description__job-criteria-text[^>]*>\s*(.*?)\s*<", s, re.S))
    post = re.search(r'num-applicants__caption[^>]*>\s*(.*?)\s*<', s, re.S)
    if post:
        n = re.findall(r"\d+", post.group(1))
        o["postulantes"] = int(n[0]) if n else None
        o["postulantes_mas_de"] = bool(re.search(r"más de|over", post.group(1), re.I))
    if re.search(r"entry level|sin experiencia|internship|prácticas", crit, re.I):
        o["junior"] = True
    time.sleep(1)
    return texto(d.group(1)) + " || " + crit if d else ""


def getonboard():
    ofertas = {}
    for q in BUSQUEDAS_GOB:
        d = get_json("https://www.getonbrd.com/api/v0/search/jobs?" + urllib.parse.urlencode(
            {"query": q, "per_page": 100, "expand": '["company"]'})) or {}
        for j in d.get("data", []):
            a = j["attributes"]
            remoto = a["remote_modality"] == "fully_remote" or (a["remote_modality"] == "remote_local" and "Colombia" in str(a["countries"]))
            sen = (a.get("seniority") or {}).get("data", {}).get("id", 9)
            dias = dias_desde(a["published_at"])
            if not remoto or sen > 2 or (dias or 0) > 30:
                continue
            sal = f'USD {a["min_salary"]}–{a["max_salary"]}/mes' if a.get("min_salary") else ""
            url = f'https://www.getonbrd.com/jobs/{j["id"]}'
            empresa = (a.get("company") or {}).get("data", {}).get("attributes", {}).get("name", "")
            det = texto(" ".join(str(a.get(k) or "") for k in ("description", "functions", "desirable", "projects")))
            ofertas[url] = oferta("Get on Board", a["title"], empresa, url, "", sal, det, junior=sen <= 2, dias=dias)
        time.sleep(1)
    return ofertas


# --- Portales remotos internacionales ---------------------------------------------

def remotive():
    ofertas = {}
    for q in BUSQUEDAS_INTL:
        d = get_json("https://remotive.com/api/remote-jobs?" + urllib.parse.urlencode({"search": q, "limit": 100})) or {}
        for j in d.get("jobs", []):
            ofertas[j["url"]] = oferta("Remotive", j["title"], j["company_name"], j["url"], "", j.get("salary") or "",
                                       texto(j.get("description")), j.get("candidate_required_location", ""),
                                       dias=dias_desde(j.get("publication_date")))
        time.sleep(1)
    return ofertas


def remoteok():
    ofertas = {}
    for tag in ("data", "analyst", "ai", "machine-learning", "python"):
        for j in (get_json(f"https://remoteok.com/api?tag={tag}") or [])[1:]:
            if not isinstance(j, dict) or "position" not in j:
                continue
            sal = f'USD {j["salary_min"]:,}–{j["salary_max"]:,}/año' if j.get("salary_min") else ""
            ofertas[j["url"]] = oferta("RemoteOK", j["position"], j.get("company", ""), j["url"], "", sal,
                                       texto(j.get("description")) + " " + " ".join(j.get("tags") or []),
                                       j.get("location", ""), dias=dias_desde(j.get("epoch")))
        time.sleep(2)
    return ofertas


def himalayas():
    ofertas = {}
    for q in BUSQUEDAS_INTL:
        d = get_json("https://himalayas.app/jobs/api/search?" + urllib.parse.urlencode({"q": q, "country": "CO"})) or {}
        for j in d.get("jobs", []):
            url = j.get("applicationLink") or j.get("guid")
            sen = " ".join(j.get("seniority") or [])
            sal = f'{j.get("currency") or "USD"} {j["minSalary"]:,}–{j["maxSalary"]:,}' if j.get("minSalary") and j.get("maxSalary") else ""
            ofertas[url] = oferta("Himalayas", j["title"], j.get("companyName", ""), url, "", sal,
                                  texto(j.get("description")), ", ".join(j.get("locationRestrictions") or []) or "Worldwide",
                                  junior=bool(re.search(r"entry|junior", sen, re.I)), dias=dias_desde(j.get("pubDate")))
        time.sleep(1)
    return ofertas


def jobicy():
    ofertas = {}
    for ind in ("data-science", "engineering", "technical-support", "business"):
        d = get_json(f"https://jobicy.com/api/v2/remote-jobs?count=100&geo=latam&industry={ind}") or {}
        for j in d.get("jobs", []):
            ofertas[j["url"]] = oferta("Jobicy", j["jobTitle"], j.get("companyName", ""), j["url"], "", "",
                                       texto(j.get("jobDescription")), j.get("jobGeo", ""),
                                       junior=bool(re.search(r"entry|junior", str(j.get("jobLevel")), re.I)),
                                       dias=dias_desde(j.get("pubDate")))
        time.sleep(1)
    return ofertas


def workingnomads():
    ofertas = {}
    for j in get_json("https://www.workingnomads.com/api/exposed_jobs/") or []:
        ofertas[j["url"]] = oferta("Working Nomads", j["title"], j.get("company_name", ""), j["url"], "", "",
                                   texto(j.get("description")) + " " + str(j.get("tags", "")), j.get("location", ""),
                                   dias=dias_desde(j.get("pub_date")))
    return ofertas


def weworkremotely():
    ofertas = {}
    s = get("https://weworkremotely.com/remote-jobs.rss")
    for it in s.split("<item>")[1:]:
        g = lambda tag: texto(re.search(rf"<{tag}>(.*?)</{tag}>", it, re.S).group(1)) if re.search(rf"<{tag}>", it) else ""
        titulo = g("title")
        empresa, _, puesto = titulo.partition(": ")
        url = g("link") or g("guid")
        ofertas[url] = oferta("We Work Remotely", puesto or titulo, empresa, url, "", "",
                              texto(html.unescape(g("description"))), g("region") or "Anywhere",
                              dias=dias_desde(datetime.strptime(g("pubDate")[:25], "%a, %d %b %Y %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
                              if g("pubDate") else None)
    return ofertas


def remoterocketship():
    ofertas = {}
    for pais, rol in ROCKETSHIP:
        d = next_data(get(f"https://www.remoterocketship.com/country/{pais}/jobs/{rol}/"))
        for j in (d.get("props", {}).get("pageProps", {}).get("initialJobOpenings") or []):
            url = j.get("url") or ""
            if not url:
                continue
            comp = (j.get("company") or {}).get("name", "") if isinstance(j.get("company"), dict) else ""
            sr = j.get("salaryRange") or {}
            sal = f'USD {sr.get("min"):,}–{sr.get("max"):,}' if isinstance(sr, dict) and sr.get("min") and sr.get("max") else ""
            ofertas[url] = oferta("Remote Rocketship", j.get("roleTitle", ""), comp, url, "", sal,
                                  texto(j.get("jobDescriptionSummary")) + " " + " ".join(map(str, j.get("techStack") or [])),
                                  j.get("location") or "LATAM", junior=bool(j.get("isEntryLevel") or j.get("isJunior")),
                                  dias=dias_desde(j.get("created_at")))
        time.sleep(1.5)
    return ofertas


def arc():
    ofertas = {}
    for rol in ARC:
        pp = next_data(get(f"https://arc.dev/remote-jobs/{rol}")).get("props", {}).get("pageProps", {})
        for j in (pp.get("arcJobs") or []) + (pp.get("externalJobs") or []):
            paises = j.get("requiredCountries") or []
            if paises and "CO" not in paises:
                continue
            comp = (j.get("company") or {}).get("name") or ""
            url = f'https://arc.dev/remote-jobs/j/{j["urlString"]}-{j["randomKey"]}' if j.get("company", {}).get("urlString") is None \
                else f'https://arc.dev/remote-jobs/j/{j["company"]["urlString"]}-{j["urlString"]}-{j["randomKey"]}'
            if j["urlString"].startswith((j.get("company") or {}).get("urlString") or "\0"):
                url = f'https://arc.dev/remote-jobs/j/{j["urlString"]}-{j["randomKey"]}'
            nivel = " ".join([str(j.get("experienceLevel") or "")] + list(map(str, j.get("experienceLevels") or [])))
            cats = " ".join(c.get("name", "") for c in j.get("categories") or [])
            sal = f'USD {j["minHourlyRate"]}–{j["maxHourlyRate"]}/hora' if j.get("minHourlyRate") else ""
            ofertas[url] = oferta("Arc.dev", j["title"], comp, url, "", sal, cats + " " + nivel,
                                  "Worldwide" if not paises else "Colombia", junior=bool(re.search(r"junior|entry", nivel, re.I)),
                                  dias=dias_desde(j.get("postedAt")))
        time.sleep(1.5)
    return ofertas


def hiringlat():
    ofertas = {}
    for cat in HIRINGLAT:
        s = get(f"https://hiring.lat/jobs/{cat}")
        trozos = re.split(r'<a href="(/job/[^"]+)"', s)
        for i in range(1, len(trozos) - 1, 2):
            url = "https://hiring.lat" + trozos[i]
            partes = [p.strip() for p in re.split(r"\|+", html.unescape(re.sub(r"<[^>]+>", "|", trozos[i + 1][:4000]))) if p.strip()]
            partes = [p for p in partes if p not in ("Apply Now", "View Details", "/")]
            if not partes:
                continue
            emp = next((p[1:] for p in partes if p.startswith("@")), "")
            sal = next((p.strip("{}") for p in partes if p.startswith("{$") and p != "{$0-$0}"), "")
            ofertas[url] = oferta("hiring.lat", partes[0], emp, url, "", sal, None, "LATAM")
        time.sleep(1)
    return ofertas


def hiringlat_detalle(o):
    t = texto(get(o["url"]))
    a = t.find(o["titulo"][:30])
    return t[max(0, a):][:9000]


def remotelatinos():
    ofertas = {}
    s = get("https://www.remotelatinos.com/jobs")
    for b in s.split("w-dyn-item")[1:]:
        h = re.search(r'href="([^"]+)"', b)
        tit = re.search(r"<h\d[^>]*>([^<]{4,120})</h\d>", b)
        if h and tit:
            url = urllib.parse.urljoin("https://www.remotelatinos.com/", h.group(1))
            ofertas[url] = oferta("Remote Latinos", tit.group(1), "", url, "", "", texto(b), "LATAM")
    return ofertas


def workana():
    ofertas = {}
    for q in WORKANA:
        s = get("https://www.workana.com/jobs?" + urllib.parse.urlencode({"query": q, "language": "es"}))
        m = re.search(r":results-initials='([^']*)'", s)
        if not m:
            continue
        for j in json.loads(html.unescape(m.group(1))).get("results", []):
            url = "https://www.workana.com/job/" + j["slug"]
            hab = " ".join(x.get("anchorText", "") for x in j.get("skills") or [])
            props = re.findall(r"\d+", str(j.get("totalBids") or ""))
            o = oferta("Workana", texto(j["title"]), "", url, j.get("postedDate", ""), j.get("budget") or "",
                       texto(j.get("description")) + " " + hab, "Remoto", freelance=True, dias=dias_texto(j.get("postedDate")))
            o["postulantes"] = int(props[0]) if props else None
            ofertas[url] = o
        time.sleep(1.5)
    return ofertas


FUENTES = [("Computrabajo", computrabajo), ("elempleo", elempleo), ("LinkedIn", linkedin), ("Get on Board", getonboard),
           ("Remotive", remotive), ("RemoteOK", remoteok), ("Himalayas", himalayas), ("Jobicy", jobicy),
           ("Working Nomads", workingnomads), ("We Work Remotely", weworkremotely), ("Remote Rocketship", remoterocketship),
           ("Arc.dev", arc), ("hiring.lat", hiringlat), ("Remote Latinos", remotelatinos), ("Workana", workana)]
DETALLE = {"Computrabajo": computrabajo_detalle, "elempleo": elempleo_detalle, "LinkedIn": linkedin_detalle,
           "hiring.lat": hiringlat_detalle}


# --- Evaluación -------------------------------------------------------------------

def es_remoto(o, det):
    if o["fuente"] not in ("elempleo", "LinkedIn"):
        return True   # el portal ya lo filtra o lo etiqueta como remoto
    d = det.lower()
    if re.search(r"h[ií]brid|hybrid|presencial|on-?site|work from office|in the office|días? (a la semana )?en (la )?oficina|days a week in", d):
        if not re.search(r"100 ?% ?remot|fully remote|totalmente remot|remote work \(from anywhere\)", d):
            return False
    if o["fuente"] == "elempleo":
        return bool(re.search(r"modalidad:? ?(100 ?% ?)?remot|100 ?% ?remot|teletrabajo|trabajo remoto|totalmente remot", d))
    return True


def puede_aplicar_desde_colombia(o, det):
    if o["local"] or o["fuente"] in ("LinkedIn", "Get on Board", "Workana"):
        return True
    ub = (o.get("ubicacion") or "").strip()
    if not ub or UBICACION_OK.search(ub):
        # aun así, algunas dicen en el texto que solo contratan en EE. UU. o Europa
        return not re.search(r"(?:must|only)[\w\s]{0,30}(?:reside|based|located|live)[\w\s]{0,20}(?:in the )?(?:us|usa|united states|uk|europe|eu|canada)\b"
                             r"|us[- ]based only|us citizens|eligible to work in the (?:us|united states)", det, re.I)
    return False


def afinidad(o, det):
    t = (o["titulo"] + " " + det).lower()
    p = sum(peso for patron, peso in AFINIDAD if re.search(patron, t))
    if re.search(r"\bia\b|\bai\b|agent|llm|genai|generativ|copilot|mcp|consultor|consultant|power bi|power platform|data|dato", o["titulo"], re.I):
        p += 3
    return p


def herramientas(texto_oferta):
    tiene = [k for k, p in TIENE.items() if re.search(p, texto_oferta, re.I)]
    falta = [k for k, p in NO_TIENE.items() if re.search(p, texto_oferta, re.I)]
    return tiene, falta


def probabilidad(o, det):
    """Estimación (0-100) de qué tan probable es que te llamen. No es una ciencia: es un orden razonable."""
    t = o["titulo"] + " " + det
    tiene, falta = herramientas(t)
    anios = o["anios"]
    p = 40
    p += {0: 22, 1: 12, 2: 0}.get(anios, 4)                 # None (no lo dice) = algo a favor
    if o["junior"] or re.search(r"junior|\bjr\b|trainee|practicante|entry|associate|aprendiz", o["titulo"], re.I):
        p += 10
    if tiene or falta:
        p += round((len(tiene) / (len(tiene) + len(falta)) - 0.5) * 40)
    ingles = ingles_alto(t)
    if ingles:
        p -= 12
    elif en_ingles(det) and not o["local"]:
        p -= 3
    if o["local"]:
        p += 6                                              # mercado colombiano, en español, menos competencia global
    elif not o["freelance"] and o["fuente"] not in ("LinkedIn", "Get on Board"):
        p -= 6                                              # portal internacional: compites con toda LATAM
    if o.get("dias") is not None:
        p += 6 if o["dias"] <= 3 else (-6 if o["dias"] > 25 else 0)
    n = o.get("postulantes")
    if n is not None:
        p += 6 if n < 25 else (-8 if n >= 100 else 0)
    if re.search(r"research|investigaci|pre-?training|post-?training|fine-?tuning|phd|doctor", o["titulo"], re.I):
        p -= 12               # puestos de investigación: suelen pedir maestría o publicaciones
    m = re.search(r"(\d{2,3}),?\d{3}", o.get("salario") or "")
    if m and "USD" in (o.get("salario") or "") and int(m.group(1)) >= 60:
        p -= 10               # USD 60.000+ al año: en la práctica buscan a alguien con más años
    if anios is None and not o["local"] and o["fuente"] != "LinkedIn":
        p = min(p, 60)        # sin dato de experiencia y con competencia de toda LATAM: nunca «buena opción»
    o.update(tiene=tiene, falta=falta, ingles=ingles)
    return max(5, min(95, p))


# --- Correo -----------------------------------------------------------------------

def _y(lista):
    return lista[0] if len(lista) == 1 else ", ".join(lista[:-1]) + " y " + lista[-1]


def por_que(o):
    """Una o dos frases en lenguaje normal: por qué tienes chance y qué te puede frenar."""
    v = sum(map(ord, o["url"]))          # misma oferta, misma frase; ofertas distintas, frases distintas
    elige = lambda opciones: opciones[v % len(opciones)]
    partes = []
    a = o["anios"]
    if a == 0:
        partes.append(elige(["No piden experiencia previa.", "Aceptan perfiles sin experiencia.",
                             "Es para alguien que está empezando."]))
    elif a == 1:
        partes.append(elige(["Piden 1 año; con la práctica en Lactalis y los proyectos de consultoría estás cerca.",
                             "Pide un año: tu práctica más lo de Verytel y VisionFund casi lo cubre.",
                             "Un año de experiencia mínimo, que puedes defender con tus proyectos."]))
    elif a == 2:
        partes.append(elige(["Piden 2 años, así que es un estirón.", "Dicen 2 años, pero con junior suelen ser flexibles.",
                             "Piden 2 años; vale la pena si en la carta muestras los proyectos."]))
    if o["tiene"]:
        y = _y(o["tiene"][:4])
        partes.append(elige([f"Usan {y}, que ya manejas.", f"Trabajan con {y}, justo lo tuyo.",
                             f"De lo que piden, ya tienes {y}."]))
    frenos = []
    if o["falta"]:
        x = _y(o["falta"][:3])
        frenos.append(elige([f"te falta {x}", f"piden {x}, que no est{'án' if len(o['falta']) > 1 else 'á'} en tu hoja de vida", f"te pueden preguntar por {x}"]))
    if o["ingles"]:
        frenos.append("exigen inglés avanzado")
    n = o.get("postulantes")
    if n and n >= 100:
        frenos.append(f"ya hay {'más de ' if o.get('postulantes_mas_de') else ''}{n} postulantes")
    if frenos:
        f = "; ".join(frenos)
        partes.append(f[0].upper() + f[1:] + ".")
    if a is None and not o["freelance"]:
        partes.append(elige(["No dicen cuánta experiencia piden.", "La oferta no aclara la experiencia.",
                             "No especifican años de experiencia."]))
    return " ".join(partes)


def linea_meta(o):
    o["salario"] = re.sub(r"([\d.,]+)\s*[–-]\s*\1\b", r"\1", o.get("salario") or "")   # «55–55» → «55»
    bits = [o["empresa"] or None, o["salario"] or None, o["fuente"]]
    d = o.get("dias")
    if d is not None:
        bits.append("publicada hoy" if d == 0 else "ayer" if d == 1 else f"hace {d} días")
    return " · ".join(html.escape(b) for b in bits if b)


def armar_correo(ofertas, revisadas, n_fuentes):
    e = html.escape
    empleos = [o for o in ofertas if not o["freelance"]]
    freel = [o for o in ofertas if o["freelance"]]
    altas = [o for o in empleos if o["prob"] >= 65]
    medias = [o for o in empleos if 45 <= o["prob"] < 65]
    bajas = [o for o in empleos if o["prob"] < 45]

    def item_largo(o):
        return f"""<li style="margin:0 0 18px">
<a href="{e(o['url'])}" style="color:#1a4fb4;font-weight:600;text-decoration:none">{e(o['titulo'])}</a><br>
<span style="color:#5f6368;font-size:13px">{linea_meta(o)}</span><br>
<span style="font-size:14px">{e(por_que(o))}</span></li>"""

    def item_corto(o):
        return f"""<li style="margin:0 0 8px"><a href="{e(o['url'])}" style="color:#1a4fb4;text-decoration:none">{e(o['titulo'])}</a>
<span style="color:#5f6368;font-size:13px"> · {linea_meta(o)}</span></li>"""

    def seccion(titulo, intro, items, largo=True):
        if not items:
            return ""
        cuerpo = "".join(item_largo(o) if largo else item_corto(o) for o in items)
        return f"""<p style="margin:26px 0 4px;font-size:15px;font-weight:600">{titulo}</p>
<p style="margin:0 0 12px;color:#5f6368;font-size:13px">{intro}</p>
<ol style="margin:0;padding-left:20px">{cuerpo}</ol>"""

    total = len(empleos)
    if altas:
        apertura = (f"Hoy encontré {total} ofertas remotas nuevas. Si solo tienes tiempo para unas pocas, "
                    f"empieza por {'esta' if len(altas) == 1 else f'estas {len(altas)}'}: es donde tu perfil calza mejor.")
    elif total:
        apertura = f"Hoy encontré {total} ofertas remotas nuevas. Ninguna es un encaje perfecto, pero varias valen el intento."
    else:
        apertura = "Hoy no apareció ningún empleo nuevo que cumpla los filtros."

    return f"""<!doctype html><html><body style="margin:0;padding:0;background:#ffffff">
<div style="max-width:600px;margin:0 auto;padding:24px 18px;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;font-size:15px;line-height:1.5;color:#202124">
<p style="margin:0 0 12px">Hola {NOMBRE},</p>
<p style="margin:0 0 4px">{apertura}</p>
{seccion("Buenas opciones", "Piden poca experiencia y usan herramientas que ya manejas.", altas)}
{seccion("Vale la pena intentar", "Te falta algo de lo que piden, pero el resto encaja.", medias)}
{seccion("Más difíciles", "Mucha competencia, inglés avanzado o herramientas que no tienes. Mándalas si te sobra tiempo.", bajas, largo=False)}
{seccion("Proyectos freelance (Workana)", "Trabajos por proyecto: sirven para sumar experiencia mientras sale el empleo.", freel, largo=False)}
<p style="margin:30px 0 0;padding-top:14px;border-top:1px solid #e8eaed;color:#80868b;font-size:12px">
Revisé {revisadas} ofertas en {n_fuentes} portales. Solo te mando trabajos 100&nbsp;% remotos que se puedan hacer desde Colombia y no pidan más de {MAX_ANIOS} años; lo que ya te mandé no se repite.
El orden es una estimación (experiencia que piden, herramientas que tienes y te faltan, inglés, competencia y qué tan reciente es), no una garantía.
Indeed, Glassdoor, Upwork, FlexJobs y remote.co no dejan revisarlos automáticamente: esos toca mirarlos a mano.</p>
</div></body></html>"""


def enviar(cuerpo, n, n_altas):
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    msg = MIMEMultipart("alternative")
    if n_altas:
        msg["Subject"] = f"{n} ofertas remotas nuevas, {n_altas} con buena pinta"
    else:
        msg["Subject"] = f"{n} ofertas remotas nuevas para revisar"
    msg["From"] = f"Agente de empleo <{cfg['gmail']}>"
    msg["To"] = cfg.get("destinatario") or cfg["gmail"]
    msg.attach(MIMEText(cuerpo, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(cfg["gmail"], cfg["contrasena_aplicacion"].replace(" ", ""))
        s.send_message(msg)
    log(f"Correo enviado a {msg['To']} con {n} ofertas")


# --- Principal --------------------------------------------------------------------

def main(preview=False, ignorar_vistas=False):
    log("==== inicio" + (" (preview)" if preview else "") + (" (ignorando vistas)" if ignorar_vistas else ""))
    vistas = json.loads(VISTAS.read_text(encoding="utf-8")) if VISTAS.exists() else {}
    ya = {} if ignorar_vistas else vistas

    todas = {}
    for nombre, fuente in FUENTES:
        try:
            r = fuente()
            log(f"{nombre}: {len(r)} ofertas")
            todas.update(r)
        except Exception:
            log(f"{nombre}: ERROR\n{traceback.format_exc()}")

    candidatas = [o for u, o in todas.items()
                  if u not in ya and TITULO_TEMA.search(o["titulo"]) and not TITULO_FUERA.search(o["titulo"])]
    unicas = {}   # la misma oferta aparece en varios portales o por ciudad
    for o in candidatas:
        clave = (re.sub(r"\W+", " ", o["titulo"].lower()).strip(), re.sub(r"\W+", " ", o["empresa"].lower()).strip())
        if clave not in unicas or (o["local"] and not unicas[clave]["local"]):
            unicas[clave] = o
    candidatas = list(unicas.values())
    log(f"Candidatas por título: {len(candidatas)}")

    elegidas, descartes = [], {"sin ficha": 0, "no remota": 0, "fuera de Colombia/LATAM": 0, "mucha experiencia": 0, "poco afín": 0}
    for o in candidatas:
        try:
            det = o["_detalle"] if o["_detalle"] is not None else DETALLE.get(o["fuente"], lambda x: "")(o)
        except Exception as ex:
            log(f"  ! detalle {o['url'][:80]}: {ex}")
            det = ""
        vistas[o["url"]] = datetime.now().strftime("%Y-%m-%d")
        motivo = None
        if not det:
            motivo = "sin ficha"
        elif not es_remoto(o, det):
            motivo = "no remota"
        elif not puede_aplicar_desde_colombia(o, det):
            motivo = "fuera de Colombia/LATAM"
        else:
            o["anios"] = anios_exigidos(det)
            if o["anios"] is not None and o["anios"] > MAX_ANIOS:
                motivo = "mucha experiencia"
            elif afinidad(o, det) < AFINIDAD_MINIMA:
                motivo = "poco afín"
        if motivo:
            descartes[motivo] += 1
            continue
        o["prob"] = probabilidad(o, det)
        o.pop("_detalle", None)
        elegidas.append(o)

    elegidas.sort(key=lambda o: (o["freelance"], -o["prob"]))
    enviadas = elegidas[:MAX_POR_CORREO]
    for o in elegidas[MAX_POR_CORREO:]:
        vistas.pop(o["url"], None)        # no cupieron: que salgan mañana
    log(f"Elegidas: {len(elegidas)} (van {len(enviadas)}) | descartes: {descartes}")

    n_altas = sum(1 for o in enviadas if not o["freelance"] and o["prob"] >= 65)
    cuerpo = armar_correo(enviadas, len(todas), len(FUENTES))
    if preview:
        (BASE / "preview.html").write_text(cuerpo, encoding="utf-8")
        log("preview.html escrito; no se envió nada ni se marcaron vistas")
        return
    if enviadas:
        enviar(cuerpo, len([o for o in enviadas if not o["freelance"]]), n_altas)
    else:
        log("Nada nuevo hoy: no se envía correo")
    VISTAS.write_text(json.dumps(vistas, ensure_ascii=False, indent=0), encoding="utf-8")


if __name__ == "__main__":
    try:
        main(preview="--preview" in sys.argv, ignorar_vistas="--ignorar-vistas" in sys.argv)
    except Exception:
        log("ERROR GENERAL\n" + traceback.format_exc())
        raise
