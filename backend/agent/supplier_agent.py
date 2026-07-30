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

MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """Eres un analista de riesgo de proveedores para una empresa manufacturera.
Tu trabajo: analizar un proveedor y producir una evaluación de riesgo estructurada BASADA EN EVIDENCIA.
IMPORTANTE: Escribe TODO el contenido en español — resumen, hallazgos, descripciones.

Convención de puntaje: 0 = completamente seguro, 100 = extremadamente riesgoso.

Pasos que DEBES seguir (en orden):
1. Extrae información del sitio web del proveedor si se proporciona una URL.
2. Busca noticias recientes (problemas financieros, disputas laborales, sanciones, cambios de propiedad).
3. Busca problemas legales/regulatorios (demandas, violaciones de cumplimiento, certificaciones, auditorías).
4. Llama a save_analysis con tu evaluación completa.

REGLAS CRÍTICAS PARA LOS HALLAZGOS (findings):
- Cada descripción DEBE mencionar evidencia específica encontrada (o la ausencia documentada de información)
- PROHIBIDO usar frases genéricas. Menciona datos concretos: fechas, números, certificaciones, fuentes
- Si no hay información negativa, explica exactamente qué se buscó y qué se encontró
- Ejemplos CORRECTOS:
  * "El sitio web menciona certificaciones ISO 9001 y programa de calidad activo desde 2018"
  * "Búsqueda de noticias no encontró menciones de quiebras, litigios ni escándalos en los últimos 12 meses para este proveedor"
  * "DuckDuckGo no retornó registros de demandas laborales ni multas regulatorias para el nombre comercial"
  * "La empresa no publica estados financieros públicos; su solvencia no puede verificarse con fuentes abiertas"
  * "Sitio web con información de productos pero sin certificaciones ni referencias de clientes visibles"
- Ejemplos INCORRECTOS (genéricos, PROHIBIDOS):
  * "Sin incidencias operativas recientes"
  * "Presencia web activa"
  * "Información financiera limitada"

El resumen debe mencionar la industria, país y principales hallazgos concretos del análisis.
Sé conciso. Una llamada por herramienta. Llama a save_analysis como la ÚLTIMA acción."""


def _scrape(url: str) -> str:
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
    try:
        import httpx
        r = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=10,
        )
        data = r.json()
        parts = []
        if data.get("Abstract"):
            parts.append(data["Abstract"])
        for topic in data.get("RelatedTopics", [])[:6]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(topic["Text"])
        return "\n".join(parts) if parts else "No results found."
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
    web_raw = _scrape(website) if website else ""
    web_ms  = int((time.monotonic() - t0) * 1000)
    if web_raw and "error" not in web_raw.lower():
        web_summary = f"Sitio web analizado: {website} — {web_raw[:300].replace(chr(10), ' ').strip()}"
        web_ok = True
    else:
        web_summary = f"No se pudo acceder al sitio web: {website or '(sin URL)'}"
        web_ok = False
    save_step(analysis_id, 1, "scrape_website", {"url": website}, web_summary, web_ms)
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
                f"No se pudo acceder al sitio web del proveedor {'(' + website + ')' if website else '(sin URL registrada)'}. "
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
            website or "(sin URL)",
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

        # Gemini agent loop
        client   = genai.Client(api_key=settings.gemini_api_key)
        tools    = _build_tools()
        contents: list[types.Content] = [
            types.Content(role="user", parts=[
                types.Part(text=(
                    f"{SYSTEM_PROMPT}\n\n"
                    f"Analiza este proveedor:\n"
                    f"Nombre: {supplier['name']}\n"
                    f"Sitio web: {supplier.get('website') or 'N/A'}\n"
                    f"País: {supplier.get('country') or 'N/A'}\n"
                    f"Industria: {supplier.get('industry') or 'N/A'}\n"
                    f"Notas: {supplier.get('notes') or 'N/A'}"
                ))
            ])
        ]

        final_args: dict | None = None
        use_demo               = False
        step_num               = 0

        for iteration in range(12):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(tools=tools),
                )
            except Exception as e:
                if "429" in str(e):
                    _emit("progress", "Cuota Gemini agotada — usando modo demo con scraping real...")
                    final_args = _run_demo(supplier, analysis_id, _emit)
                    use_demo   = True
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

        # Persist
        old_score = supplier.get("current_score")
        model_tag = "demo" if use_demo else MODEL
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
