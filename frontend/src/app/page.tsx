"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

/**
 * Landing: si el usuario tiene token, lo manda a /chat. Si no, muestra
 * tarjetas con los CTAs (login / register) y un breve resumen del sistema.
 */
export default function LandingPage() {
  const router = useRouter();
  const [hasToken, setHasToken] = useState<boolean | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("token");
    if (t) {
      router.replace("/chat");
    } else {
      setHasToken(false);
    }
  }, [router]);

  if (hasToken === null) {
    return <p className="text-sm text-slate-500">Cargando…</p>;
  }

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">
          Sistema multiagente de gestión financiera
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600 dark:text-slate-400">
          Cuatro agentes (Orchestrator, Security, Registrar, Analyst) sobre
          LangGraph. Autenticación con passphrase y biometría facial. RGPD
          opt-in en notificaciones.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="card">
          <h2 className="font-semibold">¿Eres usuario nuevo?</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Crea tu cuenta con email, contraseña y una foto. La cara se usa
            como factor biométrico en futuros inicios de sesión.
          </p>
          <Link href="/register" className="btn-primary mt-3 inline-block">
            Crear cuenta
          </Link>
        </div>

        <div className="card">
          <h2 className="font-semibold">¿Ya tienes cuenta?</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Inicia sesión con tu contraseña y una nueva foto. La cara se
            comparará con tu plantilla biométrica almacenada cifrada.
          </p>
          <Link href="/login" className="btn-secondary mt-3 inline-block">
            Iniciar sesión
          </Link>
        </div>
      </div>
    </section>
  );
}
