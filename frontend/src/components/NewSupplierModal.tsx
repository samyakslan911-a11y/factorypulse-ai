"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";

export default function NewSupplierModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    name: "", website: "", country: "", industry: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) { setError("El nombre es obligatorio"); return; }
    setLoading(true);
    setError("");
    const res = await apiFetch("/suppliers/", {
      method: "POST",
      body: JSON.stringify(form),
    });
    if (res.ok) {
      onCreated();
    } else {
      setError("Error al crear proveedor");
      setLoading(false);
    }
  }

  const field = (key: keyof typeof form, label: string, placeholder: string) => (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      <input
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        placeholder={placeholder}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
          text-white placeholder-gray-600 focus:outline-none focus:border-blue-500"
      />
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-semibold text-white">Nuevo proveedor</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl leading-none">×</button>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {field("name",     "Nombre *",   "ej. ACME Manufacturing")}
          {field("website",  "Website",    "https://...")}
          {field("country",  "País",       "ej. México")}
          {field("industry", "Industria",  "ej. Manufactura")}
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <div className="flex gap-3 mt-1">
            <button type="button" onClick={onClose}
              className="flex-1 py-2 rounded-lg text-sm text-gray-400 border border-gray-700 hover:border-gray-500">
              Cancelar
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white
                disabled:bg-gray-700 disabled:text-gray-500">
              {loading ? "Guardando..." : "Crear proveedor"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
