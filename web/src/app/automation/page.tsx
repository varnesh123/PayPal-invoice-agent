"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  getAutomationStatus,
  getScheduledReminders,
  getSchedulerJobs,
  getAuditLog,
  getEmailHealth,
  cancelReminder,
  pauseScheduler,
  processDueReminders,
  resumeScheduler,
  disableScheduler,
  sendTestEmail,
  syncInvoiceStatus,
  AutomationStatus,
  ScheduledReminderResponse,
  SchedulerJobResponse,
  AuditEvent,
} from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  scheduled: "bg-blue-100 text-blue-800",
  sent: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-amber-100 text-amber-800",
  skipped: "bg-zinc-100 text-zinc-600",
};

const JOB_STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  paused: "bg-amber-100 text-amber-800",
  disabled: "bg-red-100 text-red-800",
};

export default function AutomationDashboard() {
  const [automationStatus, setAutomationStatus] = useState<
    AutomationStatus | null
  >(null);
  const [scheduledReminders, setScheduledReminders] = useState<
    ScheduledReminderResponse[]
  >([]);
  const [schedulerJobs, setSchedulerJobs] = useState<SchedulerJobResponse[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [emailHealth, setEmailHealth] = useState<any>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processStatus, setProcessStatus] = useState<
    "idle" | "processing" | "success" | "error"
  >("idle");
  const [processResult, setProcessResult] = useState<any>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        autoRes,
        remindersRes,
        jobsRes,
        auditRes,
        emailRes,
      ] = await Promise.all([
        getAutomationStatus(),
        getScheduledReminders(),
        getSchedulerJobs(),
        getAuditLog(50),
        getEmailHealth(),
      ]);

      setAutomationStatus(autoRes);
      setScheduledReminders(remindersRes.reminders);
      setSchedulerJobs(jobsRes);
      setAuditEvents(auditRes.events);
      setEmailHealth(emailRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load automation data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleProcessReminders = async () => {
    setProcessStatus("processing");
    try {
      const result = await processDueReminders();
      setProcessResult(result);
      setProcessStatus("success");
      await fetchAll();
    } catch (err) {
      setProcessStatus("error");
      setError(err instanceof Error ? err.message : "Processing failed");
    }
  };

  const handleCancelReminder = async (reminderId: string) => {
    try {
      await cancelReminder({ reminder_id: reminderId, reason: "Cancelled via dashboard" });
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    }
  };

  const handlePauseScheduler = async () => {
    try {
      await pauseScheduler();
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pause failed");
    }
  };

  const handleResumeScheduler = async () => {
    try {
      await resumeScheduler();
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume failed");
    }
  };

  const handleDisableScheduler = async () => {
    try {
      await disableScheduler();
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disable failed");
    }
  };

  const handleSyncInvoices = async () => {
    try {
      const result = await syncInvoiceStatus();
      setProcessResult(result);
      setProcessStatus("success");
      await fetchAll();
    } catch (err) {
      setProcessStatus("error");
      setError(err instanceof Error ? err.message : "Sync failed");
    }
  };

  const handleTestEmail = async () => {
    try {
      const result = await sendTestEmail("test@example.com");
      setProcessResult(result);
      setProcessStatus("success");
    } catch (err) {
      setProcessStatus("error");
      setError(err instanceof Error ? err.message : "Test email failed");
    }
  };

  const statusColor = (status: string) => {
    return STATUS_COLORS[status] || "bg-zinc-100 text-zinc-600";
  };

  const jobStatusColor = (status: string) => {
    return JOB_STATUS_COLORS[status] || "bg-zinc-100 text-zinc-600";
  };

  if (loading && !error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="flex -space-x-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 w-8 rounded-full bg-zinc-200 animate-pulse"></div>
          ))}
        </div>
        <p className="mt-4 text-sm text-zinc-500">Loading automation dashboard…</p>
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
              <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">AI Agent</span>
            </a>
          </div>
          <div className="flex items-center gap-2 flex-1 md:flex-none md:justify-end">
            <a href="/invoices" className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 transition-colors">
              Invoices
            </a>
            <a href="/ai-insights" className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 transition-colors">
              AI Insights
            </a>
            <a href="/automation" className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 shadow-sm hover:shadow-md transition-colors">
              Automation
            </a>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Automation Dashboard</h1>
            <p className="text-zinc-500 text-sm mt-1">
              Scheduled reminders, scheduler jobs, audit log, and automation controls.
            </p>
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

        {/* Automation Status Cards */}
        {automationStatus && (
          <section className="space-y-6">
            <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider mb-4">
              Automation Status
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
                <p className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-1">
                  Total Scheduled
                </p>
                <p className="text-2xl font-bold text-zinc-900">
                  {automationStatus.total_scheduled_reminders}
                </p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
                <p className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-1">
                  Pending
                </p>
                <p className="text-2xl font-bold text-amber-700">
                  {automationStatus.pending_reminders}
                </p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
                <p className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-1">
                  Sent
                </p>
                <p className="text-2xl font-bold text-green-700">
                  {automationStatus.sent_reminders}
                </p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
                <p className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-1">
                  Failed
                </p>
                <p className="text-2xl font-bold text-red-700">
                  {automationStatus.failed_reminders}
                </p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
                <p className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-1">
                  Cancelled
                </p>
                <p className="text-2xl font-bold text-zinc-700">
                  {automationStatus.cancelled_reminders}
                </p>
              </div>
              <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
                <p className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-1">
                  Storage Backend
                </p>
                <p className={`text-2xl font-bold ${automationStatus.storage_backend === "database" ? "text-green-700" : "text-zinc-700"}`}>
                  {automationStatus.storage_backend}
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Scheduler Controls */}
        <section className="space-y-6">
          <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider mb-4">
            Scheduler Controls
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
              <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-4">
                Scheduler Jobs
              </h3>
              <div className="space-y-3">
                {schedulerJobs.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-4">
                    No scheduler jobs found.
                  </p>
                ) : (
                  schedulerJobs.map((job) => (
                    <div
                      key={job.id}
                      className="p-3 rounded border border-zinc-200 bg-zinc-50"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-zinc-900">
                          {job.job_name}
                        </span>
                        <span
                          className={`text-xs font-medium ${jobStatusColor(job.status)}`}
                        >
                          {job.status}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-700">
                        {job.job_type} • Every {job.interval_seconds}s
                      </p>
                      <p className="text-xs text-zinc-600 mt-1">
                        Runs: {job.run_count} • Failures: {job.failure_count}
                      </p>
                      <p className="text-xs text-zinc-500">
                        Next run: {job.next_run_at || "—"}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
              <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-4">
                Controls
              </h3>
              <div className="space-y-3">
                <button
                  onClick={handleProcessReminders}
                  disabled={processStatus === "processing"}
                  className={`w-full px-4 py-2.5 rounded-lg font-medium transition-colors ${
                    processStatus === "processing"
                      ? "bg-zinc-400 text-zinc-300 cursor-not-allowed"
                      : "bg-blue-600 text-white hover:bg-blue-700"
                  }`}
                >
                  {processStatus === "processing"
                    ? "Processing Reminders…"
                    : "Process Due Reminders Now"}
                </button>
                {processResult && (
                  <div className="mt-3 p-3 rounded bg-zinc-50 border border-zinc-200 text-sm">
                    <p className="text-zinc-700">
                      Processed: {processResult.processed} • Sent:{" "}
                      {processResult.sent} • Failed: {processResult.failed} •{" "}
                      Skipped: {processResult.skipped}
                    </p>
                  </div>
                )}
                <div className="flex gap-2">
                  <button
                    onClick={handlePauseScheduler}
                    className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-amber-600 text-white hover:bg-amber-700 transition-colors"
                  >
                    Pause Scheduler
                  </button>
                  <button
                    onClick={handleResumeScheduler}
                    className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-green-600 text-white hover:bg-green-700 transition-colors"
                  >
                    Resume Scheduler
                  </button>
                </div>
                <button
                  onClick={handleDisableScheduler}
                  className="w-full px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors mt-2"
                >
                  Disable Scheduler
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Sync & Test Controls */}
        <section className="space-y-6">
          <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider mb-4">
            Integration Controls
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
              <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-4">
                PayPal Sync
              </h3>
              <p className="text-xs text-zinc-600 mb-3">
                Sync invoice status from PayPal. In mock mode, no real API call is made.
              </p>
              <button
                onClick={handleSyncInvoices}
                className="w-full px-4 py-2.5 rounded-lg font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
              >
                Sync Invoice Status
              </button>
            </div>
            <div className="bg-white p-6 rounded-xl border border-zinc-200 shadow-sm">
              <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-4">
                Email Test
              </h3>
              <p className="text-xs text-zinc-600 mb-3">
                Send a test email. In mock mode, no real email is sent.
              </p>
              <button
                onClick={handleTestEmail}
                className="w-full px-4 py-2.5 rounded-lg font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
              >
                Send Test Email
              </button>
            </div>
          </div>
        </section>

        {/* Scheduled Reminders Table */}
        {scheduledReminders.length > 0 && (
          <section className="space-y-6">
            <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider mb-4">
              Scheduled Reminders
            </h2>
            <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-zinc-50 border-b border-zinc-200">
                    <tr>
                      <th className="px-4 py-3 text-xs font-semibold text-zinc-500">
                        Invoice
                      </th>
                      <th className="px-4 py-3 text-xs font-semibold text-zinc-500">
                        Customer
                      </th>
                      <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-24">
                        Amount
                      </th>
                      <th className="px-4 py-3 text-xs font-semibold text-zinc-500">
                        Status
                      </th>
                      <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-24">
                        Scheduled For
                      </th>
                      <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-32">
                        Channel
                      </th>
                      <th className="px-4 py-3 text-xs font-semibold text-zinc-500 w-32">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {scheduledReminders.map((r) => (
                      <tr key={r.id} className="hover:bg-zinc-50 transition-colors">
                        <td className="px-4 py-3 text-zinc-900 font-medium font-mono text-xs">
                          {r.paypal_invoice_id}
                        </td>
                        <td className="px-4 py-3 text-zinc-700">
                          {r.customer_name || r.customer_email}
                        </td>
                        <td className="px-4 py-3 text-zinc-700">
                          {r.amount?.toLocaleString(undefined, {
                            style: "currency",
                            currency: r.currency || "USD",
                          }) || "—"}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-1 rounded text-xs font-bold ${statusColor(r.status)}`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-zinc-700">
                          {r.scheduled_for}
                        </td>
                        <td className="px-4 py-3 text-sm text-zinc-600">
                          {r.channel}
                        </td>
                        <td className="px-4 py-3">
                          {r.status === "scheduled" ? (
                            <button
                              onClick={() => handleCancelReminder(r.id)}
                              className="px-3 py-1.5 rounded text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
                            >
                              Cancel
                            </button>
                          ) : (
                            <span className="text-xs text-zinc-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {/* Audit Log */}
        <section className="space-y-6">
          <h2 className="text-sm font-bold text-zinc-900 uppercase tracking-wider mb-4">
            Audit Log
          </h2>
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-zinc-50 border-b border-zinc-200">
                  <tr>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">
                      Time
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">
                      Event
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">
                      Resource
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">
                      Actor
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold text-zinc-500">
                      Details
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {auditEvents.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                        No audit events yet.
                      </td>
                    </tr>
                  ) : (
                    auditEvents.slice(0, 20).map((e) => (
                      <tr key={e.id} className="hover:bg-zinc-50 transition-colors">
                        <td className="px-4 py-3 text-xs font-mono text-zinc-600">
                          {e.created_at}
                        </td>
                        <td className="px-4 py-3 text-xs font-medium text-zinc-900">
                          {e.event_type}
                        </td>
                        <td className="px-4 py-3 text-xs text-zinc-700">
                          {e.resource_type || "—"}
                        </td>
                        <td className="px-4 py-3 text-xs text-zinc-700">
                          {e.actor}
                        </td>
                        <td className="px-4 py-3 text-xs text-zinc-600">
                          {e.details ? JSON.stringify(e.details).slice(0, 80) : "—"}
                        </td>
                      </tr>
                    )))}
                  </tbody>
              </table>
            </div>
          </div>
          </section>
      </main>
    </div>
  );
}