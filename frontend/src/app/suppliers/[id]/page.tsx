"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import type { Supplier } from "@/app/page";
import { apiUrl } from "@/lib/api";

type Finding = {
  type: string;
  severity: "low" | "medium" | "high";
  description: string;
};

type Analysis = {
  id: string;
  status: string;
  score_total: number | null;
  score_financial: number | null;
  score_operational: number | null;
  score_reputational: number | null;
  summary: string | null;
  findings: Finding[];
  model_used: string | null;
  triggered_by: string;
  started_at: string;
  finished_at: string | null;
};

type Step = {
  id: string;
  step_number: number;
  tool_used: string;
  tool_input: Record<string, unknown>;
  tool_output_summary: string | null;
  duration_ms: number | null;
  created_at: string;
};

const SEVERITY_STYLE: Record<string, string> = {
  low:    "bg-green-900/40 text-green-400 border-green-800",
  medium: "bg-yellow-900/40 text-yellow-400 border-yellow-800",
  high:   "bg-red-900/40 text-red-400 border-red-800",
};

const TOOL_ICON: Record<string, string> = {
  scrape_website: "🌐",
  search_news:    "📰",
  search_legal:   "⚖️",
  save_analysis:  "💾",
};

function ScoreRing({ score, size = 80 }: { score: number | null; size?: number }) {
  if (score === null) return <div className="text-gray-500 text-sm">Sin datos</div>;
  const color = score < 30 ? "#22c55e" : score < 60 ? "#eab308" : "#ef4444";
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1f2937" strokeWidth={8} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={8}
        strokeDasharray={`${filled} ${circ}`} strokeLinecap="round" />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        className="rotate-90" style={{ transform: `rotate(90deg)`, transformOrigin: "center",
          fill: color, fontSize: size * 0.26, fontWeight: 700 }}>
        {score}
      </text>
    </svg>
  );
}

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null;
  const color = value < 30 ? "bg-green-500" : value < 60 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-gray-400 w-28 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-gray-300 w-8 text-right font-mono">{value}</span>
    </div>
  );
}

export default function SupplierDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [history, setHistory]   = useState<Analysis[]>([]);
  const [selected, setSelected] = useState<Analysis | null>(null);
  const [steps, setSteps]       = useState<Step[]>([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(apiUrl(`/suppliers/${id}`)).then(r => r.json()),
      fetch(apiUrl(`/suppliers/${id}/history`)).then(r => r.json()),
    ]).then(([sup, hist]) => {
      setSupplier(sup);
      setHistory(hist);
      if (hist.length > 0) selectAnalysis(hist[0]);
      setLoading(false);
    });
  }, [id]);

  async function selectAnalysis(a: Analysis) {
    setSelected(a);
    const res = await fetch(apiUrl(`/suppliers/${id}/analyses/${a.id}/steps`));
    setSteps(await res.json());
  }

  if (loading) return <div className="py-20 text-center text-gray-500">Cargando...</div>;
  if (!supplier) return <div className="py-20 text-center text-red-400">Proveedor no encontrado</div>;

  const latest = history[0] ?? null;

  return (
    <div className="flex flex-col gap-8">
      {/* Back */}
      <button onClick={() => router.push("/")}
        className="text-gray-500 hover:text-gray-300 text-sm flex items-center gap-1 w-fit">
        ← Volver al dashboard
      </button>

      {/* Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col sm:flex-row gap-6">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">{supplier.name}</h1>
          <p className="text-gray-400 text-sm mt-1">
            {[supplier.industry, supplier.country].filter(Boolean).join(" · ")}
          </p>
          {supplier.website && (
            <a href={supplier.website} target="_blank" rel="noopener noreferrer"
              className="text-blue-400 text-sm hover:underline mt-1 block">
              {supplier.website}
            </a>
          )}
          {latest?.summary && (
            <p className="text-gray-300 text-sm mt-4 leading-relaxed border-l-2 border-gray-700 pl-4">
              {latest.summary}
            </p>
          )}
        </div>
        <div className="flex flex-col items-center gap-4">
          <ScoreRing score={supplier.current_score} size={90} />
          <div className="flex flex-col gap-2 w-48">
            <ScoreBar label="Financiero"  value={supplier.score_financial} />
            <ScoreBar label="Operacional" value={supplier.score_operational} />
            <ScoreBar label="Reputación"  value={supplier.score_reputational} />
          </div>
        </div>
      </div>

      {/* Findings */}
      {latest?.findings?.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Hallazgos</h2>
          <div className="flex flex-col gap-2">
            {latest.findings.map((f, i) => (
              <div key={i} className={`border rounded-lg px-4 py-3 flex items-start gap-3 ${SEVERITY_STYLE[f.severity] ?? SEVERITY_STYLE.low}`}>
                <span className="text-xs font-semibold uppercase mt-0.5 shrink-0">{f.severity}</span>
                <div>
                  <span className="text-xs text-gray-500 uppercase">{f.type} · </span>
                  <span className="text-sm">{f.description}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* History + Steps */}
      {history.length > 0 && (
        <section className="grid sm:grid-cols-3 gap-4">
          {/* History list */}
          <div className="flex flex-col gap-2">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">Historial</h2>
            {history.map((a) => (
              <button key={a.id} onClick={() => selectAnalysis(a)}
                className={`text-left rounded-lg px-3 py-2.5 border text-sm transition-colors
                  ${selected?.id === a.id
                    ? "bg-blue-900/30 border-blue-700 text-white"
                    : "bg-gray-900 border-gray-800 text-gray-400 hover:border-gray-600"}`}>
                <div className="flex items-center justify-between">
                  <span>{new Date(a.started_at).toLocaleDateString("es-CL")}</span>
                  {a.score_total !== null && (
                    <span className={`font-mono font-bold ${
                      a.score_total < 30 ? "text-green-400" : a.score_total < 60 ? "text-yellow-400" : "text-red-400"
                    }`}>{a.score_total}</span>
                  )}
                </div>
                <div className="text-xs text-gray-600 mt-0.5">{a.model_used ?? "demo"} · {a.triggered_by}</div>
              </button>
            ))}
          </div>

          {/* Steps */}
          <div className="sm:col-span-2 flex flex-col gap-2">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">
              Pasos del agente
            </h2>
            {steps.length === 0 ? (
              <p className="text-gray-600 text-sm">Sin pasos registrados</p>
            ) : (
              steps.map((s) => (
                <div key={s.id} className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span>{TOOL_ICON[s.tool_used] ?? "🔧"}</span>
                    <span className="text-sm font-medium text-white">{s.tool_used}</span>
                    {s.duration_ms && (
                      <span className="text-xs text-gray-600 ml-auto">{s.duration_ms}ms</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 font-mono leading-relaxed">
                    {s.tool_output_summary ?? "—"}
                  </p>
                </div>
              ))
            )}
          </div>
        </section>
      )}

      {history.length === 0 && (
        <div className="text-center py-10 text-gray-600 text-sm">
          Este proveedor aún no tiene análisis completados.
        </div>
      )}
    </div>
  );
}
