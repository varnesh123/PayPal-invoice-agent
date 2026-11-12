"use client";

import { useEffect, useState } from "react";
import { getHealth, HealthResponse } from "@/lib/api";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then((data) => {
        if (mounted) {
          setHealth(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-zinc-50 font-sans">
      <header className="bg-white border-b border-zinc-200 py-4 px-6">
        <h1 className="text-xl font-semibold text-zinc-900">
          Invoice Collection Agent
        </h1>
        <p className="text-sm text-zinc-500">Phase 1 — Foundation</p>
      </header>

      <main className="flex-1 max-w-2xl mx-auto px-6 py-8 space-y-6">
        <section className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
          <h2 className="text-base font-semibold text-zinc-900 mb-2">Backend status</h2>
          {loading ? (
            <p className="text-zinc-500">Checking backend connection…</p>
          ) : error ? (
            <p className="text-sm text-red-600 bg-red-50 rounded p-3 border border-red-100">
              Could not reach backend: {error}
            </p>
          ) : health ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="bg-zinc-100 p-3 rounded-lg">
                <p className="text-xs text-zinc-500 uppercase tracking-wider">Status</p>
                <p className={health.status === "ok" ? "text-green-700" : "text-red-700"}>{health.status}</p>
              </div>
              <div className="bg-zinc-100 p-3 rounded-lg">
                <p className="text-xs text-zinc-500 uppercase tracking-wider">Service</p>
                <p className="text-zinc-900">{health.service}</p>
              </div>
              <div className="bg-zinc-100 p-3 rounded-lg">
                <p className="text-xs text-zinc-500 uppercase tracking-wider">Environment</p>
                <p className="text-zinc-900">{health.environment}</p>
              </div>
              <div className="bg-zinc-100 p-3 rounded-lg">
                <p className="text-xs text-zinc-500 uppercase tracking-wider">Database configured</p>
                <p className={health.database_configured ? "text-green-700" : "text-amber-700"}>
                  {health.database_configured ? "Yes" : "No"}
                </p>
              </div>
            </div>
          ) : null}
        </section>

        <section className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
          <h2 className="text-base font-semibold text-zinc-900 mb-2">Next steps</h2>
          <ul className="list-disc list-inside text-zinc-600 space-y-1 text-sm">
            <li>Provision a Supabase PostgreSQL project and set DATABASE_URL.</li>
            <li>Apply migrations/0001_initial.sql.</li>
            <li>Implement PayPal OAuth + invoice sync (Phase 2).</li>
          </ul>
        </section>
      </main>
    </div>
  );
}
