"use client";

import { useEffect, useState } from "react";
import { connectPayPal, PayPalConnectResponse } from "@/lib/api";

export default function ConnectPayPal() {
  const [status, setStatus] = useState<"idle" | "connecting" | "result">("idle");
  const [response, setResponse] = useState<PayPalConnectResponse | null>(null);
  const [demoMode, setDemoMode] = useState<boolean | null>(null);

  useEffect(() => {
    // Fetch health to determine if we're in mock/demo mode
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data: any) => {
        setDemoMode(data.paypal_mode === "mock");
      })
      .catch(() => {
        // If backend unreachable, assume demo mode for display purposes
        setDemoMode(true);
      });
  }, []);

  const handleConnect = async () => {
    setStatus("connecting");
    try {
      const data: PayPalConnectResponse = await connectPayPal();
      setResponse(data);
      setStatus("result");
    } catch (err) {
      setResponse({
        connected: false,
        sandbox_business_email: null,
        message:
          err instanceof Error ? err.message : "Unknown error connecting",
      });
      setStatus("result");
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 font-sans">
      <nav className="bg-white border-b border-zinc-200 py-4 px-6 flex items-center gap-4">
        <a href="/" className="text-xl font-semibold text-zinc-900">
          Invoice Collection Agent
        </a>
        <a href="/invoices" className="text-sm text-zinc-600 hover:text-zinc-900">
          Invoices
        </a>
        <a href="/connect-paypal" className="text-sm font-medium text-zinc-900">
          Connect PayPal
        </a>
        <a href="/ai-insights" className="text-sm text-zinc-600 hover:text-zinc-900">
          AI Intelligence
        </a>
      </nav>

      <main className="max-w-2xl mx-auto px-6 py-8 space-y-6">
        <section className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
          <h1 className="text-xl font-semibold text-zinc-900 mb-2">
            Connect PayPal
          </h1>

          {/* Demo mode banner */}
          {demoMode === true && (
            <div className="mb-4 p-4 rounded-lg bg-blue-50 border border-blue-200">
              <h2 className="text-sm font-semibold text-blue-900 mb-1">
                📋 Demo Mode Active
              </h2>
              <p className="text-sm text-blue-700">
                The app is running in <strong>mock/demo mode</strong> — no
                PayPal Developer account or sandbox credentials are required.
                Invoice data is synthetic and generated locally. Real PayPal
                OAuth and API integration can be activated by setting
                <code className="font-mono text-xs bg-blue-100 px-1.5 py-0.5 rounded">
                  PAYPAL_MODE=sandbox
                </code>
                and providing sandbox credentials.
              </p>
            </div>
          )}

          <p className="text-zinc-600 mb-4">
            Link your PayPal sandbox business account so the agent can read your
            invoices and send reminders. This uses app-level OAuth
            (client-credentials) against PayPal Sandbox.
          </p>

          <button
            onClick={handleConnect}
            disabled={status === "connecting"}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              status === "connecting"
                ? "bg-zinc-400 cursor-not-allowed"
                : demoMode === true
                  ? "bg-blue-600 hover:bg-blue-700 text-white"
                  : "bg-zinc-600 hover:bg-zinc-700 text-white"
            }`}
          >
            {status === "connecting"
              ? "Connecting…"
              : demoMode === true
                ? "Use Demo Data (Mock Sync)"
                : "Connect PayPal (Sandbox)"}
          </button>

          {response && (
            <div
              className={`mt-4 p-4 rounded-lg ${
                response.connected
                  ? "bg-green-50 border border-green-200"
                  : "bg-blue-50 border border-blue-200"
              }`}
            >
              <p className={`text-sm font-medium ${
                response.connected ? "text-green-800" : "text-blue-800"
              }`}>
                {response.connected ? "✅ Connected" : "ℹ️ Demo Mode"}
              </p>
              <p className="text-sm text-zinc-600 mt-1">
                {response.message}
              </p>
              {!response.connected && demoMode === true && (
                <p className="text-xs text-zinc-500 mt-2">
                  To sync demo invoices into the database, go to the Invoices
                  page and click "Sync Demo Data".
                </p>
              )}
            </div>
          )}

          {status === "idle" && demoMode !== true && (
            <p className="text-sm text-zinc-500 mt-4">
              Make sure the backend is running at http://localhost:8000 and your
              PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are set in backend/.env.
            </p>
          )}
        </section>
      </main>
    </div>
  );
}
