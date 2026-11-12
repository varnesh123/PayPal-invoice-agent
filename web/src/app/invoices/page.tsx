"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getInvoices,
  InvoiceSummary,
  mockSync,
  MockSyncResponse,
} from "@/lib/api";

const STATUS_OPTIONS: string[] = [
  "UNPAID",
  "PAID",
  "PARTIALLY_PAID",
  "SENT",
  "DRAFT",
  "CANCELLED",
];

export default function Invoices() {
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<
    "idle" | "syncing" | "success" | "error"
  >("idle");
  const [syncResult, setSyncResult] = useState<MockSyncResponse | null>(null);

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getInvoices(filter);
      setInvoices(data.invoices);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  const handleSync = async () => {
    setSyncStatus("syncing");
    try {
      const result: MockSyncResponse = await mockSync();
      setSyncResult(result);
      setSyncStatus("success");
      // Refresh invoices after sync
      await fetchInvoices();
    } catch (err) {
      setSyncStatus("error");
      setError(
        err instanceof Error ? err.message : "Mock sync failed"
      );
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "PAID":
        return "bg-green-100 text-green-800";
      case "UNPAID":
        return "bg-red-100 text-red-800";
      case "PARTIALLY_PAID":
        return "bg-amber-100 text-amber-800";
      case "SENT":
        return "bg-blue-100 text-blue-800";
      case "DRAFT":
        return "bg-zinc-100 text-zinc-800";
      case "CANCELLED":
        return "bg-zinc-200 text-zinc-600";
      default:
        return "bg-zinc-100 text-zinc-600";
    }
  };

  const overdueCount = invoices.filter(
    (inv) =>
      inv.status === "UNPAID" ||
      inv.status === "PARTIALLY_PAID" ||
      inv.status === "SENT"
  ).length;

  return (
    <div className="min-h-screen bg-zinc-50 font-sans">
      <nav className="bg-white border-b border-zinc-200 py-4 px-6 flex items-center gap-4">
        <a href="/" className="text-xl font-semibold text-zinc-900">
          Invoice Collection Agent
        </a>
        <a href="/invoices" className="text-sm font-medium text-zinc-900">
          Invoices
        </a>
        <a href="/connect-paypal" className="text-sm text-zinc-600 hover:text-zinc-900">
          Connect PayPal
        </a>
        <a href="/ai-insights" className="text-sm font-medium text-zinc-900">
          AI Intelligence
        </a>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-zinc-900">Invoices</h1>
            <p className="text-zinc-600">
              Synced from PayPal Invoicing API v2 ({total ?? 0} total)
            </p>
          </div>

          {/* Sync button (demo mode) */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSync}
              disabled={syncStatus === "syncing"}
              className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-colors ${
                syncStatus === "syncing"
                  ? "bg-zinc-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }`}
            >
              {syncStatus === "syncing" ? "Syncing…" : "Sync Demo Data"}
            </button>
            {syncStatus === "success" && syncResult && (
              <span className="text-xs text-green-700 bg-green-100 px-2 py-1 rounded">
                ✓ {syncResult.invoices_upserted} invoices synced
              </span>
            )}
            {syncStatus === "error" && (
              <span className="text-xs text-red-700 bg-red-100 px-2 py-1 rounded">
                ✗ Sync failed
              </span>
            )}
          </div>
        </div>

        {/* Status filter chips */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilter(null)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              filter === null
                ? "bg-zinc-900 text-white"
                : "bg-zinc-200 text-zinc-600 hover:bg-zinc-300"
            }`}
          >
            All
          </button>
          {STATUS_OPTIONS.map((s) => {
          const isActive = filter === s;
          const chipColor = isActive
            ? "bg-zinc-900 text-white"
            : "bg-zinc-200 text-zinc-600 hover:bg-zinc-300";
          return (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${chipColor}`}
            >
              {s.replace(/_/g, " ")}
            </button>
          );
        })}
        </div>

        {overdueCount > 0 && filter === null && (
          <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg flex items-center gap-3">
            <span className="text-amber-900 font-medium">⚠️</span>
            <div>
              <p className="text-sm font-semibold text-amber-900">
                {overdueCount} invoice(s) need attention
              </p>
              <p className="text-xs text-amber-700">
                UNPAID, PARTIALLY_PAID, or SENT invoices require follow-up.
              </p>
            </div>
          </div>
        )}

        {loading ? (
          <p className="text-zinc-500">Loading invoices…</p>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 p-4 rounded-lg text-sm text-red-800">
            Could not load invoices: {error}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead className="bg-zinc-50 border-b border-zinc-200">
                <tr>
                  <th className="px-6 py-3 text-xs font-semibold text-zinc-500 uppercase">Invoice ID</th>
                  <th className="px-6 py-3 text-xs font-semibold text-zinc-500 uppercase">Customer</th>
                  <th className="px-6 py-3 text-xs font-semibold text-zinc-500 uppercase">Amount</th>
                  <th className="px-6 py-3 text-xs font-semibold text-zinc-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-xs font-semibold text-zinc-500 uppercase">Due Date</th>
                  <th className="px-6 py-3 text-xs font-semibold text-zinc-500 uppercase">Balance Due</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {invoices.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-zinc-500">
                      No invoices found.
                      {filter ? (
                        <p className="text-xs text-zinc-400 mt-2">
                          Try clearing the "{filter}" filter.
                        </p>
                      ) : (
                        <p className="text-xs text-zinc-400 mt-2">
                          Click "Sync Demo Data" to load sample invoices.
                        </p>
                      )}
                    </td>
                  </tr>
                ) : (
                  invoices.map((inv) => (
                    <tr key={inv.paypal_invoice_id}>
                      <td className="px-6 py-4 text-zinc-900 font-medium">
                        {inv.paypal_invoice_id}
                      </td>
                      <td className="px-6 py-4 text-zinc-700">
                        {inv.customer_name || inv.customer_email || "—"}
                      </td>
                      <td className="px-6 py-4 text-zinc-700">
                        {inv.amount.toLocaleString(undefined, {
                          style: "currency",
                          currency: inv.currency,
                        })}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${statusColor(inv.status)}`}>
                          {inv.status.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-zinc-700">
                        {inv.due_date || "—"}
                      </td>
                      <td className="px-6 py-4 text-zinc-700 font-medium">
                        {inv.balance_due.toLocaleString(undefined, {
                          style: "currency",
                          currency: inv.currency,
                        })}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
