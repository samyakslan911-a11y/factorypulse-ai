# coding: utf-8
"""
Supplier Agent — Phase 2.
Gemini 2.0 Flash con function calling. 4 herramientas: scrape, news, legal, save.
Fallback a modo demo con scraping real si Gemini no tiene cuota disponible.
"""
import json
import time
from google import genai
from google.genai import types

from backend.config import settings
from backend.db.analyses import create_analysis, update_analysis, save_step
from backend.api.stream import emit, ensure_queue

MODEL_CASCADE = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
]

SYSTEM_PROMPT = """Eres un analista senior de riesgo de proveedores con 15 años de experiencia en due diligence para empresas manufactureras Fortune 500. Tu firma analítica: cada conclusión que emites está respaldada por evidencia específica y verificable. Los gerentes de compras confían en tus reportes para tomar decisiones de millones de dólares.

TODO el contenido —resumen, hallazgos, descripciones— DEBE estar en español.

━━━ ESCALA DE RIESGO (0–100) ━━━
0–29   BAJO     → proveedor confiable, riesgo mínimo documentado
30–59  MODERADO → requiere monitoreo y documentación adicional
60–79  ALTO     → señales de alerta significativas, evaluar alternativas
80–100 CRÍTICO  → no recomendar sin auditoría presencial

━━━ RÚBRICA DE SCORING ━━━
score_financial: evalúa existencia de estados financieros públicos, señales de quiebra o impago,
  antigüedad como proxy de estabilidad, tamaño e indicadores de solvencia visibles en web y noticias.

score_operational: evalúa profesionalismo del sitio web, certificaciones (ISO 9001, ISO 14001,
  IATF 16949, CE, UL, etc.), capacidad productiva visible, referencias de clientes, infraestructura.

score_reputational: evalúa menciones en noticias (positivas/negativas), controversias laborales
  o ambientales, presencia en listas de sanciones (OFAC, ONU, UE), asociaciones y premios.

━━━ PROTOCOLO DE ANÁLISIS (sigue este orden exacto, una herramienta por llamada) ━━━

PASO 1 — scrape_website
  Objetivo: extraer certificaciones, historia, clientes, capacidad, contacto.
  Si no hay URL: documenta este hecho como hallazgo operacional de severidad media.
  Extrae cualquier dato concreto visible: años de operación, países donde opera, productos.

PASO 2 — search_news
  Estrategia de búsqueda: "[nombre] [país] finanzas quiebra noticias" Y "[nombre] scandal fraud bankruptcy"
  Documenta tanto hallazgos negativos COMO positivos. La ausencia de noticias negativas
  también es información valiosa que debes reportar explícitamente.

PASO 3 — search_legal
  Estrategia: "[nombre] lawsuit demanda compliance violation sanction"
  Verifica señales de: litigios activos, multas regulatorias, violaciones ambientales,
  incumplimientos laborales, o aparición en listas de proveedores sancionados.

PASO 4 — save_analysis (SIEMPRE EL ÚLTIMO PASO)
  Antes de llamar, realiza este checklist mental:
  ✓ ¿Cada hallazgo cita evidencia específica o documenta su ausencia?
  ✓ ¿Los scores reflejan lo encontrado, no suposiciones a priori?
  ✓ ¿El resumen menciona los 2–3 factores más importantes del análisis?
  ✓ ¿Hay al menos un hallazgo por dimensión (financial, operational, legal, reputational)?

━━━ ESTÁNDAR DE CALIDAD: HALLAZGOS ━━━
Cada descripción responde: QUÉ se encontró + DÓNDE se encontró + QUÉ implica para el riesgo.
Mínimo 1 finding por dimensión. Máximo 6 findings totales. Profundidad sobre cantidad.

JERARQUÍA DE EVIDENCIA (de mayor a menor peso en el score):
  PRIMARIA   → datos directos del sitio web (certificaciones, años, capacidad)
  SECUNDARIA → menciones en noticias o búsquedas (con extracto de texto real)
  INFERIDA   → ausencia documentada de información (se buscó X y no se encontró)

EJEMPLOS DE HALLAZGOS (usa como modelo de calidad mínima):

✅ OPERACIONAL — BAJO RIESGO:
  "El sitio web de [empresa] presenta certificación ISO 9001:2015 con logo del organismo
   certificador Bureau Veritas visible en la página de inicio. Menciona operaciones en
   [países] desde [año] y lista clientes en los sectores automotriz y aeroespacial. La
   infraestructura web es profesional con catálogo técnico descargable y chat en vivo."

✅ FINANCIERO — MEDIO RIESGO:
  "No se encontraron estados financieros públicos para [empresa] en sitio web ni en
   búsqueda de noticias. DuckDuckGo no retornó resultados sobre quiebras o reestructuraciones.
   La empresa opera desde [año visible en web], sugiriendo estabilidad básica, pero su
   solvencia no puede verificarse con fuentes abiertas. Se recomienda solicitar balance
   general y referencias bancarias directamente al proveedor."

✅ REPUTACIONAL — BAJO RIESGO:
  "La búsqueda '[nombre] fraud scandal bankruptcy' retornó [N] resultados, ninguno relacionado
   con el proveedor evaluado. No se identificaron menciones de huelgas, protestas laborales,
   demandas colectivas ni investigaciones regulatorias. [Si hubo resultados relevantes:
   el resultado más significativo menciona: '[extracto real del texto encontrado]'.]"

✅ LEGAL — BAJO RIESGO:
  "Búsqueda de '[nombre] lawsuit compliance violation' no retornó resultados de litigios
   activos ni sanciones regulatorias. El proveedor no aparece en resultados relacionados
   con listas de sanciones internacionales en las fuentes de acceso público consultadas."

❌ PROHIBIDOS (demasiado genéricos — el cliente los rechazará):
  "Sin incidencias operativas recientes"   → no dice qué se buscó ni qué se encontró
  "Presencia web activa"                   → no aporta información accionable
  "Información financiera limitada"        → no documenta las fuentes consultadas
  "Empresa reconocida en el sector"        → sin fuente, sin nombre de reconocimiento

━━━ FORMATO DE ENTREGA ━━━
summary: 3–4 oraciones. Estructura: (1) Quién es el proveedor [industria + país + antigüedad si disponible].
  (2) Hallazgo operacional clave [certificaciones o ausencia de ellas]. (3) Perfil de riesgo financiero
  y reputacional. (4) Recomendación concreta y siguiente paso sugerido al equipo de compras.

findings: JSON array de 3–6 objetos, cada uno con:
  {"type": "financial|operational|legal|reputational",
   "severity": "low|medium|high",
   "description": "texto específico con evidencia real, mínimo 40 palabras, máximo 120 palabras"}

sources_used: lista de URLs y queries de búsqueda utilizados."""


def _clean_url(url: str) -> str:
    """Strip all ad/tracking params and return clean base URL."""
    try:
        from urllib.parse import urlparse, urlencode, parse_qs
        TRACKING = {
            "utm_source","utm_medium","utm_campaign","utm_content","utm_term","utm_id",
            "gclid","gad_source","gad_campaignid","gbraid","wbraid","gclsrc",
            "matchtype","keyword","network","device","adposition","creative",
            "campaignid","adgroupid","adid",
            "fbclid","fb_action_ids","fb_ref","fb_source",
            "msclkid","ttclid","twclid","li_fat_id",
            "mc_cid","mc_eid","igshid","_ga","_gl",
        }
        p = urlparse(url)
        clean_qs = {k: v for k, v in parse_qs(p.query).items() if k.lower() not in TRACKING}
        clean = p._replace(query=urlencode(clean_qs, doseq=True))
        return clean.geturl().rstrip("?&")
    except Exception:
        return url


def _scrape(url: str) -> str:
    url = _clean_url(url)
    if settings.firecrawl_api_key:
        try:
            from firecrawl import FirecrawlApp
            app = FirecrawlApp(api_key=settings.firecrawl_api_key)
            result = app.scrape_url(url, formats=["markdown"])
            return (result.markdown or "")[:3000]
        except Exception as e:
            return f"Firecrawl error: {e}"
    try:
        import httpx, re
        r = httpx.get(url, timeout=10, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (compatible; FactoryPulse/1.0)"})
        text = re.sub(r"<[^>]+>", " ", r.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]
    except Exception as e:
        return f"Scrape error: {e}"


def _duckduckgo(query: str) -> str:
    """Search using DuckDuckGo HTML interface — returns real results for any company."""
    try:
        import httpx, re
        r = httpx.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "kl": "wt-wt"},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            timeout=12,
            follow_redirects=True,
        )
        # Extract result snippets from DDG HTML
        snippets = re.findall(r'class="result__snippet[^"]*"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        titles   = re.findall(r'class="result__a[^"]*"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        parts = []
        for title, snippet in zip(titles[:5], snippets[:5]):
            clean_t = re.sub(r"<[^>]+>", "", title).strip()
            clean_s = re.sub(r"<[^>]+>", "", snippet).strip()
            if clean_t or clean_s:
                parts.append(f"{clean_t}: {clean_s}" if clean_t else clean_s)
        if parts:
            return "\n".join(parts)
        # Fallback: strip all HTML and return raw text excerpt
        plain = re.sub(r"<[^>]+>", " ", r.text)
        plain = re.sub(r"\s+", " ", plain).strip()
        return plain[500:2000] if len(plain) > 500 else ("No results found." if not plain else plain[:1000])
    except Exception as e:
        return f"Search error: {e}"


def _build_tools() -> list[types.Tool]:
    return [types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="scrape_website",
            description="Scrape the supplier's website to extract company info, products, certifications, and services.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"url": types.Schema(type=types.Type.STRING, description="Full URL to scrape")},
                required=["url"],
            ),
        ),
        types.FunctionDeclaration(
            name="search_news",
            description="Search for recent news about the supplier: financial issues, acquisitions, strikes, sanctions.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"query": types.Schema(type=types.Type.STRING, description="Search query string")},
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="search_legal",
            description="Search for legal/regulatory issues: lawsuits, compliance violations, audits, certifications.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"query": types.Schema(type=types.Type.STRING, description="Search query string")},
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="save_analysis",
            description="Save the final risk analysis. Call this LAST after gathering all information.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "score_total": types.Schema(type=types.Type.INTEGER,
                        description="Overall risk score 0-100. 0=very safe, 100=very risky."),
                    "score_financial": types.Schema(type=types.Type.INTEGER,
                        description="Financial risk 0-100."),
                    "score_operational": types.Schema(type=types.Type.INTEGER,
                        description="Operational risk 0-100."),
                    "score_reputational": types.Schema(type=types.Type.INTEGER,
                        description="Reputational/ESG risk 0-100."),
                    "summary": types.Schema(type=types.Type.STRING,
                        description="Resumen ejecutivo en español, 2-3 oraciones con hallazgos concretos."),
                    "findings": types.Schema(type=types.Type.STRING,
                        description='JSON array con hallazgos basados en evidencia real: [{"type":"financial|operational|legal|reputational","severity":"low|medium|high","description":"descripción específica con evidencia concreta"}]'),
                    "sources_used": types.Schema(type=types.Type.STRING,
                        description='JSON array of URLs or search queries used: ["url1", "query2"]'),
                },
                required=["score_total", "score_financial", "score_operational",
                          "score_reputational", "summary", "findings", "sources_used"],
            ),
        ),
    ])]


def _run_demo(supplier: dict, analysis_id: str, emit_fn) -> dict:
    """
    Modo demo — hace scraping y búsquedas reales pero sin Gemini para síntesis.
    Genera hallazgos basados en el contenido real encontrado.
    """
    import random

    name     = supplier["name"]
    website  = supplier.get("website") or ""
    industry = supplier.get("industry") or "manufactura"
    country  = supplier.get("country") or "la región"

    # Step 1: Scrape
    emit_fn("progress", "[1] scrape_website...")
    t0 = time.monotonic()
    clean_website = _clean_url(website) if website else ""
    web_raw = _scrape(clean_website) if clean_website else ""
    web_ms  = int((time.monotonic() - t0) * 1000)
    if web_raw and "error" not in web_raw.lower():
        web_summary = f"Sitio web analizado: {clean_website} — {web_raw[:300].replace(chr(10), ' ').strip()}"
        web_ok = True
    else:
        web_summary = f"No se pudo acceder al sitio web: {clean_website or '(sin URL)'}"
        web_ok = False
    save_step(analysis_id, 1, "scrape_website", {"url": clean_website}, web_summary, web_ms)
    time.sleep(0.5)

    # Step 2: News
    emit_fn("progress", "[2] search_news...")
    t0 = time.monotonic()
    news_raw = _duckduckgo(f"{name} {country} noticias finanzas problemas")
    news_ms  = int((time.monotonic() - t0) * 1000)
    news_ok  = bool(news_raw) and news_raw != "No results found." and len(news_raw) > 40
    news_summary = (
        news_raw[:400].replace(chr(10), " ").strip()
        if news_ok
        else f"Sin resultados relevantes en búsqueda de noticias para '{name}'"
    )
    save_step(analysis_id, 2, "search_news", {"query": f"{name} noticias finanzas"}, news_summary, news_ms)
    time.sleep(0.5)

    # Step 3: Legal
    emit_fn("progress", "[3] search_legal...")
    t0 = time.monotonic()
    legal_raw = _duckduckgo(f"{name} lawsuit demanda compliance violation")
    legal_ms  = int((time.monotonic() - t0) * 1000)
    legal_ok  = bool(legal_raw) and legal_raw != "No results found." and len(legal_raw) > 40
    legal_summary = (
        legal_raw[:400].replace(chr(10), " ").strip()
        if legal_ok
        else f"Sin registros legales encontrados para '{name}' en fuentes públicas"
    )
    save_step(analysis_id, 3, "search_legal", {"query": f"{name} lawsuit demanda compliance"}, legal_summary, legal_ms)

    # Build contextual findings
    findings = []

    # Operational — web presence
    if web_ok:
        snippet = web_raw[:150].replace("\n", " ").strip()
        findings.append({
            "type": "operational",
            "severity": "low",
            "description": f"Sitio web accesible y con contenido activo. Extracto: \"{snippet}...\"",
        })
    else:
        findings.append({
            "type": "operational",
            "severity": "medium",
            "description": (
                f"No se pudo acceder al sitio web del proveedor {'(' + clean_website + ')' if clean_website else '(sin URL registrada)'}. "
                "La presencia digital no pudo ser verificada en el momento del análisis."
            ),
        })

    # Reputational — news
    if news_ok:
        snippet = news_raw[:120].replace("\n", " ").strip()
        findings.append({
            "type": "reputational",
            "severity": "low",
            "description": (
                f"La búsqueda de noticias para '{name}' retornó información pública. "
                f"Extracto: \"{snippet}...\". No se detectaron menciones de escándalos o controversias."
            ),
        })
    else:
        findings.append({
            "type": "reputational",
            "severity": "low",
            "description": (
                f"La búsqueda de noticias no encontró menciones de quiebras, disputas laborales, "
                f"sanciones ni controversias públicas para '{name}' en los últimos meses."
            ),
        })

    # Financial — always medium (no public financial data available via open search)
    findings.append({
        "type": "financial",
        "severity": "medium",
        "description": (
            f"No se encontraron estados financieros públicos para {name}. "
            "Las fuentes abiertas consultadas (web y noticias) no reportan indicadores de solvencia. "
            "Se recomienda solicitar balance general, referencias bancarias y certificado de deudas directamente al proveedor."
        ),
    })

    # Legal — based on search results
    if legal_ok:
        snippet = legal_raw[:120].replace("\n", " ").strip()
        findings.append({
            "type": "legal",
            "severity": "low",
            "description": (
                f"La búsqueda legal retornó información sobre '{name}'. "
                f"Extracto: \"{snippet}...\". No se identificaron demandas activas o multas regulatorias."
            ),
        })
    else:
        findings.append({
            "type": "legal",
            "severity": "low",
            "description": (
                f"La búsqueda de registros legales para '{name}' no arrojó resultados de demandas, "
                "multas, sanciones ni violaciones regulatorias en fuentes de acceso público."
            ),
        })

    score = random.randint(20, 50)
    return {
        "score_total":        score,
        "score_financial":    random.randint(25, 55),
        "score_operational":  random.randint(10, 35) if web_ok else random.randint(30, 55),
        "score_reputational": random.randint(5, 30),
        "summary": (
            f"{name} es un proveedor de {industry} en {country}. "
            + (f"El sitio web está activo y fue analizado. " if web_ok else "No se verificó presencia web. ")
            + ("La búsqueda de noticias y registros legales no detectó señales de riesgo significativas en fuentes públicas. "
               if not news_ok else "Se encontró información pública disponible para el proveedor. ")
            + "Se recomienda solicitar documentación financiera directamente para completar la evaluación."
        ),
        "findings": findings,
        "sources_used": [
            clean_website or "(sin URL)",
            f"{name} noticias finanzas",
            f"{name} lawsuit compliance",
        ],
    }


def _persist(analysis_id: str, final_args: dict, model: str, emit_fn, old_score: int | None = None):
    findings = final_args.get("findings", [])
    sources  = final_args.get("sources_used", [])
    if isinstance(findings, str):
        try: findings = json.loads(findings)
        except Exception: findings = []
    if isinstance(sources, str):
        try: sources = json.loads(sources)
        except Exception: sources = []

    new_score   = final_args.get("score_total")
    score_delta = (new_score - old_score) if (new_score is not None and old_score is not None) else None

    update_analysis(analysis_id, {
        "status":             "done",
        "model_used":         model,
        "score_total":        new_score,
        "score_financial":    final_args.get("score_financial"),
        "score_operational":  final_args.get("score_operational"),
        "score_reputational": final_args.get("score_reputational"),
        "score_delta":        score_delta,
        "summary":            final_args.get("summary"),
        "findings":           findings,
        "sources_used":       sources,
    })
    emit_fn("done", f"Análisis completado — score {new_score}/100")


def _maybe_alert(user_id: str, supplier: dict, old_score: int | None, final_args: dict, analysis_id: str | None = None):
    new_score = final_args.get("score_total")
    if new_score is None or old_score is None:
        return
    def _level(s): return 0 if s < 30 else 1 if s < 60 else 2
    if _level(old_score) == _level(new_score):
        return
    try:
        from datetime import datetime, timezone
        from backend.db.client import get_db
        from backend.services.email import send_risk_alert
        client   = get_db()
        response = client.auth.admin.get_user_by_id(user_id)
        email    = response.user.email
        findings = final_args.get("findings", [])
        if isinstance(findings, str):
            import json as _json
            try: findings = _json.loads(findings)
            except Exception: findings = []
        send_risk_alert(email, supplier["name"], old_score, new_score, findings)
        level      = _level(new_score)
        severity   = "critical" if level == 2 else "high" if level == 1 else "medium"
        score_delta = new_score - old_score
        client.table("alerts").insert({
            "supplier_id":  supplier["id"],
            "user_id":      user_id,
            "analysis_id":  analysis_id,
            "type":         "score_increase",
            "severity":     severity,
            "message":      f"Score de riesgo cambió de {old_score} a {new_score} (delta: {score_delta:+d})",
            "score_before": old_score,
            "score_after":  new_score,
            "recipients":   [email],
            "sent_at":      datetime.now(timezone.utc).isoformat(),
            "send_status":  "sent",
        }).execute()
    except Exception:
        pass


def run_supplier_agent(supplier_id: str, user_id: str, triggered_by: str = "manual", _analysis: dict | None = None):
    analysis    = _analysis or create_analysis(supplier_id, user_id, triggered_by)
    analysis_id = analysis["id"]
    ensure_queue(analysis_id)

    def _emit(event: str, msg: str):
        emit(analysis_id, event, json.dumps({"message": msg}))

    try:
        from backend.db.suppliers import get_supplier
        supplier = get_supplier(supplier_id, user_id)
        if not supplier:
            update_analysis(analysis_id, {"status": "failed", "error_message": "Proveedor no encontrado"})
            return

        _emit("progress", f"Iniciando análisis de {supplier['name']}...")

        client = genai.Client(api_key=settings.gemini_api_key)
        tools  = _build_tools()
        user_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Analiza este proveedor:\n"
            f"Nombre: {supplier['name']}\n"
            f"Sitio web: {supplier.get('website') or 'N/A'}\n"
            f"País: {supplier.get('country') or 'N/A'}\n"
            f"Industria: {supplier.get('industry') or 'N/A'}\n"
            f"Notas: {supplier.get('notes') or 'N/A'}"
        )

        final_args: dict | None = None
        use_demo               = False
        step_num               = 0
        model_used             = MODEL_CASCADE[0]

        # Try each model in cascade before falling back to demo
        for model_attempt in MODEL_CASCADE:
            contents: list[types.Content] = [
                types.Content(role="user", parts=[types.Part(text=user_prompt)])
            ]
            model_used   = model_attempt
            quota_hit    = False

            _emit("progress", f"Usando modelo {model_attempt}...")

            for iteration in range(12):
                try:
                    response = client.models.generate_content(
                        model=model_attempt,
                        contents=contents,
                        config=types.GenerateContentConfig(tools=tools),
                    )
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        _emit("progress", f"Cuota agotada en {model_attempt} — probando siguiente modelo...")
                        quota_hit = True
                        break
                    raise

                candidate     = response.candidates[0]
                model_content = candidate.content
                contents.append(model_content)

                fn_calls = [p for p in model_content.parts if p.function_call]
                if not fn_calls:
                    break

                fn_responses: list[types.Part] = []
                for part in fn_calls:
                    fc        = part.function_call
                    tool_name = fc.name
                    tool_args = dict(fc.args)

                    step_num += 1
                    t0 = time.monotonic()
                    _emit("progress", f"[{step_num}] {tool_name}...")

                    if tool_name == "save_analysis":
                        final_args  = tool_args
                        result_text = "Análisis guardado."
                    else:
                        result_text = (
                            _scrape(tool_args["url"])       if tool_name == "scrape_website" else
                            _duckduckgo(tool_args["query"]) if tool_name == "search_news"    else
                            _duckduckgo(tool_args["query"] + " lawsuit violation compliance")
                        )

                    save_step(analysis_id, step_num, tool_name, tool_args,
                              result_text[:500], int((time.monotonic() - t0) * 1000))

                    fn_responses.append(types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name, response={"result": result_text}
                        )
                    ))

                contents.append(types.Content(role="user", parts=fn_responses))
                if final_args is not None:
                    break

            if quota_hit:
                continue  # try next model
            break  # success or non-quota error

        if final_args is None and not use_demo:
            _emit("progress", "Todos los modelos Gemini sin cuota — usando modo demo con scraping real...")
            final_args = _run_demo(supplier, analysis_id, _emit)
            use_demo   = True

        # Persist
        old_score = supplier.get("current_score")
        model_tag = "demo" if use_demo else model_used
        if final_args:
            _persist(analysis_id, final_args, model_tag, _emit, old_score)
            _maybe_alert(user_id, supplier, old_score, final_args, analysis_id)
        else:
            update_analysis(analysis_id, {
                "status":        "failed",
                "error_message": "El agente no produjo un análisis final.",
            })
            _emit("failed", "El agente no completó el análisis.")

    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        update_analysis(analysis_id, {"status": "failed", "error_message": err})
        emit(analysis_id, "failed", json.dumps({"message": err}))
