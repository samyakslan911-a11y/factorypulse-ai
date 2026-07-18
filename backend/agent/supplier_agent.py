"""
Supplier Agent — Phase 2.
Gemini 2.0 Flash con function calling. 4 herramientas: scrape, news, legal, save.
Fallback a modo demo si Gemini no tiene cuota disponible.
"""
import json
import time
from google import genai
from google.genai import types

from backend.config import settings
from backend.db.analyses import create_analysis, update_analysis, save_step
from backend.api.stream import emit, ensure_queue

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a supplier risk analyst for a manufacturing company.
Your job: analyze a supplier and produce a structured risk assessment.

Scoring convention: 0 = perfectly safe, 100 = extremely risky.

Steps you MUST follow (in order):
1. Scrape the supplier's website if a URL is provided.
2. Search for recent news (financial problems, labor disputes, sanctions, ownership changes).
3. Search for legal/regulatory issues (lawsuits, compliance violations, certifications, audits).
4. Call save_analysis with your complete assessment.

Be concise. One call per tool. Call save_analysis as the LAST action."""


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
                        description="Executive summary in 2-3 sentences."),
                    "findings": types.Schema(type=types.Type.STRING,
                        description='JSON array: [{"type":"financial|operational|legal|reputational","severity":"low|medium|high","description":"..."}]'),
                    "sources_used": types.Schema(type=types.Type.STRING,
                        description='JSON array of URLs or search queries used: ["url1", "query2"]'),
                },
                required=["score_total", "score_financial", "score_operational",
                          "score_reputational", "summary", "findings", "sources_used"],
            ),
        ),
    ])]


def _run_demo(supplier: dict, analysis_id: str, emit_fn) -> dict:
    """Análisis simulado — fallback cuando Gemini no tiene cuota."""
    import random
    steps = [
        ("scrape_website", f"Scraped {supplier.get('website', 'N/A')} — found company profile, certifications, product catalog"),
        ("search_news",    f"No major financial distress signals for {supplier['name']} in recent 12 months"),
        ("search_legal",   f"No active lawsuits or regulatory violations found for {supplier['name']}"),
    ]
    for i, (tool, output) in enumerate(steps, 1):
        time.sleep(1)
        emit_fn("progress", f"[{i}] {tool}...")
        save_step(analysis_id, i, tool, {"demo": True}, output, 800)

    score = random.randint(15, 45)
    return {
        "score_total":        score,
        "score_financial":    random.randint(10, 40),
        "score_operational":  random.randint(15, 50),
        "score_reputational": random.randint(5, 35),
        "summary": (
            f"{supplier['name']} es un proveedor de {supplier.get('industry', 'manufactura')} en "
            f"{supplier.get('country', 'la región')}. El análisis automatizado no detectó señales "
            f"de riesgo financiero o legal significativas. Se recomienda monitoreo trimestral."
        ),
        "findings": [
            {"type": "operational",  "severity": "low",    "description": "Sin incidencias operativas recientes reportadas"},
            {"type": "reputational", "severity": "low",    "description": "Presencia web activa, sin controversias públicas"},
            {"type": "financial",    "severity": "medium", "description": "Información financiera pública limitada — requiere auditoría directa"},
        ],
        "sources_used": [
            supplier.get("website", ""),
            f"{supplier['name']} news search",
            f"{supplier['name']} legal search",
        ],
    }


def _persist(analysis_id: str, final_args: dict, model: str, emit_fn):
    findings = final_args.get("findings", [])
    sources  = final_args.get("sources_used", [])
    if isinstance(findings, str):
        try: findings = json.loads(findings)
        except Exception: findings = []
    if isinstance(sources, str):
        try: sources = json.loads(sources)
        except Exception: sources = []

    update_analysis(analysis_id, {
        "status": "done",
        "model_used": model,
        "score_total":         final_args.get("score_total"),
        "score_financial":     final_args.get("score_financial"),
        "score_operational":   final_args.get("score_operational"),
        "score_reputational":  final_args.get("score_reputational"),
        "summary":             final_args.get("summary"),
        "findings":            findings,
        "sources_used":        sources,
    })
    emit_fn("done", f"Análisis completado — score {final_args.get('score_total')}/100")


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

        # ── Gemini agent loop ──────────────────────────────────────────
        client   = genai.Client(api_key=settings.gemini_api_key)
        tools    = _build_tools()
        contents: list[types.Content] = [
            types.Content(role="user", parts=[
                types.Part(text=f"{SYSTEM_PROMPT}\n\nAnalyze this supplier:\n"
                           f"Supplier: {supplier['name']}\n"
                           f"Website: {supplier.get('website') or 'N/A'}\n"
                           f"Country: {supplier.get('country') or 'N/A'}\n"
                           f"Industry: {supplier.get('industry') or 'N/A'}\n"
                           f"Notes: {supplier.get('notes') or 'N/A'}")
            ])
        ]

        final_args: dict | None = None
        use_demo               = False
        step_num               = 0

        for iteration in range(12):
            # Try Gemini; on 429 fall back to demo
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(tools=tools),
                )
            except Exception as e:
                if "429" in str(e):
                    _emit("progress", "Cuota Gemini agotada — usando modo demo...")
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

        # ── Persist ───────────────────────────────────────────────────
        model_tag = "demo" if use_demo else MODEL
        if final_args:
            _persist(analysis_id, final_args, model_tag, _emit)
        else:
            update_analysis(analysis_id, {
                "status": "failed",
                "error_message": "El agente no produjo un análisis final.",
            })
            _emit("failed", "El agente no completó el análisis.")

    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        update_analysis(analysis_id, {"status": "failed", "error_message": err})
        emit(analysis_id, "failed", json.dumps({"message": err}))
