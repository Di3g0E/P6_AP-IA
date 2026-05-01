"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { WebcamCapture } from "@/components/WebcamCapture";
import { login, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [face, setFace] = useState<Blob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!face) {
      setError("Captura una foto primero.");
      return;
    }
    setLoading(true);
    try {
      const r = await login(email, passphrase, face);
      setToken(r.access_token, r.user_id);
      router.push("/chat");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="mx-auto max-w-xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Iniciar sesión</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Tu cara se compara con tu plantilla biométrica almacenada cifrada.
        </p>
      </header>

      <form onSubmit={onSubmit} className="card space-y-4">
        <label className="block">
          <span className="text-sm font-medium">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input mt-1"
            autoComplete="email"
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium">Contraseña</span>
          <input
            type="password"
            required
            value={passphrase}
            onChange={(e) => setPassphrase(e.target.value)}
            className="input mt-1"
            autoComplete="current-password"
          />
        </label>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Foto en vivo</legend>
          <WebcamCapture onCapture={setFace} />
        </fieldset>

        {error && (
          <p className="rounded-md bg-red-50 p-2 text-sm text-red-800 dark:bg-red-950/30">
            {error}
          </p>
        )}

        <div className="flex items-center justify-between">
          <Link
            href="/register"
            className="text-sm text-blue-600 hover:underline"
          >
            ¿Eres nuevo? Crea tu cuenta
          </Link>
          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !face}
          >
            {loading ? "Verificando…" : "Entrar"}
          </button>
        </div>
      </form>
    </section>
  );
}
