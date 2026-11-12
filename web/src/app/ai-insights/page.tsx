"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  analyzeBatchInvoices,
  getAIHealth,
  getApprovals,
  getBatchPriority,
  getInvoices,
  getPaymentInsights,
  generateReminder,
  processApproval,
  AIHealthResponse,
  ApprovalRequest,
  ApprovalRecordSummary,
  BatchPriorityResponse,
  InvoiceAnalysisResponse,
  InvoiceSummary,
  PaymentBehaviourResponse,
  PriorityScoreResponse,
  ReminderDraftRequest,
  ReminderDraftResponse,
} from "@/lib/api";

const PRIORITY_CONFIG: Record<
  string,
  { label: string; color: string }
> = {
  critical: { label: "Critical", color: "bg-red-100 text-red-800" },
  high: { label: "High", color: "bg-amber-100 text-amber-800" },
  medium: { label: "Medium", color: "bg-blue-100 text-blue-800" },
  low: { label: "Low", color: "bg-green-100 text-green-800" },
};

const TONE_LABELS: Record<string, string> = {
  polite: "Polite",
  friendly: "Friendly",
  firm: "Firm",
};

function formatCurrency(amount: number, currency: string = "USD"): string {
  return amount.toLocaleString(undefined, { style: "currency", currency });
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function PriorityBadge({ level }: { level: string }) {
  const config = PRIORITY_CONFIG[level] ?? {
    label: level,
    color: "bg-zinc-100 text-zinc-600",
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${config.color}`}>
      {config.label}
    </span>
  );
}

function StatCard({
  title,
  value,
  subtitle,
  trend,
  trendColor,
}: {
  title: string;
  value: string | number;
  subtitle: string;
  trend: string;
  trendColor: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-1">
            {title}
          </p>
          <p className="text-2xl font-bold text-zinc-900">{value}</p>
          <p className="text-xs text-zinc-500 mt-1">{subtitle}</p>
        </div>
        <span className={`text-xs font-medium ${trendColor}`}>{trend}</span>
      </div>
    </div>
  );
}

function PriorityRow({
  invoice,
  analysis,
}: {
  invoice: PriorityScoreResponse;
  analysis: InvoiceAnalysisResponse | undefined;
}) {
  const config = PRIORITY_CONFIG[invoice.priority_level] ?? {
    label: invoice.priority_level,
    color: "bg-zinc-100 text-zinc-600",
  };
  const isOverdue = invoice.days_overdue > 0;
  const isPayable =
    invoice.status !== "PAID" && invoice.status !== "CANCELLED";

  return (
    <tr key={invoice.invoice_id} className="hover:bg-zinc-50 transition-colors group">
      <td className="px-4 py-3">
        <PriorityBadge level={invoice.priority_level} />
      </td>
      <td className="px-4 py-3">
        <div className="text-sm font-medium text-zinc-900">
          {invoice.invoice_number || invoice.invoice_id}
        </div>
        {invoice.invoice_number && (
          <p className="text-xs text-zinc-500">#{invoice.invoice_number}</p>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="text-sm font-medium text-zinc-900">
          {invoice.customer_name || "Unknown customer"}
        </div>
        <p className="text-xs text-zinc-500">
          {invoice.customer_email || "—"}
        </p>
      </td>
      <td className="px-4 py-3 text-sm font-medium text-zinc-900">
        {formatCurrency(invoice.amount, invoice.currency)}
      </td>
      <td className="px-4 py-3">
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          invoice.status === "PAID"
            ? "bg-green-100 text-green-800"
            : invoice.status === "UNPAID"
              ? "bg-red-100 text-red-800"
              : invoice.status === "PARTIALLY_PAID"
                ? "bg-amber-100 text-amber-800"
                : invoice.status === "SENT"
                  ? "bg-blue-100 text-blue-800"
                  : "bg-zinc-100 text-zinc-600"
        }`}>
          {invoice.status.replace(/_/g, " ")}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-zinc-600">
        {formatDate(invoice.due_date)}
      </td>
      <td className="px-4 py-3 text-sm font-medium">
        {isOverdue ? (
          <span className="text-red-600">+{invoice.days_overdue} days</span>
        ) : (
          <span className="text-zinc-400">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="h-2 w-16 bg-zinc-100 rounded-full overflow-hidden">
            <div
              className="h-full"
              style={{
                backgroundColor:
                  invoice.score >= 75
                    ? "#ef4444"
                    : invoice.score >= 55
                      ? "#f59e0b"
                      : invoice.score >= 30
                        ? "#3b82f6"
                        : "#22c55e",
                width: `${invoice.score}%`,
              }}
            ></div>
          </div>
          <span className="text-xs font-bold text-zinc-900">
            {invoice.score.toFixed(0)}
          </span>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-zinc-600">
        {analysis?.attention_reasons
          .slice(0, 2)
          .map((r) => r.description)
          .join(" ") || invoice.explanation}
      </td>
      <td className="px-4 py-3">
        <button
          onClick={() => {}}
          disabled={!isPayable}
          className={`px-3 py-1.5 rounded text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            isPayable
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-zinc-200 text-zinc-400"
          }`}
        >
          Draft Reminder
        </button>
      </td>
    </tr>
  );
}

export default function AIIntelligence() {
  const [health, setHealth] = useState<AIHealthResponse | null>(null);
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [priorities, setPriorities] = useState<PriorityScoreResponse[]>([]);
  const [analyses, setAnalyses] = useState<InvoiceAnalysisResponse[]>([]);
  const [insights, setInsights] = useState<PaymentBehaviourResponse | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRecordSummary[]>([]);

  const [composerInvoiceId, setComposerInvoiceId] = useState<string | null>(null);
  const [composerTone, setComposerTone] = useState<string>("polite");
  const [composerContext, setComposerContext] = useState<string>("");
  const [reminderDraft, setReminderDraft] = useState<ReminderDraftResponse | null>(null);
  const [composerStatus, setComposerStatus] = useState<
    "idle" | "generating" | "success" | "error"
  >("idle");

  const [approvalModal, setApprovalModal] = useState<{
    open: boolean;
    record: ApprovalRecordSummary | null;
  }>({ open: false, record: null });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isMock = health?.ai_mode === "mock";
  const aiAvailable = health?.available ?? false;

  const outstandingInvoices = useMemo(
    () =>
      priorities.filter(
        (p) =>
          p.status === "UNPAID" ||
          p.status === "PARTIALLY_PAID" ||
          p.status === "SENT"
      ),
    [priorities]
  );

  const totalOutstanding = useMemo(
    () => outstandingInvoices.reduce((sum, p) => sum + p.amount, 0),
    [outstandingInvoices]
  );

  const highRiskCount = useMemo(
    () =>
      priorities.filter(
        (p) => p.priority_level === "critical" || p.priority_level === "high"
      ).length,
    [priorities]
  );

  const pendingApprovals = useMemo(
    () => approvals.filter((a) => a.status === "pending"),
    [approvals]
  );

  const getAnalysisForInvoice = (invoiceId: string) =>
    analyses.find((a) => a.invoice_id === invoiceId);

  const getInvoiceById = (id: string) =>
    invoices.find((inv) => inv.paypal_invoice_id === id);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        healthRes,
        priorityRes,
        invoiceRes,
        insightsRes,
        approvalsRes,
      ] = await Promise.all([
        getAIHealth(),
        getBatchPriority(),
        getInvoices(),
        getPaymentInsights(),
        getApprovals(),
      ]);

      setHealth(healthRes);
      setPriorities(priorityRes.invoices);
      setInvoices(invoiceRes.invoices);
      setInsights(insightsRes);
      setApprovals(approvalsRes.records);

      if (invoiceRes.invoices.length > 0) {
        try {
          const batchRes = await analyzeBatchInvoices();
          setAnalyses(batchRes.invoices);
        } catch {
          // Batch analysis is supplementary
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleGenerateReminder = async () => {
    if (!composerInvoiceId) return;
    setComposerStatus("generating");
    try {
      const request: ReminderDraftRequest = {
        invoice_id: composerInvoiceId,
        tone: composerTone,
        custom_context: composerContext || undefined,
      };
      const draft = await generateReminder(request);
      setReminderDraft(draft);
      setComposerStatus("success");
    } catch (err) {
      setComposerStatus("error");
      setError(err instanceof Error ? err.message : "Failed to generate reminder draft");
    }
  };

  const handleApprove = async (record: ApprovalRecordSummary) => {
    setApprovalModal({ open: false, record: null });
    try {
      const request: ApprovalRequest = {
        recommendation_id: record.recommendation_id,
        action: "approve",
        editor_note: "",
      };
      const result = await processApproval(request);
      setApprovals((prev) =>
        prev.map((r) =>
          r.id === result.recommendation_id
            ? { ...r, status: result.status, decided_at: result.decided_at }
            : r
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval action failed");
    }
  };

  const handleReject = async (record: ApprovalRecordSummary) => {
    setApprovalModal({ open: false, record: null });
    try {
      const request: ApprovalRequest = {
        recommendation_id: record.recommendation_id,
        action: "reject",
        editor_note: "",
      };
      const result = await processApproval(request);
      setApprovals((prev) =>
        prev.map((r) =>
          r.id === result.recommendation_id
            ? { ...r, status: result.status, decided_at: result.decided_at }
            : r
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rejection action failed");
    }
  };

  const handleEditApproval = async (record: ApprovalRecordSummary, note: string) => {
    setApprovalModal({ open: false, record: null });
    try {
      const request: ApprovalRequest = {
        recommendation_id: record.recommendation_id,
        action: "edit",
        editor_note: note,
      };
      const result = await processApproval(request);
      setApprovals((prev) =>
        prev.map((r) =>
          r.id === result.recommendation_id
            ? { ...r, status: result.status, decided_at: result.decided_at, editor_note: note }
            : r
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Edit action failed");
    }
  };

  if (loading && !error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="flex -space-x-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 w-8 rounded-full bg-zinc-200 animate-pulse"></div>
          ))}
        </div>
        <p className="mt-4 text-sm text-zinc-500">Loading AI insights…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 font-sans antialiased">
      <nav className="bg-white border-b border-zinc-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6 py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <a href="/" className="flex items-center gap-2">
              <span className="text-xl font-bold text-zinc-900 tracking-tight">Invoice Collection</span>
              <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded">AI Agent</span>
            </a>
          </div>
          <div className="flex items-center gap-2 flex-1 md:flex-none md:justify-end">
            <a href="/invoices" className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 transition-colors">
              Invoices
            </a>
            <a href="/connect-paypal" className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 transition-colors">
              Connect PayPal
            </a>
            <a href="/ai-insights" className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow-md transition-all">
              AI Intelligence
            </a>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">AI Intelligence</h1>
            <p className="text-zinc-500 text-sm mt-1">
              Collection prioritization, reminder drafting, and payment behaviour insights powered by AI.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className={`px-3 py-1.5 rounded-full text-xs font-medium border ${
              aiAvailable
                ? "bg-green-50 text-green-700 border-green-200"
                : "bg-amber-50 text-amber-700 border-amber-200"
            }`}>
              {isMock ? "📋 Mock AI" : "🤖 OpenAI"} &nbsp;
              {aiAvailable ? "Available" : "Unavailable"}
            </div>
            {isMock && (
              <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border-blue-200">
                Demo mode — no credentials required
              </span>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
            <div className="flex items-start gap-3">
              <span className="text-red-600">⚠️</span>
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Section A: Collection Overview */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider">Collection Overview</h2>
              <p className="text-xs text-zinc-500 mt-0.5">Key collection metrics at a glance</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard title="High-Risk Invoices" value={highRiskCount} subtitle="Critical &amp; high priority" trend={highRiskCount > 0 ? "⚠️ Attention needed" : "All clear"} trendColor={highRiskCount > 0 ? "text-amber-600" : "text-green-600"} />
            <StatCard title="Total Outstanding" value={formatCurrency(totalOutstanding)} subtitle="Unpaid + partially paid" trend={highRiskCount > 0 ? "Review queue" : "All clear"} trendColor="text-blue-600" />
            <StatCard title="AI Recommendations" value={priorities.length} subtitle="Invoices analyzed" trend={isMock ? "Demo data" : "Live data"} trendColor="text-zinc-600" />
            <StatCard title="Pending Approvals" value={pendingApprovals.length} subtitle="Awaiting human review" trend={pendingApprovals.length > 0 ? "Action required" : "Up to date"} trendColor={pendingApprovals.length > 0 ? "text-red-600" : "text-green-600"} />
          </div>
        </section>

        {/* Section B: AI Priority Analysis */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider">AI Priority Analysis</h2>
              <p className="text-xs text-zinc-500 mt-0.5">Invoices ranked by collection urgency</p>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-zinc-50 border-b border-zinc-200">
                  <tr>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500 uppercase w-20">Priority</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Invoice</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Customer</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-24">Amount</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-24">Status</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-24">Due Date</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-24">Days Overdue</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-32">Score</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Why This Priority</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-32">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {priorities.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="px-4 py-12 text-center text-zinc-500">
                        No priority data available. Sync demo data from the Invoices page first.
                      </td>
                    </tr>
                  ) : (
                    priorities.map((p) => (
                      <PriorityRow key={p.invoice_id} invoice={p} analysis={getAnalysisForInvoice(p.invoice_id)} />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Section C: AI Insights */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider">AI Insights</h2>
              <p className="text-xs text-zinc-500 mt-0.5">Payment behaviour trends and collection risk</p>
            </div>
          </div>
          {isMock && (
            <div className="bg-blue-50 border border-blue-100 p-3 rounded-lg">
              <p className="text-xs text-blue-700 flex items-center gap-2">
                <span>📋</span>
                Insights below are generated from <strong>demo data</strong>. Switch to AI_MODE=openai for live analysis of real PayPal invoice data.
              </p>
            </div>
          )}
          {insights ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6">
                  <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-4">Payment Behaviour Summary</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between"><span className="text-sm text-zinc-600">Total invoices</span><span className="text-sm font-medium text-zinc-900">{insights.total_invoices}</span></div>
                    <div className="flex items-center justify-between"><span className="text-sm text-zinc-600">Paid</span><span className="text-sm font-medium text-green-700">{insights.paid_invoices}</span></div>
                    <div className="flex items-center justify-between"><span className="text-sm text-zinc-600">Outstanding</span><span className="text-sm font-medium text-red-700">{insights.unpaid_invoices}</span></div>
                    {insights.average_days_late !== null && (<div className="flex items-center justify-between"><span className="text-sm text-zinc-600">Avg days late</span><span className="text-sm font-medium text-amber-700">{insights.average_days_late} days</span></div>)}
                    {insights.on_time_rate !== null && (<div className="flex items-center justify-between"><span className="text-sm text-zinc-600">On-time rate</span><span className="text-sm font-medium text-green-700">{insights.on_time_rate.toFixed(0)}%</span></div>)}
                  </div>
                </div>
                <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6">
                  <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-4">Behaviour Trends</h3>
                  <div className="space-y-3">
                    {insights.trends.map((trend, i) => (
                      <div key={i} className="p-3 rounded border border-zinc-200 bg-zinc-50">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-semibold text-zinc-900">{trend.label}</span>
                          <span className={`text-xs font-medium ${trend.confidence === "high" ? "text-green-700" : trend.confidence === "medium" ? "text-amber-700" : "text-zinc-700"}`}>{trend.confidence} confidence</span>
                        </div>
                        <p className="text-sm text-zinc-700 leading-relaxed">{trend.description}</p>
                        {trend.is_estimate && (<p className="text-xs text-zinc-400 mt-1">↳ Estimate — not a guaranteed outcome</p>)}
                      </div>
                    ))}
                    {insights.trends.length === 0 && (<p className="text-sm text-zinc-500 text-center py-4">No trend data available yet.</p>)}
                  </div>
                </div>
              </div>
              <div className="mt-6 bg-zinc-50 rounded-xl border border-zinc-200 p-6">
                <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-3">Data Source &amp; Limitations</h3>
                <p className="text-sm text-zinc-600 leading-relaxed mb-3">
                  Insights are derived from current invoice statuses in the dataset. No external payment history, bank data, or credit information is used.
                </p>
                {insights.is_estimate && (
                  <p className="text-sm text-amber-700">⚠️ All estimates are indicative — based on available data only, not guaranteed predictions of future customer behaviour.</p>
                )}
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 text-center">
              <p className="text-zinc-500 text-sm">No insights data available. Sync demo data to generate payment behaviour analysis.</p>
            </div>
          )}
        </section>

        {/* Section D: AI Reminder Composer */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider">AI Reminder Composer</h2>
              <p className="text-xs text-zinc-500 mt-0.5">Generate personalized payment reminder drafts</p>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-2 block">Select Invoice</label>
                  <select value={composerInvoiceId || ""} onChange={(e) => setComposerInvoiceId(e.target.value || null)} className="w-full px-3 py-2 rounded-lg border border-zinc-300 bg-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                    <option value="">— Choose an invoice —</option>
                    {outstandingInvoices.map((p) => (
                      <option key={p.invoice_id} value={p.invoice_id}>{p.invoice_number || p.invoice_id} — {p.customer_name || "Unknown customer"} ({formatCurrency(p.amount, p.currency)})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-2 block">Tone</label>
                  <div className="flex gap-2">
                    {Object.entries(TONE_LABELS).map(([key, label]) => (
                      <button key={key} onClick={() => setComposerTone(key)} className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${composerTone === key ? "bg-blue-600 text-white shadow-sm" : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"}`}>{label}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-2 block">Additional Context (optional)</label>
                  <textarea value={composerContext} onChange={(e) => setComposerContext(e.target.value)} rows={3} placeholder="e.g. Customer promised payment by Friday" className="w-full px-3 py-2 rounded-lg border border-zinc-300 bg-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                </div>
                <div className="pt-2">
                  <button onClick={handleGenerateReminder} disabled={!composerInvoiceId || composerStatus === "generating"} className={`w-full px-4 py-2.5 rounded-lg font-medium transition-colors ${composerStatus === "generating" ? "bg-zinc-400 text-zinc-300 cursor-not-allowed" : !composerInvoiceId ? "bg-zinc-200 text-zinc-400 cursor-not-allowed" : "bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow-md"}`}>{composerStatus === "generating" ? "Generating…" : "Generate Draft"}</button>
                  {composerStatus === "error" && (<p className="mt-2 text-xs text-red-600">Failed to generate draft. Try again.</p>)}
                </div>
              </div>
              {composerInvoiceId && (
                <div className="space-y-4">
                  <div className="bg-blue-50 rounded-lg border border-blue-100 p-4">
                    <div className="flex items-start gap-3">
                      <span className="text-blue-600">ℹ️</span>
                      <div>
                        <p className="text-xs font-bold text-blue-900 uppercase tracking-wider mb-1">Invoice Context</p>
                        {getInvoiceById(composerInvoiceId) && (
                          <>
                            <p className="text-sm text-zinc-700"><strong>Invoice:</strong> {getInvoiceById(composerInvoiceId)?.invoice_number}</p>
                            <p className="text-sm text-zinc-700"><strong>Customer:</strong> {getInvoiceById(composerInvoiceId)?.customer_name}</p>
                            <p className="text-sm text-zinc-700"><strong>Amount:</strong> {getInvoiceById(composerInvoiceId) ? formatCurrency(getInvoiceById(composerInvoiceId)!.amount, getInvoiceById(composerInvoiceId)!.currency) : "—"}</p>
                            <p className="text-sm text-zinc-700"><strong>Due:</strong> {formatDate(getInvoiceById(composerInvoiceId)?.due_date ?? null)}</p>
                            <p className="text-sm text-zinc-700"><strong>Status:</strong> {getInvoiceById(composerInvoiceId)?.status}</p>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  {reminderDraft && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider">Generated Reminder Draft</h3>
                        <span className="px-2 py-1 rounded text-xs font-bold" style={{ backgroundColor: reminderDraft.method === "ai" ? "#f0fdf4" : "#fffbeb", color: reminderDraft.method === "ai" ? "#15803d" : "#92400e" }}>
                          {reminderDraft.method === "ai" ? "AI-generated" : "Template-based"}
                        </span>
                      </div>
                      <div className="bg-zinc-900 rounded-lg p-4 font-mono text-sm text-zinc-300 overflow-x-auto">
                        <div className="font-bold text-zinc-200 mb-2">{reminderDraft.subject}</div>
                        <div className="whitespace-pre-wrap">{reminderDraft.body}</div>
                      </div>
                      <p className="text-xs text-zinc-500">{reminderDraft.requires_approval ? "⚠️ This draft requires human approval before sending. No emails are sent automatically." : "Draft ready for review."}</p>
                    </div>
                  )}
                </div>
              )}
              {!composerInvoiceId && (
                <div className="flex flex-col items-center justify-center py-20 bg-zinc-50 rounded-lg border border-zinc-200">
                  <span className="text-zinc-400">📝</span>
                  <p className="mt-2 text-sm text-zinc-500">Select an outstanding invoice to generate a reminder draft.</p>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Section E: Human Approval Center */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider">Human Approval Center</h2>
              <p className="text-xs text-zinc-500 mt-0.5">Review, edit, approve, or reject AI recommendations</p>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-zinc-50 border-b border-zinc-200">
                  <tr>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Recommendation</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Action</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-24">Status</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Decided At</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Editor Note</th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-40">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {pendingApprovals.length === 0 && approvals.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-12 text-center text-zinc-500">
                        No approval records yet. Generate a reminder draft to begin the approval workflow.
                      </td>
                    </tr>
                  ) : (
                    approvals.map((a) => (
                      <tr key={a.id} className="hover:bg-zinc-50 transition-colors">
                        <td className="px-4 py-3">
                          <div className="text-sm font-medium text-zinc-900">{a.recommendation_id}</div>
                          <p className="text-xs text-zinc-500">{a.action.replace(/_/g, " ")}</p>
                        </td>
                        <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-bold ${a.status === "approved" ? "bg-green-100 text-green-800" : a.status === "rejected" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"}`}>{a.status}</span></td>
                        <td className="px-4 py-3 text-sm text-zinc-600">{a.decided_at ? formatDate(a.decided_at) : "—"}</td>
                        <td className="px-4 py-3 text-sm text-zinc-600">{a.editor_note || "—"}</td>
                        <td className="px-4 py-3">
                          {a.status === "pending" ? (
                            <div className="flex gap-2">
                              <button onClick={() => handleApprove(a)} className="px-3 py-1.5 rounded text-xs font-medium bg-green-600 text-white hover:bg-green-700 transition-colors">Approve</button>
                              <button onClick={() => setApprovalModal({ open: true, record: a })} className="px-3 py-1.5 rounded text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition-colors">Reject</button>
                              <button onClick={() => setApprovalModal({ open: true, record: a })} className="px-3 py-1.5 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors">Edit</button>
                            </div>
                          ) : (
                            <span className="text-xs text-zinc-400">Completed</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Approval Edit Modal */}
        {approvalModal.open && approvalModal.record && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="fixed inset-0 bg-zinc-900/50 backdrop-blur-sm" onClick={() => setApprovalModal({ open: false, record: null })}></div>
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
              {approvalModal.record && (
                <>
                  <h3 className="text-sm font-bold text-zinc-900 mb-4">Edit Approval: {approvalModal.record.recommendation_id}</h3>
                  <p className="text-xs text-zinc-500 mb-6">Original action: <span className="font-medium text-zinc-900">{approvalModal.record.action.replace(/_/g, " ")}</span></p>
                  <div className="space-y-3">
                    <button onClick={() => handleApprove(approvalModal.record as ApprovalRecordSummary)} className="w-full px-4 py-2 rounded-lg text-sm font-medium bg-green-600 text-white hover:bg-green-700 transition-colors">✅ Approve</button>
                    <button onClick={() => handleReject(approvalModal.record as ApprovalRecordSummary)} className="w-full px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors">❌ Reject</button>
                    <div>
                      <label className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-2 block">Editor Note</label>
                      <textarea value={approvalModal.record.editor_note || ""} onChange={(e) => setApprovalModal((prev) => ({ ...prev, record: prev.record ? { ...prev.record, editor_note: e.target.value } : null }))} rows={3} className="w-full px-3 py-2 rounded-lg border border-zinc-300 bg-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                      <button onClick={() => { const rec = approvalModal.record as ApprovalRecordSummary; handleEditApproval(rec, rec.editor_note || ""); }} className="w-full px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors mt-2">Save Edit</button>
                    </div>
                    <button onClick={() => setApprovalModal({ open: false, record: null })} className="w-full px-4 py-2 rounded-lg text-sm font-medium text-zinc-600 hover:bg-zinc-100 transition-colors">Cancel</button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
