I'll start by researching PayPal's APIs, webhooks, agent toolkit, and sandbox details to ground this blueprint in accurate technical facts before writing anything.
→Explored: 5 searches
+Thought · 841ms
The web search tool failed. Let me retry with a single focused search.
→Explored: 1 search
+Thought · 4.8s
Confirmed key Invoicing API facts. Let me gather more on webhooks, the Agentic Toolkit, and sandbox specifics.
→Explored: 4 searches
+Thought · 7.8s
I have strong research on OAuth, Invoicing API, and webhooks. Let me make a couple more targeted attempts on the Agentic Toolkit and AI Toolkit.
→Explored: 3 searches
+Thought · 2m 51s
I now have confirmed research on PayPal OAuth, Invoicing API v2, webhooks, and sandbox. The Agentic Toolkit and AI Toolkit specifics could not be confirmed via search, so I'll mark those as Needs verification and default to direct REST integration. Here is the complete blueprint.
AI-Powered Invoice Collection Agent — Engineering Blueprint
Status: Planning & research only. No code written, no files created, no implementation started.
Audience: First-year CSE student + OpenCode AI coding agent (implementation in later stages).
1. Executive Summary
We are building an AI-Powered Invoice Collection Agent — a web dashboard that connects to a business's PayPal account (Sandbox first), retrieves their invoices, uses an AI agent to analyze which unpaid invoices need attention, prioritizes them, drafts personalized payment reminders, classifies customer replies, and updates invoice status via PayPal webhooks — all with a human-in-the-loop approval step before any message is sent.
Why: PayPal already sends invoices and generic reminders, but it does not (a) prioritize which unpaid invoices matter most, (b) understand the context of a customer's reply, or (c) adapt follow-up strategy based on payment history and commitments. Our differentiator is intelligent collection workflow automation with human oversight, not another invoice generator.
Core promise to hackathon judges: "PayPal tells you an invoice is unpaid. Our agent tells you which unpaid invoice to chase first, writes the reminder, reads the customer's reply, and stops chasing once PayPal confirms payment — with you approving every outgoing message."
Confirmed technical decisions (research-backed):
- PayPal OAuth 2.0 client-credentials flow; access token cached and refreshed proactively (~8-hour expiry).
- PayPal Invoicing API v2 (/v2/invoicing/...) — list, get details, send, remind, cancel.
- PayPal webhooks: INVOICING.INVOICE.PAID (and others) to stop follow-ups on confirmed payment.
- Direct PayPal REST integration (Agentic Toolkit not adopted — see §4D, marked Needs verification).
- Single OpenAI agent with direct function/tool calling (no LangGraph for MVP).
- Next.js + Tailwind frontend; Python + FastAPI backend; PostgreSQL via Supabase; deployment on Vercel + Render/Railway.
2. Problem Statement and Target Users
Primary target users
- Freelancers, consultants, and small agencies who invoice clients via PayPal.
- Small businesses using PayPal Invoicing who have 10–200 outstanding invoices and no dedicated accounts-receivable person.
Most important problems (in priority order)
1. Visibility: They don't have a single view of all unpaid/overdue invoices across customers.
2. Prioritization: They don't know which overdue invoice to chase first (amount? age? customer reliability?).
3. Message drafting: Writing polite but firm reminders takes time and emotional energy.
4. Reply interpretation: When a customer replies ("can I pay next week?", "I never got this", "I dispute the amount"), the owner must manually interpret intent and decide next steps.
5. Payment confirmation: They must manually check PayPal to see if payment arrived, then remember to stop reminders.
6. Consistency: Follow-ups are ad-hoc and often forgotten.
What success looks like (MVP)
The owner opens one dashboard, sees a prioritized list of overdue invoices with AI-written reminder drafts, approves one, sends it, and when the customer pays (confirmed via PayPal webhook), the invoice moves to "Paid" and is removed from the collection queue automatically.
3. Product Vision and Core Features
Product vision
A single dashboard where a PayPal-using business delegates routine invoice-collection work to an AI agent, while retaining final approval over every customer-facing message and every consequential action.
Core features (MVP scope)
#	Feature	Description
F1	PayPal Connect	OAuth link to the user's PayPal business account (Sandbox).
F2	Invoice sync	Pull invoices from PayPal; store status, amount, due date, customer email.
F3	Overdue detection	Automatically flag invoices past due date with status UNPAID/PARTIALLY_PAID.
F4	AI prioritization	Rank outstanding invoices by urgency (transparent formula).
F5	Reminder drafting	AI writes personalized reminder text per invoice/customer.
F6	Human approval	Owner reviews/edits/approves every reminder before it is sent.
F7	Send reminder	Trigger PayPal /remind (generic) or log custom message for manual send.
F8	Reply classification	AI classifies customer replies into intent categories.
F9	Follow-up recommendation	AI recommends next action & timing per intent category.
F10	Payment webhook	INVOICING.INVOICE.PAID webhook updates status and stops reminders.
F11	Collection summary	Dashboard + AI-generated summary of outstanding/collected/promised amounts.
Out of scope for MVP (future features)
- Creating/sending new invoices via our app (PayPal already does this).
- Multi-currency FX handling, tax computation.
- Recurring/subscription invoices.
- Direct email inbox integration (customer replies entered manually or via simulated channel for hackathon).
- PayPal Orders, Payouts, Subscriptions, disputes, credit products.
- Mobile app.
4. Existing Solutions and Differentiation
How PayPal's own invoicing works (confirmed)
PayPal Invoicing lets a business create, send, and track invoices, and offers:
- Manual reminder sending via /v2/invoicing/invoices/{invoice_id}/remind.
- Invoice statuses: DRAFT, SENT, UNPAID, PAID, PARTIALLY_PAID, CANCELLED, REFUNDED, etc.
- Webhooks for invoice state transitions (INVOICING.INVOICE.PAID, etc.).
- No intelligence about which invoice to chase first, no understanding of customer replies, no prioritization, no human-approval workflow for reminder text.
Comparison table
Capability	PayPal built-in invoicing	Accounting software (QuickBooks/Xero)	Automated reminder tools	AI finance/collection products	Our Agent
Invoice tracking	✅ Native	✅ Native	⚠️ Via import/sync	✅ Native	✅ Via PayPal sync
Reminder automation	✅ Generic reminders	✅ Templates	✅ Scheduled blasts	✅ AI-written	✅ AI-written + personalized
Context-aware communication	❌ No	⚠️ Limited templates	❌ No	✅ Yes	✅ Yes (invoice + history)
Customer reply understanding	❌ No	❌ No	❌ No	⚠️ Some	✅ Yes (intent classification)
Prioritization of outstanding	❌ No	⚠️ Aging report only	❌ No	⚠️ Some	✅ Yes (transparent formula)
Human approval before send	❌ N/A (auto)	❌ N/A	❌ N/A	⚠️ Varies	✅ Required gate
Payment-event sync (webhook)	✅ Native	✅ Native	⚠️ Partial	✅ Native	✅ Via PayPal webhooks
Collection insights/reports	⚠️ Basic	✅ Reports	⚠️ Basic	✅ Dashboards	✅ AI-generated summary
What existing products do well
- PayPal: reliable invoicing, payment processing, webhooks, global reach.
- Accounting software: full ledger, tax, aging reports.
- Automated reminders: reliable scheduled delivery.
The gap we address
None of the above combine PayPal-native invoice data + AI prioritization + reply intent understanding + human-approved personalized messaging + webhook-driven auto-stop in one lightweight dashboard aimed at freelancers/small businesses.
What is genuinely innovative (for this project scope)
- A single AI agent that owns the collection workflow (analyze → prioritize → draft → classify reply → recommend next action → stop on payment), rather than just generating invoice text or sending generic reminders.
- Transparent priority scoring so the owner understands why an invoice is top priority.
- Human-approval gate: the AI proposes, the human disposes.
What is only standard automation (do not overclaim)
- Syncing invoices from PayPal API → database.
- Webhook updating status to PAID.
- Sending a reminder via PayPal /remind.
- These are necessary plumbing, not differentiation. Differentiation is the AI layer on top.
How to communicate value to judges
"PayPal's invoicing tells you an invoice is unpaid. Our agent decides which unpaid invoice to chase first, writes the reminder in the customer's context, reads their reply, and stops the moment PayPal confirms payment — and it won't send anything until you approve it."
5. Final Technology Stack
Decisions are finalized (marked Needs verification where research was inconclusive).
Layer	Selected tool	Purpose	Essential?	Where used	Alternatives considered
Frontend framework	Next.js (React)	Dashboard UI, pages, API surface	Yes	Frontend	React + Vite (rejected: Next.js simpler for deployment on Vercel)
Styling	Tailwind CSS	Component styling	Yes	Frontend	Plain CSS (rejected: slower)
UI components	Tailwind + shadcn/ui (optional)	Pre-built accessible components	Optional	Frontend	Raw Tailwind (acceptable fallback)
Charts	Recharts (optional)	Collection summary charts	Optional	Reports section	No charts (MVP can use tables)
Backend	Python + FastAPI	API, business logic, webhook listener, AI orchestration	Yes	Backend	Node.js (rejected: Python is AI-native, better for OpenAI integration)
Data validation	Pydantic	Request/response schemas	Yes	Backend	—
AI model	OpenAI (gpt-4o-mini)	Reminder drafting, reply classification, summarization	Yes	AI agent	gpt-3.5-turbo (rejected: weaker reasoning)
AI invocation	OpenAI direct function/tool calling	Agent calls backend tools	Yes	AI agent	OpenAI Agents SDK / LangGraph (rejected: over-engineering for MVP; Needs verification if complex multi-step needed later)
Database	PostgreSQL via Supabase	All app data, invoices, messages, webhook log	Yes	Backend	Self-hosted Postgres on Render/Railway (Supabase simplest free tier)
Payments	PayPal REST API v2 (direct)	Invoices, status, reminders, webhooks	Yes	Backend → PayPal	PayPal SDKs (rejected: raw HTTP via httpx is lighter and clearer for a student)
PayPal Agentic Toolkit	Not used	PayPal-provided agent tools	No	—	Needs verification: invoice coverage uncertain; direct REST is simpler and more reliable
PayPal AI Toolkit	Not used	Skills/prompts library	No	—	No runtime benefit for MVP
Notifications	PayPal /remind (primary)	PayPal emails customer a reminder	Yes	Backend → PayPal	Resend/SendGrid (optional, for custom AI-composed email; simulate for hackathon)
Frontend hosting	Vercel (free)	Next.js hosting	Yes	Frontend	Netlify
Backend hosting	Render free tier or Railway (free trial)	FastAPI + public webhook URL	Yes	Backend	Railway (Render spins down on free tier — note for demo)
Local dev tunnel	ngrok (optional)	Expose local backend to PayPal webhooks during dev	Optional	Dev only	—
Paid / usage-limit notes
- OpenAI API: pay-per-token; gpt-4o-mini is cheap (few dollars for a hackathon). Set a usage limit.
- Supabase free tier: 500 MB DB, sufficient.
- Render free tier: spins down after inactivity (backend "cold start"); acceptable for demo but webhooks may miss events while sleeping. For a reliable demo, keep the backend awake or use a paid tier/Railway.
- PayPal Sandbox: free, no transaction fees.
Documentation links (official)
- PayPal REST: https://developer.paypal.com/api/rest/
- PayPal OAuth/authentication: https://developer.paypal.com/api/rest/authentication/
- PayPal Invoicing API v2: https://developer.paypal.com/api/invoicing/v2/
- PayPal Invoicing webhooks: https://developer.paypal.com/api/invoicing/webhooks
- PayPal webhook event names: https://developer.paypal.com/api/rest/webhooks/event-names/
- PayPal Dashboard/Sandbox: https://developer.paypal.com/dashboard/
- PayPal Agentic Toolkit: https://github.com/paypal/agent-toolkit (Needs verification)
- PayPal AI Toolkit: https://github.com/paypal/AI-Toolkit (Needs verification)
- OpenAI: https://platform.openai.com/docs
- FastAPI: https://fastapi.tiangolo.com
- Supabase: https://supabase.com
- Next.js: https://nextjs.org
- Tailwind: https://tailwindcss.com
6. High-Level Architecture Diagram
┌─────────────────────────────────────────────────────────────────────┐
│                         USER (BROWSER)                              │
│                    Next.js + Tailwind Dashboard                     │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ HTTPS (REST)
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI, Python)                     │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────────────┐ │
│  │  API Router │ │ PayPal Client│ │  OpenAI Client (tool use)   │ │
│  │  (endpoints)│ │  (httpx)     │ │  (function calling)         │ │
│  └──────┬──────┘ └──────┬───────┘ └───────────┬─────────────────┘ │
│         │               │                     │                    │
│         ▼               ▼                     ▼                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │             DETERMINISTIC SERVICE LAYER                     │  │
│  │  • OAuth token cache & refresh                              │  │
│  │  • Invoice sync & polling                                   │  │
│  │  • Priority score calculation (deterministic)               │  │
│  │  • Webhook signature verification & idempotency             │  │
│  │  • Approval gate enforcement                                │  │
│  └──────────────┬──────────────────────────────────────┬────────┘  │
│                 │                                      │            │
│                 ▼                                      ▼            │
│   ┌─────────────────────┐                   ┌──────────────┐      │
│   │  PostgreSQL (Supabase)│                 │  PayPal API  │      │
│   │  (users, invoices,    │ ◄───────────────►  (v2 REST)   │      │
│   │   messages, webhooks) │  HTTPS            │  Sandbox     │      │
│   └─────────────────────┘                   └──────────────┘      │
│                 ▲                                                   │
│                 │ HTTPS webhook (POST)                              │
└─────────────────┴───────────────────────────────────────────────────┘
                   ▲
                   │ HTTPS (webhook events: INVOICING.INVOICE.PAID, etc.)
                   ▼
            PAYPAL SANDBOX (webhook source)
Separation of concerns
Responsibility	Lives in	Notes
UI rendering, user auth session, displaying data	Frontend (Next.js)	Never touches PayPal secrets
API endpoints, business rules, PayPal client, OpenAI client, token cache, webhook listener	Backend (FastAPI)	Holds PAYPAL_CLIENT_SECRET (env var only)
Deterministic priority calc, status transitions, idempotency	Backend service layer	Ordinary Python code — no AI
Reminder text generation, reply intent classification, summarization	OpenAI (via function calling)	AI only where interpretation is valuable
Invoice data source of truth, payment confirmation	PayPal API	Backend never invents payment status
Durable state, audit log	PostgreSQL	Single source of truth for app state
Rule: No AI for deterministic tasks. Date math, status transitions, token caching, webhook verification, and priority scoring are ordinary backend code. OpenAI is used only for drafting messages, classifying free-text replies, and generating summaries.
7. Component Responsibilities
Frontend (Next.js)
- Pages: Login/Connect PayPal, Dashboard overview, Invoices list, AI Collection Agent (priorities + draft reminders), Customer Conversations, Reports, Settings.
- Calls backend REST endpoints only.
- Displays data returned by backend; never calls PayPal directly.
- Handles owner approval actions (approve/edit/reject a reminder draft).
- Shows collection summary and charts.
Backend (FastAPI)
- Auth: session management for the business owner (simple cookie/session; not PayPal OAuth — that's separate for the PayPal connection).
- PayPal client: httpx calls to api-m.sandbox.paypal.com; OAuth token cache with expiry; PayPal-Request-Id idempotency header on POSTs.
- Invoice sync: GET /v2/invoicing/invoices, GET /v2/invoicing/invoices/{id}; write to DB.
- Deterministic service layer: priority scoring, overdue detection, status machine (UNPAID → PAID only via webhook), duplicate-webhook detection.
- AI orchestration: builds system prompt + tool definitions, calls OpenAI with tool_choice, executes tool results, enforces approval gate.
- Webhook listener: POST /webhooks/paypal; verifies RSA signature (cert_url, transmission_id|transmission_time|webhook_id|body_hash); idempotent processing; 2xx response.
- Approvals: stores approval records; only sends a reminder after an approval_records row exists.
AI Agent (OpenAI function calling)
- Single agent: "Invoice Collection Agent."
- Receives context: current user's overdue invoices, customer message (if any), prior reminder history.
- Chooses which tools to call; backend executes them; results fed back.
- Never calls PayPal directly; never writes to DB directly; always via backend tools.
Database (PostgreSQL / Supabase)
- Durable store for users, PayPal connections, customers, invoices, messages, reminders, AI recommendations, webhook events, approvals.
- Source of truth for what the dashboard displays.
PayPal (Sandbox)
- Source of truth for invoice existence, amount, due date, payment status.
- Sends webhook events on state changes.
- /remind sends a PayPal-generated reminder email to the customer.
8. PayPal Integration Blueprint
A. Authentication (OAuth 2.0 client credentials)
Confirmed from PayPal docs:
- Endpoint: POST https://api-m.sandbox.paypal.com/v1/oauth2/token
- Auth: HTTP Basic (client_id:client_secret base64) + grant_type=client_credentials form body.
- Response: access_token, token_type: Bearer, expires_in (~28,800 s / 8 hrs; read actual value), scope.
- No refresh_token for client-credentials grant — re-request the token when expired.
- Cache token with expires_at; refresh proactively ~60s before expiry; don't fetch per request (rate-limit friendly).
- Required scope for invoicing read: https://uri.paypal.com/services/invoicing/invoices/read.
- Store PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET as backend environment variables only. Never in frontend.
- Sandbox base URL: https://api-m.sandbox.paypal.com; Production: https://api-m.paypal.com. Drive both from env vars (no hardcoding).
- Idempotency: include PayPal-Request-Id (UUID) header on every POST; reuse same UUID on retry.
B. PayPal Invoicing API v2 — required operations
Confirmed endpoints from PayPal docs:
#	Endpoint	Purpose	Calls it	Data returned	Essential to MVP?
1	GET /v2/invoicing/invoices	List invoices (page/page_size)	Backend (sync)	invoice items w/ id, status, amount, due_date, recipient email	✅ Yes
2	GET /v2/invoicing/invoices/{invoice_id}	Get single invoice details	Backend (tool: get_invoice_details)	Full invoice object	✅ Yes
3	POST /v2/invoicing/invoices	Create draft invoice	—	invoice ID	❌ No (MVP doesn't create invoices)
4	POST /v2/invoicing/invoices/{id}/send	Send a draft invoice	—	—	❌ No (invoices already sent via PayPal)
5	POST /v2/invoicing/invoices/{id}/remind	Send invoice reminder to payer	Backend (tool: send_invoice_reminder, needs approval)	202 accepted	✅ Yes (primary send path)
6	POST /v2/invoicing/invoices/{id}/cancel	Cancel sent invoice	—	—	❌ No
7	POST /v2/invoicing/invoices/{id}/payments	Record a payment	—	—	❌ No (webhook is source of truth)
8	POST /v2/invoicing/search-invoices	Multi-filter search	—	—	⚠️ Optional (list endpoint suffices for MVP)
Invoice statuses (confirmed enum): DRAFT, SENT, SCHEDULED, PAID, MARKED_AS_PAID, CANCELLED, REFUNDED, PARTIALLY_PAID, PARTIALLY_REFUNDED, MARKED_AS_REFUNDED, UNPAID, PAYMENT_PENDING, AUTO_CANCELLED, PAID_EXTERNAL, REFUNDED_EXTERNAL, SHARED.
Collection-relevant statuses: UNPAID, PARTIALLY_PAID, PAYMENT_PENDING = "outstanding"; PAID = collected.
Verified: /remind exists and sends a reminder to the payer. Needs verification: exact request body parameters for /remind (whether it accepts a custom message or only sends PayPal's default reminder). If /remind does not accept custom text, our AI-composed reminder must be sent via our own email channel (Resend) or copied by the owner — this is a documented limitation, not a blocker.
Avoid: Orders, Payouts, Subscriptions, Vault, disputes, credit APIs. Not required.
C. PayPal Webhooks
Confirmed from PayPal docs:
Relevant invoice webhook events:
- INVOICING.INVOICE.CREATED — draft created
- INVOICING.INVOICE.SENT — sent to recipient
- INVOICING.INVOICE.PAID — paid / partially paid / payment pending ← the key one for us
- INVOICING.INVOICE.REFUNDED
- INVOICING.INVOICE.UPDATED
- INVOICING.INVOICE.CANCELLED
- INVOICING.INVOICE.SCHEDULED
Webhook lifecycle:
1. In PayPal Developer Portal, create a REST app, add webhook listener URL (https://<backend>/webhooks/paypal), subscribe to invoicing events → get webhook_id.
2. PayPal POSTs event JSON to the listener URL.
3. Backend must respond HTTP 2xx quickly; otherwise PayPal retries up to 25 times over 3 days.
4. Backend verifies signature before processing:
- Read raw body (do not parse-then-re-serialize).
- Headers: PAYPAL-TRANSMISSION-ID, PAYPAL-TRANSMISSION-TIME, PAYPAL-CERT-URL, PAYPAL-AUTH-ALGO (RSA-SHA256), PAYPAL-TRANSMISSION-SIG.
- Verification string: transmission_id|transmission_time|webhook_id|sha256(raw_body).
- Download cert from cert_url, verify RSA-SHA256 signature.
- Reject if timestamp older than 5 minutes (replay protection).
5. Idempotency: store webhook_event.id in webhook_events table; skip if already processed.
6. On INVOICING.INVOICE.PAID: fetch invoice from PayPal (GET /v2/invoicing/invoices/{id}) to confirm status = PAID, update DB invoice status to PAID, set paid_at, flag collection_stopped = true, create audit log.
Webhook simulator: PayPal Developer Portal has a webhook simulator to generate mock events (mock webhook ID = WEBHOOK_ID; postback verification not supported for mock events). Useful for hackathon demo.
Verified limitation: INVOICING.INVOICE.PAID won't fire if the webhook is registered to a different PayPal app than the one whose credentials created the invoice. Must register webhook to the same sandbox app.
D. PayPal Agentic Toolkit — decision
Search did not return usable results for the Python Agentic Toolkit's invoice coverage.
Decision: Do not use PayPal Agentic Toolkit for MVP. Rationale:
- Invoice operation coverage in the toolkit is unconfirmed (Needs verification).
- Direct REST (httpx + 5–6 endpoints) is simpler, fully understood, easier to debug, and gives the student full control over approval gates and idempotency.
- The toolkit adds a dependency and abstraction layer without a clear benefit for this scope.
- Revisit post-hackathon if the toolkit matures and adds invoice read/remind tools.
E. PayPal AI Toolkit
- Purpose: skills/prompt library for PayPal-related AI tasks (per GitHub repo paypal/AI-Toolkit). Distinct from Agentic Toolkit.
- Not included in runtime architecture — no concrete benefit for MVP. Marked Needs verification if we later want pre-built PayPal agent skills.
F. PayPal Sandbox
- Developer dashboard provides default sandbox personal + business accounts; can create more.
- Test invoices appear in sandbox business account under Invoicing; status UNPAID after send.
- Simulate payment: mark invoice paid in sandbox business account, or trigger INVOICING.INVOICE.PAID via webhook simulator.
- Sandbox and live use separate base URLs and credentials; never mix.
- India-specific: A PayPal Business account is required to test integrations outside the US and to go live. PayPal's Acceptable Use Policy restricts personal payments in India (business invoicing is a different category, but production eligibility should be confirmed before claiming live India support). Needs verification: whether invoicing API in production is available to India-registered business accounts.
- Sandbox limitation: webhooks require a public HTTPS URL; during local dev use ngrok or deploy backend first. Sandbox email delivery may be delayed; for the demo, use the webhook simulator rather than waiting for real email.
Final minimal PayPal integration plan
- Essential APIs: GET /v2/invoicing/invoices, GET /v2/invoicing/invoices/{id}, POST /v2/invoicing/invoices/{id}/remind.
- Essential webhook: INVOICING.INVOICE.PAID (also subscribe to .UPDATED and .SENT for completeness).
- Authentication: OAuth client-credentials, token cache, sandbox base URL.
- Sandbox: developer account + sandbox business account; webhook simulator for demo.
- Optional: POST /v2/invoicing/search-invoices.
- Avoid: create/send/cancel invoices, payments/refunds recording, Orders/Payouts/Subscriptions.
9. AI Agent Architecture
Design choice: one agent, direct function calling
- No LangGraph — multi-agent orchestration is unnecessary complexity for this MVP.
- No OpenAI Agents SDK required — raw OpenAI Chat Completions with tools (function calling) is sufficient and easiest to debug.
- Model: gpt-4o-mini (cheap, fast, strong enough for classification + drafting).
- Needs verification: if the agent struggles with multi-step reasoning (e.g., "classify reply then recommend action then draft response"), escalate to OpenAI Agents SDK — but start with direct tool calling.
Agent definition
- Objective: Help the business owner collect unpaid PayPal invoices efficiently by prioritizing outstanding invoices, drafting personalized reminders, interpreting customer replies, and recommending follow-ups — always requiring owner approval before any message is sent.
- Instructions (system prompt): professional, polite tone; never invent payment status; never mark an invoice paid; only suggest actions backed by data; explain priority reasoning in plain language.
- Context provided per turn: user's business profile, synced invoices (status, amount, due date, days overdue, customer email), reminder history, any incoming customer message, prior AI recommendations.
- Available tools: see Tool Registry (§10). All tools executed by backend; agent only requests.
- Decision-making responsibilities: which invoices are top priority, what reminder text to draft, what intent a customer reply maps to, what follow-up action to recommend.
- Memory: short-term = current conversation context passed in prompt; long-term = reminder history, customer messages, AI recommendations stored in DB and fetched as context.
- Approval boundaries: agent may draft and recommend; agent may NOT send, mark paid, or change invoice data without an owner approval record.
- Error handling: if OpenAI call fails, return a graceful message ("AI temporarily unavailable; manual review needed"); if a tool returns an error, surface it to the owner without crashing.
Deterministic vs AI responsibilities (critical)
Task	Method	Why
Fetch invoices from PayPal	Backend code (httpx)	Deterministic API call
Compute days overdue	Backend code	Simple date math
Priority score	Backend code (weighted formula)	Transparent, auditable, deterministic
Mark invoice PAID	Backend only, triggered by verified webhook	Never trust AI for financial state
Send reminder	Backend only, after approval record	Consequential action
Draft reminder text	OpenAI	Requires language/context nuance
Classify reply intent	OpenAI	Free-text interpretation
Summarize collections	OpenAI	Synthesis
Priority scoring formula (transparent, deterministic)
For each outstanding invoice (status UNPAID / PARTIALLY_PAID / PAYMENT_PENDING, past due_date):
days_overdue = today - due_date   (0 if not yet overdue)
amount_tier  = amount / 1000   (capped)
reminders_sent = count of reminder_history for this invoice
has_promise = whether customer promised payment by a future date (from customer_messages)

priority_score =
  (days_overdue * 2.0) +
  (amount_tier * 1.5) +
  (10 if reminders_sent == 0 else 0) +
  (5 if reminders_sent <= 2 else -5) +
  (-20 if has_promise and promise_date > today else 0)
Higher score = higher priority. The agent explains the score in plain language (e.g., "High priority: $2,400 invoice, 18 days overdue, no reminder sent yet").
Intent categories and recommended actions
Category	Definition	Recommended action
Payment completed	Customer says they paid	Verify via PayPal/webhook; if confirmed, stop reminders; else ask for transaction ID
Payment promised	Customer commits to pay by a date	Record promise date; suppress reminders until date passes; follow up day after
Extension requested	Customer asks for more time	Recommend owner review; suggest new due date; draft acknowledgment
Invoice clarification	Customer questions amount/items	Recommend owner review invoice details; draft clarification offer
Dispute/issue	Customer disputes charge or flags problem	Flag for owner manual intervention; pause automated reminders
No clear response	Unclear or unrelated reply	Recommend a polite follow-up reminder
10. Complete Tool Registry
Legend: PayPal API op = calls PayPal REST; Backend fn = ordinary Python function; AI tool = function exposed to OpenAI; External notification = email/PayPal remind. "Approval required" = owner must approve before execution.
#	Tool name	Type	Purpose	Input	Output	Calls	Read/Write	Approval required?
1	get_invoices	Backend fn (exposed as AI tool)	Retrieve user's invoices	user_id, optional status filter	List of invoices (id, number, customer, amount, status, due_date, balance)	PayPal GET /invoices + DB	Read	No
2	get_invoice_details	Backend fn (AI tool)	Get one invoice	invoice_id	Full invoice object	PayPal GET /invoices/{id}	Read	No
3	analyze_overdue_invoices	Backend fn (deterministic)	Identify overdue invoices	user_id	List of overdue invoices w/ days overdue	DB	Read	No
4	calculate_collection_priority	Backend fn (deterministic)	Rank by urgency	invoice list	Prioritized list w/ score & reason	DB	Read	No
5	generate_reminder	AI tool (OpenAI)	Draft personalized reminder	invoice_id, customer context, tone	Reminder text (subject + body)	None (LLM)	Read (generates draft only)	Yes (before send)
6	send_invoice_reminder	Backend fn (AI tool, gated)	Trigger PayPal reminder	invoice_id, approved_reminder_text	Confirmation (PayPal 202 or logged)	PayPal POST /remind	Write (external)	Yes
7	classify_customer_reply	AI tool (OpenAI)	Classify reply intent	message_text, customer, invoice	Intent category + confidence	None (LLM)	Read	No
8	recommend_followup	AI tool (OpenAI)	Recommend next action	intent category, invoice, history	Action type + timing + draft	None (LLM)	Read	No (recommendation only)
9	get_payment_status	Backend fn (AI tool)	Check current payment status	invoice_id	Status + paid_at + amount paid	PayPal GET /invoices/{id}	Read	No
10	get_collection_summary	Backend fn (+ OpenAI)	Collection report	user_id	Totals (outstanding, overdue, collected, promised)	DB	Read	No
Approval-gated tools (require approval_records row before execution)
- send_invoice_reminder — sends external communication.
- Any future "mark paid" or "change terms" tool — explicitly NOT in MVP.
Tools safe for automatic execution (no approval)
- All read-only tools (get_invoices, get_invoice_details, analyze_overdue_invoices, calculate_collection_priority, get_payment_status, get_collection_summary).
- classify_customer_reply and recommend_followup (produce recommendations only; owner decides).
11. Five End-to-End Workflows
Workflow 1: Overdue invoice detection
1. User connects PayPal (OAuth; backend stores connection).
2. Backend retrieves invoices via GET /v2/invoicing/invoices (PayPal).
3. Database stores synchronized invoices (customers + invoices tables).
4. Backend identifies overdue: status ∈ {UNPAID, PARTIALLY_PAID} and due_date < today.
5. Agent analyzes context: fetches reminder history, customer messages.
6. Priority score: deterministic formula (backend).
7. Agent generates recommended actions: drafts reminder for top-priority invoice (OpenAI).
8. Dashboard displays prioritized list.
- AI decision: which invoice is top priority + draft reminder text.
- DB changes: invoices, customers, reminder_history, ai_recommendations inserted/updated.
- Failure scenarios: PayPal 401 (token expired → refresh), 403 (missing invoicing scope → surface config error), network timeout → retry with backoff.
- Demo-able in Sandbox: Yes.
Workflow 2: Payment reminder
1. Agent identifies an invoice requiring follow-up (top priority).
2. Agent generates personalized reminder (OpenAI generate_reminder).
3. Owner reviews draft on dashboard; may edit.
4. Owner approves → approval_records row created.
5. Backend sends: calls PayPal POST /remind (generic PayPal reminder) and/or logs custom message; if using custom email channel, calls Resend with AI-composed body.
6. Action logged: reminder_history row (invoice_id, sent_at, channel, approval_id).
7. Dashboard shows "Reminder sent" + next follow-up date.
- AI decision: reminder text content.
- DB changes: reminder_history, approval_records.
- Failure: PayPal /remind error → surface to owner, do not retry blindly (idempotency via PayPal-Request-Id).
- Demo-able in Sandbox: Yes (PayPal sends real sandbox email; verify in sandbox customer inbox or simulate).
Workflow 3: Customer requests an extension
1. Customer sends response (entered by owner via dashboard "log customer reply" or simulated inbox for demo).
2. Backend receives message → customer_messages row.
3. AI classifies intent (classify_customer_reply) → "Extension requested".
4. Agent understands context: invoice, due date, promise history.
5. Agent recommends response (recommend_followup) → acknowledge, propose new due date, flag for owner.
6. Owner approves response draft.
7. Follow-up schedule updated: set next_follow_up = promised date + 1 day; suppress reminders until then.
- AI decision: intent category + recommended response.
- DB changes: customer_messages, ai_recommendations, invoices.next_follow_up.
- Failure: ambiguous reply → classify as "No clear response," recommend owner manual reply.
- Demo-able in Sandbox: Yes (simulated customer reply; no real email needed).
Workflow 4: Payment received
1. PayPal sends webhook INVOICING.INVOICE.PAID to POST /webhooks/paypal.
2. Backend verifies signature (RSA cert check, 5-min timestamp window).
3. Backend processes idempotently: check webhook_events.id not already processed.
4. Invoice status updated: invoice.status = PAID, paid_at, paid_amount, collection_stopped = true.
5. Agent stops reminders: no further send_invoice_reminder for this invoice; clear pending follow-ups.
6. Dashboard + reports updated (invoice moves to "Collected").
- AI decision: none (deterministic).
- DB changes: invoices, webhook_events, audit_log.
- Failure scenarios: bad signature → 400 reject; duplicate event → skip (idempotent); webhook while backend sleeping (Render free tier) → PayPal retries up to 25 times over 3 days; missed event → owner can manually sync via "refresh from PayPal."
- Demo-able in Sandbox: Yes via webhook simulator (INVOICING.INVOICE.PAID mock event).
Workflow 5: Daily collection summary
1. Backend retrieves current invoices from PayPal (or uses cached DB state).
2. Metrics calculated: total outstanding, overdue, collected, promised, count needing attention.
3. Agent summarizes important changes (OpenAI): "3 new overdue invoices totaling $4,200; 1 customer promised payment by Friday; 2 invoices paid today."
4. Dashboard displays report section.
- AI decision: summary narrative.
- DB changes: none (read-only); optional ai_recommendations log.
- Demo-able in Sandbox: Yes.
12. Database Schema and ER Diagram
Principle
Store locally: app state, approvals, messages, AI recommendations, webhook log, derived priority.
Always retrieve from PayPal (source of truth): current invoice status, amount, due date — synced on demand and via webhooks; do not cache payment status long-term without webhook confirmation.
Avoid storing sensitive data: never store PayPal credentials or customer passwords; store only email and invoice reference.
ER Diagram (Mermaid)
erDiagram
    users ||--o{ paypal_connections : owns
    users ||--o{ customers : has
    users ||--o{ ai_recommendations : generates
    users ||--o{ approval_records : approves
    paypal_connections ||--o{ invoices : syncs
    customers ||--o{ invoices : receives
    customers ||--o{ customer_messages : sends
    invoices ||--o{ reminder_history : generates
    invoices ||--o{ ai_recommendations : receives
    invoices ||--o{ webhook_events : triggers
    customer_messages ||--o{ ai_recommendations : informs
    approval_records ||--o{ reminder_history : authorizes
Entities
Entity	Fields (type)	PK	FK	Notes
users	id UUID, email text, name text, created_at timestamptz	id	—	Business owner account
paypal_connections	id UUID, user_id UUID, paypal_access_token_encrypted text, token_expires_at timestamptz, sandbox_business_email text, webhook_id text, created_at timestamptz	id	user_id → users	Encrypt token at rest (Needs verification: choose encryption lib)
customers	id UUID, user_id UUID, name text, email text, created_at timestamptz	id	user_id → users	One customer per email per user
invoices	id UUID, paypal_invoice_id text, user_id UUID, customer_id FK, invoice_number text, amount_cents integer, currency text, status text, due_date date, balance_due_cents integer, paid_at timestamptz, collection_stopped boolean, next_follow_up date, created_at timestamptz, updated_at timestamptz	id	user_id, customer_id	paypal_invoice_id = PayPal invoice ID (INV2-...)
invoice_activity	id UUID, invoice_id FK, event_type text, event_data jsonb, created_at timestamptz	id	invoice_id	Audit trail of status changes
reminder_history	id UUID, invoice_id FK, approval_id FK, channel text, sent_at timestamptz, message_preview text, paypal_request_id text	id	invoice_id, approval_id	One row per sent reminder
customer_messages	id UUID, customer_id FK, message_text text, direction text (inbound/outbound), received_at timestamptz, intent_category text, intent_confidence real	id	customer_id	Logged customer replies
ai_recommendations	id UUID, user_id UUID, invoice_id FK, customer_message_id FK, type text, content jsonb, status text (pending/approved/rejected), created_at timestamptz	id	user_id, invoice_id, customer_message_id	Agent's draft recommendations
webhook_events	id UUID, paypal_event_id text unique, event_type text, received_at timestamptz, processed boolean	id	—	Idempotency log for webhooks
approval_records	id UUID, user_id UUID, ai_recommendation_id FK, action text, approved boolean, decided_at timestamptz, editor_note text	id	user_id, ai_recommendation_id	Human approval gate
Important indexes
- invoices(user_id, status) — dashboard queries.
- invoices(paypal_invoice_id) — webhook lookup.
- invoices(due_date) — overdue detection.
- reminder_history(invoice_id, sent_at) — follow-up scheduling.
- webhook_events(paypal_invoice_id) — duplicate detection.
- customer_messages(customer_id, received_at) — conversation history.
What is stored locally vs retrieved from PayPal
- Locally: invoice snapshot at sync time, priority score, reminder history, messages, approvals, webhook log.
- From PayPal (live): current payment status (only trust webhook-verified PAID), full invoice details on demand.
13. Security and Approval Architecture
Safeguards
 1. OAuth credential storage: PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET as backend environment variables only. Never in frontend, never committed to git (use .env + .gitignore). PayPal access tokens encrypted at rest in paypal_connections (Needs verification: encryption approach — Fernet or Supabase pgcrypto).
 2. No frontend PayPal calls: frontend talks only to our backend; backend holds secrets and calls PayPal.
 3. Authentication/authorization: simple owner session; every backend endpoint checks user_id; users only see their own invoices/connections.
 4. Webhook signature verification: RSA-SHA256 via cert_url (as specified by PayPal); reject invalid signatures with 400; validate timestamp within 5 minutes.
 5. Duplicate webhook prevention: webhook_events.paypal_event_id UNIQUE + idempotency check before processing.
 6. API rate limits: cache OAuth token (don't fetch per request); exponential backoff on 429/5xx; respect PayPal rate-limit headers.
 7. Retry handling: bounded retries (max 3) with jitter for transient failures; idempotency key (PayPal-Request-Id) reused on retries.
 8. API failures/timeouts: circuit-breaker-lite (fail closed, surface error to owner); dashboard shows "PayPal sync failed — retry."
 9. Database consistency: transactions for invoice status + invoice_activity together; foreign keys enforced.
10. Audit logs: invoice_activity + reminder_history + approval_records record who did what and when.
11. Customer data protection: only store email/name/invoice reference; no payment instruments; messages not logged beyond needed context.
12. AI-generated message validation: owner reviews/edits before send; system strips any content that claims payment was received or changes terms; length limits on reminder text.
13. Human approval before external actions: send_invoice_reminder requires an approval_records row. No auto-send.
The AI agent must never (hard rules enforced in backend)
- Invent a payment confirmation.
- Mark an invoice PAID unless a verified webhook (or explicit owner action via approved record) confirms it.
- Send repeated reminders due to duplicate webhook events (idempotency).
- Change invoice amounts, due dates, or payment terms.
- Make unauthorized financial decisions (refunds, cancellations).
How safeguards fit the architecture
Owner requests "send reminder"
        │
        ▼
Backend checks approval_records for this reminder draft
        │
        ├─ No approval → 403 "Owner approval required"
        │
        ├─ Approval exists → call PayPal POST /remind
        │                              │
        │                              ▼
        │                    Log reminder_history (channel, paypal_request_id)
        │                              │
        │                              ▼
        │                    Return confirmation to frontend
        │
        ▼
Frontend shows "Reminder sent" (never auto-sends again)
14. Development Roadmap — No Implementation Yet
Phase 1: Foundation
Objective: Set up repo, frontend shell, backend shell, database, basic auth.
Tasks (in order):
1. Initialize GitHub repo; add .gitignore, .env.example.
2. Scaffold Next.js (frontend) + FastAPI (backend) in same repo or two folders.
3. Tailwind CSS + basic layout (nav, placeholder pages).
4. Supabase PostgreSQL provisioned; connection string in env.
5. SQL schema (all entities from §12) applied via migration.
6. Simple owner login/session (email + password or magic link) — auth for dashboard only.
Dependencies: GitHub, Supabase account.
Expected output: Running frontend + backend connected to DB; empty dashboard.
Definition of done: npm run dev and uvicorn both start; DB migration applies; health endpoint returns 200.
Testing: health check; DB migration applies cleanly.
Phase 2: PayPal Integration
Objective: Connect to PayPal Sandbox and sync invoices.
Tasks (in order):
1. Create PayPal Developer account + sandbox app; get client ID/secret; note sandbox business account email.
2. Add env vars: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_BASE_URL=sandbox.
3. Backend: OAuth client-credentials token cache + refresh logic.
4. Backend: GET /v2/invoicing/invoices sync endpoint; store customers+invoices in DB.
5. Backend: GET /v2/invoicing/invoices/{id} details endpoint.
6. Frontend: "Connect PayPal" button → store connection; dashboard shows synced invoices list.
7. Register webhook URL in PayPal Developer Portal (needs public URL — deploy backend or use ngrok); subscribe to invoicing events; store webhook_id.
8. Backend: webhook listener POST /webhooks/paypal with signature verification + idempotency (stub processing: log event only).
Dependencies: Phase 1; PayPal Developer account.
Expected output: Sandbox invoices appear in dashboard; webhook endpoint receives and logs events.
Definition of done: Owner can connect PayPal and see their sandbox invoices with status/amount/due date.
Testing: Sandbox invoice list matches sandbox business account; invalid webhook signature returns 400.
Phase 3: Core Collection Logic
Objective: Detect overdue invoices, prioritize, display.
Tasks (in order):
1. Backend: analyze_overdue_invoices (status overdue + due_date < today).
2. Backend: calculate_collection_priority deterministic formula.
3. Frontend: Invoices page (list, status badge, due date, days overdue, priority badge).
4. Frontend: Overview cards (total outstanding, overdue count, collected, upcoming).
5. Backend: invoice sync on demand + periodic background refresh (cron or on page load).
Dependencies: Phase 2.
Expected output: Prioritized overdue invoice list on dashboard.
Definition of done: Overdue invoices highlighted; priority score and reason shown.
Testing: manually create overdue sandbox invoices; verify they appear top of list.
Phase 4: AI Agent
Objective: Agent drafts reminders, classifies replies, recommends actions.
Tasks (in order):
1. OpenAI account; API key env var; set usage limit.
2. Backend: OpenAI client; system prompt for Invoice Collection Agent.
3. Backend: expose tools to OpenAI (get_invoices, get_invoice_details, generate_reminder, classify_customer_reply, recommend_followup, get_payment_status, get_collection_summary).
4. Agent: reminder generation for top-priority invoice.
5. Agent: reply intent classification (test with sample messages).
6. Agent: follow-up recommendation per intent category.
7. Frontend: AI Collection Agent page (priority list + "Generate reminder" button + draft display).
8. Frontend: Customer Conversations page (log reply, see classification, see recommendation).
Dependencies: Phase 3; OpenAI API key.
Expected output: AI-written reminder drafts; classified replies with recommendations.
Definition of done: Agent produces a sensible reminder for an overdue invoice and classifies a sample reply correctly.
Testing: unit-test intent classification with 5 sample replies per category.
Phase 5: Approval and Automation
Objective: Human-approval gate; send reminders; stop on payment.
Tasks (in order):
1. Backend: approval_records; endpoint to approve/edit/reject a draft.
2. Backend: send_invoice_reminder gated on approval; calls PayPal /remind; logs reminder_history.
3. Frontend: approve/edit/reject UI on reminder draft.
4. Backend: webhook processing for INVOICING.INVOICE.PAID → update invoice status, collection_stopped=true.
5. Backend: stop-follow-up logic (skip invoices where collection_stopped).
6. Frontend: invoice status reflects Paid; removed from overdue list.
Dependencies: Phase 4; PayPal webhook public URL.
Expected output: Approved reminders sent; paid invoices auto-stopped.
Definition of done: Approve a reminder → PayPal /remind called → logged; webhook PAID → invoice marked Paid and reminders stop.
Testing: webhook simulator sends PAID; verify dashboard updates; duplicate webhook → no double processing.
Phase 6: Reports and Polish
Objective: Collection summary, UI polish, error handling, deployment.
Tasks (in order):
1. Backend: get_collection_summary metrics + OpenAI summary narrative.
2. Frontend: Reports page (outstanding, overdue, collected, promised, chart optional).
3. Error handling: graceful messages for PayPal/OpenAI failures; retry UI.
4. Deployment: frontend to Vercel, backend to Render/Railway; env vars configured.
5. Demo rehearsal (3–5 min script).
Dependencies: Phase 5.
Expected output: Deployed, demoable app.
Definition of done: Deployed app passes demo script end-to-end.
Testing: full demo walkthrough; error-state walkthrough (PayPal down, OpenAI down).
MVP vs Future enhancements
MVP (hackathon): PayPal connect, invoice sync, overdue detection, AI priority, reminder draft + owner approval, send via PayPal /remind, customer reply classification, webhook PAID stops reminders, collection summary, deployed demo.
Future: custom email channel (Resend), create/send invoices from app, multi-business, recurring invoices, mobile app, Slack/Teams notifications, advanced reports export, live PayPal production (requires business approval).
15. Testing Strategy
Test-case matrix
ID	Workflow	Case	Steps	Expected result
T1	Overdue detection	Normal	Sandbox has 3 invoices: 2 overdue, 1 current	Dashboard shows 2 overdue, prioritized
T2	Priority	Normal	High-amount + old overdue vs low-amount + new	High/old ranks top with reason shown
T3	Reminder	Normal	Generate draft → owner approves → send	PayPal /remind called; logged; dashboard shows sent
T4	Reminder	Edge	Owner edits draft before approving	Edited text stored; approval record reflects edit
T5	Reply classification	Normal	"I can pay next Friday"	Classified "Payment promised"; follow-up set to Saturday
T6	Reply classification	Edge	"Thanks" / unclear	Classified "No clear response"; recommend manual follow-up
T7	Reply classification	Edge	"I dispute this charge"	Classified "Dispute/issue"; pause reminders; flag owner
T8	Payment received	Normal	Webhook simulator INVOICING.INVOICE.PAID	Invoice → Paid; collection_stopped; removed from overdue
T9	Payment received	Failure	Invalid webhook signature	400; event not processed; no status change
T10	Payment received	Edge	Duplicate webhook event (same ID)	Second event skipped (idempotent); no duplicate reminder stop
T11	Summary	Normal	Open Reports page	Totals match DB; AI narrative generated
T12	Auth	Edge	Backend token expired mid-sync	Auto-refresh; sync completes; no 401 surfaced to user
T13	PayPal API	Failure	PayPal returns 500	Backend returns graceful error; dashboard shows "sync failed"
What must be genuinely integrated vs simulated
- Genuinely integrated: OAuth + token cache, invoice list/details sync, PayPal /remind, webhook listener + signature verification, DB persistence, OpenAI calls.
- Sandbox-supported: All of the above in Sandbox; webhook simulator for PAID event.
- Simulated (if needed): Customer inbound email (enter reply manually in dashboard), custom email sending (Resend not configured — log "would send" instead), real customer paying (mark paid via sandbox dashboard or webhook simulator).
- Never present simulated as real: Label demo steps clearly ("Sandbox webhook simulator," "Manual reply entry for demo"). Do not claim live PayPal production integration.
16. Hackathon Demo Script (3–5 minutes)
Setup before demo (done offline, not during demo):
- Sandbox app created, webhook registered to backend public URL, backend deployed, a few sandbox invoices created (some overdue, some current), one sandbox invoice already marked paid.
Minute 0–1: The problem + connect
- Open dashboard; show empty state or previous data.
- Click "Connect PayPal (Sandbox)"; OAuth flow; sandbox business account linked.
- Invoices load from PayPal: show list with status, amount, due date. Say: "These are real sandbox invoices from PayPal."
Minute 1–2: AI prioritization
- Go to AI Collection Agent; show overdue invoices ranked.
- Click top invoice; show priority score breakdown (days overdue, amount, no reminder yet) and the AI's plain-language reason.
- Say: "The agent decided this $2,400 invoice, 18 days overdue with no reminder, is top priority — not just the oldest one."
Minute 2–3: Reminder + approval
- Click "Generate reminder"; AI writes personalized text.
- Owner edits one sentence; clicks "Approve and send."
- Backend calls PayPal /remind; dashboard shows "Reminder sent" with timestamp.
- Say: "The AI drafted it, but the human approved it — and only then did PayPal send the reminder."
Minute 3–4: Customer reply
- Simulate a customer reply: paste "Can I pay next Friday?" into Customer Conversations.
- AI classifies: "Payment promised"; recommends follow-up after Friday; owner approves.
- Dashboard schedules follow-up and suppresses reminders until then.
Minute 4–5: Payment received + summary
- Trigger webhook simulator: INVOICING.INVOICE.PAID for the top invoice.
- Invoice moves to "Paid"; reminder queue stops; dashboard updates.
- Open Reports: outstanding/collected totals + AI one-line summary.
- Close: "PayPal confirms payment; our agent stops chasing automatically."
Anti-fake disclosure (say explicitly): "All PayPal operations here run against PayPal Sandbox. The webhook event was generated by PayPal's webhook simulator. This is not live production money."
17. Risks, Limitations, and Feasibility
Risk	Impact	Likelihood	Mitigation	Fallback
PayPal Invoice API doesn't support custom reminder text via /remind	Medium	Medium (unconfirmed)	Verify /remind params early; if no custom text, owner copies AI draft into their own email or PayPal sends generic reminder	Log AI draft for manual send; mark as "manual send" in UI
Agentic Toolkit invoice coverage uncertain	Low	High	Not used; direct REST only	N/A
India production eligibility for invoicing API	Medium	Low	Sandbox only for hackathon; state clearly that production India access needs verification	Demo explicitly sandbox-scoped
Sandbox webhook needs public HTTPS URL	Medium	Medium	Deploy backend before testing webhooks; or use ngrok locally; webhook simulator for demo	Manual "sync from PayPal" button
Render free tier spins down backend	Medium	High	Keep backend awake during demo; or use Railway free trial	Demo from a kept-alive instance; note as known limitation
OpenAI API cost / rate limit	Low	Low	gpt-4o-mini; set usage limit; cache summaries	Reduce OpenAI calls; fallback to templates
AI hallucinates payment status	High	Low	Hard rule: PAID only from verified webhook; backend enforces	Never expose AI-determined payment status
Duplicate webhook → repeated reminders	Medium	Low	Idempotency via webhook_events + PayPal-Request-Id	Manual cleanup in DB
Email replies not actually received	Medium	High	Manual reply entry in dashboard for hackathon; Resend optional later	Simulated inbound channel clearly labeled
Development time overrun	High	Medium	Strict MVP scope; cut charts/email/custom invoices	Demo core 3 workflows only
18. MVP vs Future Features
 	MVP (this hackathon)	Future (post-hackathon)
PayPal connection	Sandbox OAuth	Live production (business approval needed)
Invoice sync	Read-only from PayPal	Create/send invoices from app
Reminders	AI draft + owner approval + PayPal /remind	Custom email via Resend; SMS
Customer replies	Manual entry / simulated	Real inbox integration
Payment stop	Webhook INVOICING.INVOICE.PAID	Same, more event types
Reports	Dashboard summary	PDF/CSV export, trends
Multi-user	Single owner	Team roles
Agent	Single OpenAI agent	Multi-agent (LangGraph) if justified
19. Final Implementation Checklist (for OpenCode)
Ordered list to hand to OpenCode in later stages:
 1. Repo init, .gitignore, .env.example, project folder structure (frontend /web, backend /api).
 2. Next.js + Tailwind scaffold; basic navigation and placeholder pages.
 3. FastAPI scaffold; health endpoint; Pydantic schemas.
 4. Supabase Postgres; apply SQL schema (all entities + indexes).
 5. Owner authentication (sessions) + middleware protecting routes.
 6. PayPal env vars; OAuth client-credentials token cache + refresh.
 7. GET /v2/invoicing/invoices sync → customers + invoices tables.
 8. GET /v2/invoicing/invoices/{id} details endpoint.
 9. Frontend: Connect PayPal page + invoices list page + overview cards.
10. Overdue detection + deterministic priority calculation.
11. Frontend: AI Collection Agent page with priority ranking + reason.
12. OpenAI integration; system prompt; tool definitions exposed.
13. generate_reminder tool (AI drafts text).
14. classify_customer_reply + recommend_followup tools.
15. Approval records + approve/edit/reject UI + gated send_invoice_reminder (PayPal /remind).
16. Reminder history logging.
17. Webhook listener with signature verification + idempotency; INVOICING.INVOICE.PAID handler.
18. Stop-follow-up logic on PAID; dashboard status update.
19. Customer Conversations page (log reply, see classification/recommendation).
20. Collection summary + Reports page.
21. Error handling and retry logic throughout.
22. Deploy frontend (Vercel) + backend (Render/Railway); configure env vars; register public webhook URL.
23. Demo rehearsal with Sandbox + webhook simulator.
24. Record demo video (backup in case live demo fails).
20. Unresolved Decisions and Questions
Mark these Needs verification before/during implementation:
1. PayPal Agentic Toolkit: Does the Python toolkit expose invoices.list, invoices.get, and invoices.remind? If yes and it's stable, it could simplify tool definitions; otherwise direct REST (chosen) remains. Unconfirmed
2. PayPal /remind custom text: Does POST /v2/invoicing/invoices/{id}/remind accept a custom reminder message, or only PayPal's default? Determines whether we need a separate email channel (Resend) for AI-composed reminders. Needs verification
3. OpenAI function calling sufficiency: Is single-agent direct tool calling enough for the classify→recommend→draft flow, or do we need OpenAI Agents SDK? Start with direct calling; escalate only if reasoning breaks. Likely sufficient
4. India production eligibility: Can an India-registered PayPal Business account use the Invoicing API in production? Hackathon uses Sandbox only, but state this limitation honestly. Needs verification
5. Token encryption at rest: Which library to encrypt PayPal access tokens in paypal_connections? (e.g., cryptography Fernet.) Implementation detail
6. Backend hosting: Render free tier spins down; confirm a kept-alive option for the demo (Railway free trial or paid tier). Deployment decision
7. Email channel: Confirm whether to integrate Resend/SendGrid for custom AI-composed emails or keep PayPal /remind + manual send for MVP. Scope decision
Recommended implementation order for OpenCode
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 as detailed in §14. Do not start coding until this blueprint is reviewed and the PayPal Sandbox app + webhook URL are provisioned. Begin with repo setup and the PayPal OAuth/invoice-sync plumbing, since everything else depends on it.
End of blueprint. No code was written, no files created, no packages installed, and no implementation started. This document is the complete specification to hand to OpenCode for implementation.
⋮⋮⋮⋮
⋮⋮⋮⋮⋮⋮⋮⋮
⋮⋮⋮⋮⋮⋮⋮⋮