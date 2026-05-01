"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { chat, clearToken, getUserId } from "@/lib/api";

type Turn = {
  role: "user" | "assistant";
  text: string;
  action?: string | null;
};

const SUGGESTIONS = [
  "resume mis gastos del último mes",
  "¿qué tendencia tienen mis gastos?",
  "¿qué gastos recurrentes detectas?",
  "¿qué tengo pendiente de revisar?",
];

export default function ChatPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Protege la ruta: sin token → /login
  useEffect(() => {
    const uid = getUserId();
    if (!uid) {
      router.replace("/login");
    } else {
      setUserId(uid);
    }
  }, [router]);

  // Auto-scroll al fondo cuando llega un nuevo turno
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [turns]);

  const send = async (text: string) => {
    setError(null);
    setTurns((t) => [...t, { role: "user", text }]);
    setInput("");
    setLoading(true);
    try {
      const r = await chat(text, sessionId);
      setSessionId(r.session_id);
      setTurns((t) => [
        ...t,
        { role: "assistant", text: r.response, action: r.last_action },
      ]);
    } catch (err) {
      const msg = (err as Error).message;
      setError(msg);
      // Si el token expiró, redirigir a login
      if (msg.toLowerCase().includes("token") || msg.includes("401")) {
        clearToken();
        router.replace("/login");
      }
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !loading) send(input.trim());
  };

  const onLogout = () => {
    clearToken();
    router.replace("/login");
  };

  if (!userId) {
    return <p className="text-sm text-slate-500">Cargando…</p>;
  }

  return (
    <section className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Chat</h1>
          <p className="text-xs text-slate-500">
            Usuario: <code className="font-mono">{userId.slice(0, 8)}…</code>
            {sessionId && (
              <>
                {" · "}sesión <code className="font-mono">{sessionId.slice(0, 8)}…</code>
              </>
            )}
          </p>
        </div>
        <button onClick={onLogout} className="btn-secondary text-sm">
          Cerrar sesión
        </button>
      </header>

      <div
        ref={scrollRef}
        className="card max-h-[60vh] min-h-[40vh] overflow-y-auto space-y-3"
      >
        {turns.length === 0 && (
          <div className="text-sm text-slate-500">
            <p>Escribe una pregunta o prueba una sugerencia:</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="btn-secondary text-xs"
                  onClick={() => send(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t, i) => (
          <div
            key={i}
            className={
              t.role === "user"
                ? "ml-auto max-w-[80%] rounded-lg bg-blue-600 px-3 py-2 text-sm text-white"
                : "max-w-[80%] rounded-lg bg-slate-100 px-3 py-2 text-sm dark:bg-slate-800"
            }
          >
            <p className="whitespace-pre-wrap">{t.text}</p>
            {t.action && (
              <p className="mt-1 text-[10px] uppercase tracking-wider opacity-60">
                {t.action}
              </p>
            )}
          </div>
        ))}
        {loading && (
          <p className="text-sm italic text-slate-500">El orquestador está pensando…</p>
        )}
      </div>

      {error && (
        <p className="rounded-md bg-red-50 p-2 text-sm text-red-800 dark:bg-red-950/30">
          {error}
        </p>
      )}

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          type="text"
          className="input flex-1"
          placeholder="Escribe tu mensaje…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="btn-primary"
          disabled={loading || !input.trim()}
        >
          Enviar
        </button>
      </form>
    </section>
  );
}
