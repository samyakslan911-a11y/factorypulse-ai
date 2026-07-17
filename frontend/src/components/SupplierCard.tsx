"use client";

import { useState } from "react";
import Link from "next/link";
import type { Supplier } from "@/app/page";

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-gray-500 text-sm">Sin análisis</span>;
  const color = score < 30 ? "text-green-400" : score < 60 ? "text-yellow-400" : "text-red-400";
  const label = score < 30 ? "Bajo riesgo" : score < 60 ? "Riesgo medio" : "Alto riesgo";
  return (
    <div className="flex items-center gap-2">
      <span className={`text-2xl font-bold ${color}`}>{score}</span>
      <span className={`text-xs ${color} opacity-75`}>{label}</span>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null;
  const color = value < 30 ? "bg-green-500" : value < 60 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-400 w-24 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-700 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-gray-300 w-6 text-right">{value}</span>
    </div>
  );
}

export default function SupplierCard({
  supplier,
  onAnalysisComplete,
}: {
  supplier: Supplier;
  onAnalysisComplete: () => void;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  async function handleAnalyze() {
    setAnalyzing(true);
    setLogs(["Iniciando análisis..."]);

    const res = await fetch(`/api/analyses/${supplier.id}/run`, { method: "POST" });
    const { analysis_id } = await res.json();

    const es = new EventSource(`/api/stream/${analysis_id}`);

    es.addEventListener("progress", (e) => {
      const { message } = JSON.parse(e.data);
      setLogs((prev) => [...prev, message]);
    });

    es.addEventListener("done", (e) => {
      const { message } = JSON.parse(e.data);
      setLogs((prev) => [...prev, `✓ ${message}`]);
      es.close();
      setAnalyzing(false);
      onAnalysisComplete();
    });

    es.addEventListener("failed", (e) => {
      const { message } = JSON.parse(e.data);
      setLogs((prev) => [...prev, `✗ ${message}`]);
      es.close();
      setAnalyzing(false);
    });
  }

  const hasScore = supplier.current_score !== null;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="font-semibold text-white leading-tight">{supplier.name}</h2>
          <p className="text-gray-400 text-xs mt-0.5">
            {[supplier.industry, supplier.country].filter(Boolean).join(" · ")}
          </p>
          {supplier.website && (
            <a
              href={supplier.website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 text-xs hover:underline mt-0.5 block truncate max-w-[200px]"
            >
              {supplier.website.replace(/^https?:\/\//, "")}
            </a>
          )}
        </div>
        <ScoreBadge score={supplier.current_score} />
      </div>

      {/* Score bars */}
      {hasScore && (
        <div className="flex flex-col gap-1.5">
          <ScoreBar label="Financiero"   value={supplier.score_financial} />
          <ScoreBar label="Operacional"  value={supplier.score_operational} />
          <ScoreBar label="Reputación"   value={supplier.score_reputational} />
        </div>
      )}

      {/* Last analyzed */}
      {supplier.last_analyzed && (
        <p className="text-gray-600 text-xs">
          Último análisis: {new Date(supplier.last_analyzed).toLocaleDateString("es-CL")}
        </p>
      )}

      {/* SSE log */}
      {logs.length > 0 && (
        <div className="bg-gray-950 rounded-lg p-3 text-xs font-mono text-gray-400 max-h-32 overflow-y-auto flex flex-col gap-0.5">
          {logs.map((l, i) => <span key={i}>{l}</span>)}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="flex-1 py-2 rounded-lg text-sm font-medium transition-colors
            bg-blue-600 hover:bg-blue-500 text-white
            disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed"
        >
          {analyzing ? "Analizando..." : hasScore ? "Re-analizar" : "Analizar"}
        </button>
        {hasScore && (
          <Link href={`/suppliers/${supplier.id}`}
            className="px-3 py-2 rounded-lg text-sm text-gray-400 border border-gray-700
              hover:border-gray-500 hover:text-gray-200 transition-colors whitespace-nowrap">
            Ver detalle →
          </Link>
        )}
      </div>
    </div>
  );
}
