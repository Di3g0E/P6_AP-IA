"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  clearToken,
  confirmPending,
  getUserId,
  listPending,
  rejectPending,
  type PendingReview,
} from "@/lib/api";

export default function PendingPage() {
  const router = useRouter();
  const [items, setItems] = useState<PendingReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const list = await listPending();
      setItems(list);
    } catch (err) {
      const msg = (err as Error).message;
      setError(msg);
      if (msg.toLowerCase().includes("token") || msg.includes("401")) {
        clearToken();
        router.replace("/login");
      }
    } finally {
      setLoading(false);
    }
  }, [router]);

  // Protege la ruta + carga inicial
  useEffect(() => {
    if (!getUserId()) {
      router.replace("/login");
      return;
    }
    refresh();
  }, [router, refresh]);

  const onConfirm = async (id: string) => {
    setBusyId(id);
    try {
      await confirmPending(id);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  const onReject = async (id: string) => {
    if (!confirm("¿Rechazar esta transacción? No se contabilizará en analytics.")) {
      return;
    }
    setBusyId(id);
    try {
      await rejectPending(id);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Transacciones pendientes de revisar
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Estas transacciones fueron marcadas por el agente Security como
            posibles anomalías. Apruébalas para que cuenten en tus analytics
            o recházalas para descartarlas.
          </p>
        </div>
        <button onClick={refresh} className="btn-secondary text-sm">
          Refrescar
        </button>
      </header>

      {error && (
        <p className="rounded-md bg-red-50 p-2 text-sm text-red-800 dark:bg-red-950/30">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Cargando…</p>
      ) : items.length === 0 ? (
        <p className="card text-sm text-slate-500">
          Sin pendientes de revisión 🎉
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((it) => (
            <li key={it.record.id} className="card space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-medium">{it.record.description}</h3>
                <span className="text-lg font-semibold">
                  {it.record.amount} {it.record.currency}
                </span>
              </div>
              <div className="text-xs text-slate-500">
                {it.record.date} · {it.record.area.join(", ")} · {it.record.type}
              </div>
              {it.anomaly_reasons.length > 0 && (
                <ul className="rounded-md bg-amber-50 p-2 text-xs text-amber-900 dark:bg-amber-900/20 dark:text-amber-200">
                  {it.anomaly_reasons.map((r, i) => (
                    <li key={i}>· {r}</li>
                  ))}
                </ul>
              )}
              <div className="flex gap-2">
                <button
                  className="btn-primary text-sm"
                  onClick={() => onConfirm(it.record.id)}
                  disabled={busyId === it.record.id}
                >
                  Aprobar
                </button>
                <button
                  className="btn-danger text-sm"
                  onClick={() => onReject(it.record.id)}
                  disabled={busyId === it.record.id}
                >
                  Rechazar
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
