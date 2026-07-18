import resend
from backend.config import settings


def _level(score: int) -> str:
    if score < 30: return "bajo"
    if score < 60: return "medio"
    return "alto"

def _color(score: int) -> str:
    if score < 30: return "#22c55e"
    if score < 60: return "#f59e0b"
    return "#ef4444"

def _label(score: int) -> str:
    if score < 30: return "Bajo riesgo"
    if score < 60: return "Riesgo medio"
    return "Alto riesgo"

def _emoji(score: int) -> str:
    if score < 30: return "🟢"
    if score < 60: return "🟡"
    return "🔴"


def send_risk_alert(
    to_email: str,
    supplier_name: str,
    old_score: int,
    new_score: int,
    findings: list,
) -> None:
    if not settings.resend_api_key:
        return

    resend.api_key = settings.resend_api_key

    high = [f for f in findings if f.get("severity") == "high"]
    findings_html = "".join(
        f'<li style="margin-bottom:6px"><strong>{f.get("type","").title()}</strong>: {f.get("description","")}</li>'
        for f in high[:3]
    )
    findings_block = (
        f'<div style="background:#1f2937;border-radius:8px;padding:16px;margin-bottom:16px">'
        f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Hallazgos críticos</div>'
        f'<ul style="margin:0;padding-left:18px;color:#d1d5db;font-size:13px;line-height:1.6">{findings_html}</ul>'
        f'</div>'
    ) if high else ""

    resend.Emails.send({
        "from": settings.email_from,
        "to": [to_email],
        "subject": f"{_emoji(new_score)} {supplier_name} — riesgo {_label(new_score)}",
        "html": f"""
<div style="font-family:system-ui,-apple-system,sans-serif;background:#0a0e1a;min-height:100vh;padding:40px 16px">
<div style="max-width:520px;margin:0 auto">

  <div style="display:flex;align-items:center;gap:10px;margin-bottom:28px">
    <div style="width:30px;height:30px;background:#3b82f6;border-radius:7px;display:flex;align-items:center;justify-content:center;font-weight:700;color:white;font-size:14px">F</div>
    <span style="font-weight:600;color:#f9fafb;font-size:14px">FactoryPulse AI</span>
  </div>

  <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:28px">
    <p style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.08em;margin:0 0 10px">Alerta de riesgo</p>
    <h1 style="font-size:22px;font-weight:700;color:#f9fafb;margin:0 0 6px">{supplier_name}</h1>
    <p style="color:#9ca3af;font-size:14px;margin:0 0 24px">El nivel de riesgo cambió de <strong style="color:#f9fafb">{_label(old_score)}</strong> a <strong style="color:{_color(new_score)}">{_label(new_score)}</strong>.</p>

    <div style="display:flex;gap:12px;margin-bottom:24px">
      <div style="flex:1;background:#1f2937;border-radius:10px;padding:16px;text-align:center">
        <div style="font-size:10px;color:#6b7280;text-transform:uppercase;margin-bottom:6px">Antes</div>
        <div style="font-size:32px;font-weight:700;color:#9ca3af;line-height:1">{old_score}</div>
        <div style="font-size:11px;color:#6b7280;margin-top:4px">{_label(old_score)}</div>
      </div>
      <div style="display:flex;align-items:center;color:#374151;font-size:18px;padding:0 4px">→</div>
      <div style="flex:1;background:#1f2937;border-radius:10px;padding:16px;text-align:center;border:1px solid {_color(new_score)}33">
        <div style="font-size:10px;color:#6b7280;text-transform:uppercase;margin-bottom:6px">Ahora</div>
        <div style="font-size:32px;font-weight:700;color:{_color(new_score)};line-height:1">{new_score}</div>
        <div style="font-size:11px;color:{_color(new_score)};margin-top:4px">{_label(new_score)}</div>
      </div>
    </div>

    {findings_block}

    <a href="https://factorypulse-ai-3skn.vercel.app"
       style="display:block;background:#3b82f6;color:white;text-align:center;padding:13px;border-radius:9px;text-decoration:none;font-weight:500;font-size:14px">
      Ver análisis completo →
    </a>
  </div>

  <p style="text-align:center;color:#374151;font-size:11px;margin-top:20px">
    FactoryPulse AI · Supplier Risk Intelligence
  </p>
</div>
</div>
""",
    })
