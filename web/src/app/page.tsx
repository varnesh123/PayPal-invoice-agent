"use client";

import { useEffect, useState } from "react";

interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  database_configured: boolean;
  paypal_mode: string;
}

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<HealthResponse>;
      })
      .then((data) => {
        if (mounted) {
          setHealth(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const isDemoMode = health?.paypal_mode === "mock";

  return (
    <div className="min-h-screen bg-zinc-50 font-sans">
      <nav className="bg-white border-b border-zinc-200 py-4 px-6 flex items-center gap-4">
        <a href="/" className="text-xl font-semibold text-zinc-900">
          Invoice Collection Agent
        </a>
        <a href="/invoices" className="text-sm text-zinc-600 hover:text-zinc-900">
          Invoices
        </a>
        <a href="/connect-paypal" className="text-sm text-zinc-600 hover:text-zinc-900">
          Connect PayPal
        </a>
        <a href="/ai-insights" className="text-sm text-zinc-600 hover:text-zinc-900">
          AI Intelligence
        </a>
        <a href="/automation" className="text-sm text-zinc-600 hover:text-zinc-900">
          Automation
        </a>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        <section className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
          <h1 className="text-xl font-semibold text-zinc-900 mb-2">Dashboard</h1>
          <p className="text-zinc-600 mb-4">
            AI-Powered Invoice Collection Agent — Phase 2/3 (PayPal Integration
            + Demo Mode).
          </p>

          {/* Mode banner */}
          {isDemoMode && (
            <div className="mb-6 p-4 rounded-lg bg-blue-50 border border-blue-200">
              <h2 className="text-sm font-semibold text-blue-900 mb-1">
                📋 Demo Mode Active
              </h2>
              <p className="text-sm text-blue-700">
                Running with <strong>mock/demo data</strong>. No PayPal
                credentials required. Sync demo invoices from the Invoices page,
                then switch to <code className="font-mono text-xs bg-blue-100 px-1.5 py-0.5 rounded">PAYPAL_MODE=sandbox</code>
                for real PayPal integration.
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-zinc-100 p-4 rounded-lg">
              <p className="text-xs text-zinc-500 uppercase tracking-wider">Backend</p>
              <p className={health?.status === "ok" ? "text-green-700 font-medium" : "text-red-700 font-medium"}>
                {loading ? "Checking…" : health?.status || "unknown"}
              </p>
            </div>
            <div className="bg-zinc-100 p-4 rounded-lg">
              <p className="text-xs text-zinc-500 uppercase tracking-wider">Database</p>
              <p className={health?.database_configured ? "text-green-700 font-medium" : "text-amber-700 font-medium"}>
                {loading ? "Checking…" : health?.database_configured ? "Configured" : "Not configured"}
              </p>
            </div>
            <div className="bg-zinc-100 p-4 rounded-lg">
              <p className="text-xs text-zinc-500 uppercase tracking-wider">PayPal Mode</p>
              <p className={isDemoMode ? "text-blue-700 font-medium" : "text-zinc-700 font-medium"}>
                {loading ? "—" : health?.paypal_mode || "unknown"}
              </p>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 p-4 rounded-lg text-sm text-red-800">
              Could not reach backend: {error}. Make sure uvicorn is running on port 8000.
            </div>
          )}

          <div className="bg-zinc-50 p-4 rounded-lg border border-zinc-200">
            <h3 className="text-sm font-semibold text-zinc-900 mb-2">Next steps</h3>
            <ul className="list-disc list-inside text-zinc-600 text-sm space-y-1">
              <li>Go to <strong>Connect PayPal</strong> to confirm demo mode (or set real PayPal credentials).</li>
              <li>Go to <strong>Invoices</strong> and click "Sync Demo Data" to load sample invoices.</li>
              <li>Use status filter chips to view UNPAID, PAID, SENT, etc.</li>
              <li>Provision Supabase and apply <code className="font-mono text-xs bg-zinc-200 px-1.5 py-0.5">supabase/migrations/0001_initial.sql</code> for persistence.</li>
              <li>Set <code className="font-mono text-xs bg-zinc-200 px-1.5 py-0.5">PAYPAL_MODE=sandbox</code> + credentials for real PayPal integration.</li>
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}
