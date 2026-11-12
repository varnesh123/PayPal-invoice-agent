// Backend API client for the frontend.
//
// Phase 1: health check.
// Phase 2/3: PayPal connect, mock sync, invoice listing with status filter.
// Phase 4: AI Intelligence - analysis, priority, reminders, insights, approvals.

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  database_configured: boolean;
  paypal_mode: string;
}

export interface PayPalConnectResponse {
  connected: boolean;
  sandbox_business_email: string | null;
  message: string;
}

export interface InvoiceSummary {
  paypal_invoice_id: string;
  invoice_number: string | null;
  customer_name: string | null;
  customer_email: string | null;
  amount: number;
  currency: string;
  status: string;
  due_date: string | null;
  balance_due: number;
}

export interface InvoicesListResponse {
  invoices: InvoiceSummary[];
  total: number | null;
}

export interface MockSyncResponse {
  status: string;
  mode: string;
  invoices_seen: number;
  customers_upserted: number;
  invoices_upserted: number;
  demo_mode: boolean;
}

// --- AI Intelligence types ---

export interface AttentionReason {
  factor: string;
  description: string;
  severity: string;
}

export interface InvoiceAnalysisResponse {
  invoice_id: string;
  invoice_number: string | null;
  customer_name: string | null;
  customer_email: string | null;
  amount: number;
  currency: string;
  status: string;
  due_date: string | null;
  days_overdue: number;
  needs_attention: boolean;
  attention_reasons: AttentionReason[];
  summary: string;
}

export interface PriorityFactor {
  name: string;
  weight: number;
  contribution: number;
  explanation: string;
}

export interface PriorityScoreResponse {
  invoice_id: string;
  invoice_number: string | null;
  customer_name: string | null;
  customer_email: string | null;
  amount: number;
  currency: string;
  status: string;
  due_date: string | null;
  days_overdue: number;
  priority_level: string;
  score: number;
  factors: PriorityFactor[];
  explanation: string;
  method: string;
}

export interface BatchPriorityResponse {
  invoices: PriorityScoreResponse[];
  total_count: number;
}

export interface ReminderDraftRequest {
  invoice_id: string;
  tone: string;
  custom_context?: string;
}

export interface ReminderDraftResponse {
  invoice_id: string;
  invoice_number: string | null;
  customer_name: string | null;
  customer_email: string | null;
  amount: number;
  currency: string;
  due_date: string | null;
  tone: string;
  subject: string;
  body: string;
  method: string;
  requires_approval: boolean;
  recommendation_id?: string;
}

export interface PaymentBehaviourInsight {
  category: string;
  label: string;
  value: any;
  confidence: string;
  description: string;
  is_estimate: boolean;
}

export interface PaymentBehaviourResponse {
  customer_email: string | null;
  total_invoices: number;
  paid_invoices: number;
  unpaid_invoices: number;
  average_days_late: number | null;
  on_time_rate: number | null;
  trends: PaymentBehaviourInsight[];
  summary: string;
  is_estimate: boolean;
}

export interface ApprovalRequest {
  recommendation_id: string;
  action: string;
  edited_content?: any;
  editor_note?: string;
}

export interface ApprovalResponse {
  recommendation_id: string;
  action: string;
  status: string;
  decided_at: string;
  editor_note: string | null;
  storage_backend: string;
}

export interface ApprovalRecordSummary {
  id: string;
  recommendation_id: string;
  action: string;
  status: string;
  decided_at: string | null;
  editor_note: string | null;
  storage_backend: string;
}

export interface ApprovalsListResponse {
  records: ApprovalRecordSummary[];
  total: number;
}

export interface AIHealthResponse {
  ai_mode: string;
  configured: boolean;
  provider: string;
  available: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`Backend request failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

/** Fetch backend health status. */
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

/** Validate PayPal / demo connection. */
export async function connectPayPal(): Promise<PayPalConnectResponse> {
  return request<PayPalConnectResponse>("/paypal/connect", {
    method: "POST",
  });
}

/** Sync mock invoices into Supabase (mock mode only). */
export async function mockSync(): Promise<MockSyncResponse> {
  return request<MockSyncResponse>("/paypal/mock-sync", {
    method: "POST",
  });
}

/** List invoices with optional status filter. */
export async function getInvoices(
  status?: string | null
): Promise<InvoicesListResponse> {
  const url = status
    ? `/invoices?status=${encodeURIComponent(status)}`
    : "/invoices";
  return request<InvoicesListResponse>(url);
}

/** Get a single invoice by PayPal invoice ID. */
export async function getInvoice(
  invoiceId: string
): Promise<InvoiceSummary> {
  return request<InvoiceSummary>(`/invoices/${encodeURIComponent(invoiceId)}`);
}

// --- AI Intelligence API client ---

/** Get AI service health status. */
export async function getAIHealth(): Promise<AIHealthResponse> {
  return request<AIHealthResponse>("/ai/health");
}

/** Analyze a single invoice for collection attention. */
export async function analyzeInvoice(
  invoiceId: string
): Promise<InvoiceAnalysisResponse> {
  return request<InvoiceAnalysisResponse>("/ai/analyze", {
    method: "POST",
    body: JSON.stringify({ invoice_id: invoiceId }),
  });
}

/** Analyze all invoices for collection attention. */
export async function analyzeBatchInvoices(): Promise<{
  invoices: InvoiceAnalysisResponse[];
  total_analyzed: number;
  needs_attention_count: number;
}> {
  return request<{
    invoices: InvoiceAnalysisResponse[];
    total_analyzed: number;
    needs_attention_count: number;
  }>("/ai/analyze/batch", {
    method: "POST",
  });
}

/** Get priority score for a single invoice. */
export async function getInvoicePriority(
  invoiceId: string
): Promise<PriorityScoreResponse> {
  return request<PriorityScoreResponse>("/ai/priority", {
    method: "POST",
    body: JSON.stringify({ invoice_id: invoiceId }),
  });
}

/** Get priority scores for all invoices, sorted by priority. */
export async function getBatchPriority(): Promise<BatchPriorityResponse> {
  return request<BatchPriorityResponse>("/ai/priority/batch", {
    method: "POST",
  });
}

/** Generate a personalized reminder draft (requires human approval). */
export async function generateReminder(
  body: ReminderDraftRequest
): Promise<ReminderDraftResponse> {
  return request<ReminderDraftResponse>("/ai/reminder", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Generate payment behaviour insights. */
export async function getPaymentInsights(
  customerEmail?: string | null
): Promise<PaymentBehaviourResponse> {
  const url = customerEmail
    ? `/ai/insights?customer_email=${encodeURIComponent(customerEmail)}`
    : "/ai/insights";
  return request<PaymentBehaviourResponse>(url, {
    method: "POST",
  });
}

/** Approve, reject, or edit an AI recommendation. */
export async function processApproval(
  body: ApprovalRequest
): Promise<ApprovalResponse> {
  return request<ApprovalResponse>("/ai/approval", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** List approval history (most recent first). */
export async function getApprovals(): Promise<ApprovalsListResponse> {
  return request<ApprovalsListResponse>("/ai/approvals");
}

// --- Phase 5: Scheduling & Automation types ---

export interface ScheduledReminderResponse {
  id: string;
  user_id: string;
  ai_recommendation_id: string | null;
  invoice_id: string | null;
  paypal_invoice_id: string;
  customer_email: string;
  customer_name: string | null;
  subject: string;
  body: string;
  tone: string;
  channel: string;
  status: string;
  scheduled_for: string;
  sent_at: string | null;
  executed_at: string | null;
  idempotency_key: string;
  delivery_attempts: number;
  max_attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  amount: number | null;
  currency: string | null;
}

export interface ScheduledRemindersListResponse {
  reminders: ScheduledReminderResponse[];
  total: number;
}

export interface ScheduleReminderRequest {
  recommendation_id: string;
  scheduled_for: string;
  tone: string;
  channel: string;
}

export interface CancelReminderRequest {
  reminder_id: string;
  reason: string | null;
}

export interface SchedulerJobResponse {
  id: string;
  job_name: string;
  job_type: string;
  status: string;
  last_run_at: string | null;
  next_run_at: string | null;
  interval_seconds: number;
  run_count: number;
  failure_count: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationStatus {
  scheduler_running: boolean;
  total_scheduled_reminders: number;
  pending_reminders: number;
  sent_reminders: number;
  failed_reminders: number;
  cancelled_reminders: number;
  next_job_run: string | null;
  storage_backend: string;
}

export interface AuditEvent {
  id: string;
  user_id: string | null;
  event_type: string;
  event_category: string;
  resource_type: string | null;
  resource_id: string | null;
  actor: string;
  details: any;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogResponse {
  events: AuditEvent[];
  total: number;
}

// --- Phase 5: Scheduling & Automation API client ---

/** Schedule a reminder from an approved draft. */
export async function scheduleReminder(
  body: ScheduleReminderRequest
): Promise<ScheduledReminderResponse> {
  return request<ScheduledReminderResponse>("/ai/schedule-reminder", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** List all scheduled reminders. */
export async function getScheduledReminders(): Promise<ScheduledRemindersListResponse> {
  return request<ScheduledRemindersListResponse>("/ai/scheduled-reminders");
}

/** Cancel a scheduled reminder. */
export async function cancelReminder(
  body: CancelReminderRequest
): Promise<{ status: string; reminder_id: string }> {
  return request<{ status: string; reminder_id: string }>("/ai/cancel-reminder", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** List all scheduler jobs. */
export async function getSchedulerJobs(): Promise<SchedulerJobResponse[]> {
  return request<SchedulerJobResponse[]>("/ai/scheduler/jobs");
}

/** Pause the scheduler. */
export async function pauseScheduler(): Promise<{ status: string }> {
  return request<{ status: string }>("/ai/scheduler/pause", {
    method: "POST",
  });
}

/** Resume the scheduler. */
export async function resumeScheduler(): Promise<{ status: string }> {
  return request<{ status: string }>("/ai/scheduler/resume", {
    method: "POST",
  });
}

/** Disable the scheduler. */
export async function disableScheduler(): Promise<{ status: string }> {
  return request<{ status: string }>("/ai/scheduler/disable", {
    method: "POST",
  });
}

/** Process due reminders (smart follow-up). */
export async function processDueReminders(): Promise<any> {
  return request<any>("/ai/scheduler/process", {
    method: "POST",
  });
}

/** Email provider health. */
export async function getEmailHealth(): Promise<any> {
  return request<any>("/ai/email/health");
}

/** Send a test email. */
export async function sendTestEmail(toEmail: string): Promise<any> {
  return request<any>("/ai/email/test", {
    method: "POST",
    body: JSON.stringify({ to_email: toEmail }),
  });
}

/** Get audit log events. */
export async function getAuditLog(
  limit?: number,
  eventType?: string | null,
  eventCategory?: string | null
): Promise<AuditLogResponse> {
  const url = `/ai/audit-log?limit=${limit ?? 100}${
    eventType ? `&event_type=${encodeURIComponent(eventType)}` : ""
  }${eventCategory ? `&event_category=${encodeURIComponent(eventCategory)}` : ""}`;
  return request<AuditLogResponse>(url);
}

/** Get automation status. */
export async function getAutomationStatus(): Promise<AutomationStatus> {
  return request<AutomationStatus>("/ai/automation-status");
}

/** Sync invoice status from PayPal. */
export async function syncInvoiceStatus(): Promise<any> {
  return request<any>("/paypal/sync-invoice-status", {
    method: "POST",
  });
}
