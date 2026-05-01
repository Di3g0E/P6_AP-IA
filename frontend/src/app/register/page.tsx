"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { WebcamCapture } from "@/components/WebcamCapture";
import { register, setToken } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [consent, setConsent] = useState(false);
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
    if (passphrase.length < 6) {
      setError("La contraseña debe tener al menos 6 caracteres.");
      return;
    }
    setLoading(true);
    try {
      const r = await register(email, passphrase, consent, face);
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
        <h1 className="text-2xl font-bold tracking-tight">Crear cuenta</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Tu rostro se usará como factor biométrico. Se cifra con AES-128 +
          PBKDF2 antes de almacenarse.
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
          <span className="text-sm font-medium">Contraseña (≥ 6)</span>
          <input
            type="password"
            required
            minLength={6}
            value={passphrase}
            onChange={(e) => setPassphrase(e.target.value)}
            className="input mt-1"
            autoComplete="new-password"
          />
        </label>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Foto biométrica</legend>
          <WebcamCapture onCapture={setFace} />
        </fieldset>

        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-1"
            required
          />
          <span>
            Acepto el tratamiento de mis datos biométricos para autenticación
            (RGPD Art. 9).
          </span>
        </label>

        {error && (
          <p className="rounded-md bg-red-50 p-2 text-sm text-red-800 dark:bg-red-950/30">
            {error}
          </p>
        )}

        <div className="flex items-center justify-between">
          <Link href="/login" className="text-sm text-blue-600 hover:underline">
            ¿Ya tienes cuenta? Inicia sesión
          </Link>
          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !face || !consent}
          >
            {loading ? "Creando…" : "Crear cuenta"}
          </button>
        </div>
      </form>
    </section>
  );
}
