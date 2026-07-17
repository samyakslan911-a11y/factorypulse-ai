"use client";

import { useEffect, useState } from "react";
import SupplierCard from "@/components/SupplierCard";
import NewSupplierModal from "@/components/NewSupplierModal";

export type Supplier = {
  id: string;
  name: string;
  website: string | null;
  country: string | null;
  industry: string | null;
  tags: string[];
  current_score: number | null;
  score_financial: number | null;
  score_operational: number | null;
  score_reputational: number | null;
  risk_status: string;
  last_analyzed: string | null;
  last_analysis_status: string | null;
  created_at: string;
};

type SchedulerStatus = {
  running: boolean;
  next_run: string | null;
  interval_days: number;
  check_hours: number;
  enabled: boolean;
};

function SchedulerWidget() {
  const [status, setStatus] = useState<SchedulerStatus | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch("/api/scheduler/status")
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => null);
  }, []);

  async function handleRunNow() {
    setRunning(true);
    await fetch("/api/scheduler/run-now", { method: "POST" });
    setRunning(false);
  }

  if (!status) return null;

  const nextRun = status.next_run
    ? new Date(status.next_run).toLocaleString("es-CL", {
        day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
      })
    : "—";

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4 flex flex-wrap items-center gap-4 mb-6">
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${status.running ? "bg-green-500" : "bg-gray-600"}`} />
        <span className="text-sm text-gray-300 font-medium">
          Scheduler {status.running ? "activo" : "inactivo"}
        </span>
      </div>
      <div className="text-xs text-gray-500">
        Re-analiza cada <span className="text-gray-300">{status.interval_days} días</span>
      </div>
      {status.running && (
        <div className="text-xs text-gray-500">
          Próxima revisión: <span className="text-gray-300">{nextRun}</span>
        </div>
      )}
      <button
        onClick={handleRunNow}
        disabled={running}
        className="ml-auto text-xs px-3 py-1.5 rounded-lg border border-gray-700
          text-gray-400 hover:border-gray-500 hover:text-gray-200 transition-colors
          disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {running ? "Ejecutando..." : "Re-analizar todos ahora"}
      </button>
    </div>
  );
}

export default function Dashboard() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [showModal, setShowModal] = useState(false);

  async function fetchSuppliers() {
    try {
      const res = await fetch("/api/suppliers");
      if (!res.ok) throw new Error();
      const data = await res.json();
      setSuppliers(data);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchSuppliers(); }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Proveedores</h1>
          <p className="text-gray-400 text-sm mt-1">
            {suppliers.length} proveedor{suppliers.length !== 1 ? "es" : ""} registrado{suppliers.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          + Nuevo proveedor
        </button>
      </div>

      <SchedulerWidget />

      {loading ? (
        <div className="text-center py-20 text-gray-500">Cargando...</div>
      ) : error ? (
        <div className="text-center py-20">
          <p className="text-red-400 mb-2">No se pudo conectar al backend</p>
          <p className="text-gray-600 text-sm">Asegúrate de que run.bat está corriendo en otra terminal</p>
        </div>
      ) : suppliers.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-gray-500 mb-4">No hay proveedores todavía</p>
          <button
            onClick={() => setShowModal(true)}
            className="text-blue-400 hover:text-blue-300 text-sm underline"
          >
            Agrega tu primer proveedor
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {suppliers.map((s) => (
            <SupplierCard key={s.id} supplier={s} onAnalysisComplete={fetchSuppliers} />
          ))}
        </div>
      )}

      {showModal && (
        <NewSupplierModal
          onClose={() => setShowModal(false)}
          onCreated={() => { setShowModal(false); fetchSuppliers(); }}
        />
      )}
    </div>
  );
}
