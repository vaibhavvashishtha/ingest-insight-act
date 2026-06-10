"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import {
  type ApiLogEntry,
  type CampaignPlan,
  type DataSource,
  type IngestionJob,
  type Insight,
  type Report,
  campaigns,
  dev,
  ingestion,
  insights,
  queryData,
  reports,
  setApiCaptureHook,
  setDevTenantId,
  sources,
} from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

type StepStatus = "locked" | "idle" | "loading" | "success" | "error";

interface HarnessState {
  tenantId: string;
  stepStatuses: Record<number, StepStatus>;
  stepData: {
    source?: DataSource;
    ingestionJob?: IngestionJob;
    queryResults?: Record<string, unknown>[];
    insight?: Insight;
    report?: Report;
    campaignPlan?: CampaignPlan;
    generatedContent?: Record<string, unknown>;
  };
  logs: Record<number, ApiLogEntry[]>;
  activeLogTab: number;
}

type Action =
  | { type: "SET_TENANT_ID"; id: string }
  | { type: "SET_STEP_STATUS"; step: number; status: StepStatus }
  | { type: "SET_STEP_DATA"; key: keyof HarnessState["stepData"]; value: unknown }
  | { type: "APPEND_LOG"; step: number; entry: ApiLogEntry }
  | { type: "SET_ACTIVE_LOG_TAB"; step: number };

const initState = (): HarnessState => ({
  tenantId:
    typeof window !== "undefined"
      ? localStorage.getItem("harness_tenant_id") ?? ""
      : "",
  stepStatuses: { 1: "idle", 2: "locked", 3: "locked", 4: "locked", 5: "locked", 6: "locked", 7: "locked", 8: "locked" },
  stepData: {},
  logs: {},
  activeLogTab: 1,
});

function reducer(state: HarnessState, action: Action): HarnessState {
  switch (action.type) {
    case "SET_TENANT_ID":
      return { ...state, tenantId: action.id };
    case "SET_STEP_STATUS": {
      const next = { ...state.stepStatuses, [action.step]: action.status };
      // Auto-unlock next step on success
      if (action.status === "success" && action.step < 8) {
        next[action.step + 1] = "idle";
      }
      return { ...state, stepStatuses: next };
    }
    case "SET_STEP_DATA":
      return { ...state, stepData: { ...state.stepData, [action.key]: action.value } };
    case "APPEND_LOG": {
      const existing = state.logs[action.step] ?? [];
      return { ...state, logs: { ...state.logs, [action.step]: [...existing, action.entry] } };
    }
    case "SET_ACTIVE_LOG_TAB":
      return { ...state, activeLogTab: action.step };
    default:
      return state;
  }
}

// ── usePoll hook ───────────────────────────────────────────────────────────

function usePoll<T>(
  fetcher: () => Promise<T>,
  shouldStop: (data: T) => boolean,
  onResult: (data: T) => void,
  onTimeout: () => void,
  intervalMs = 2000,
  timeoutMs = 60000
) {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startRef = useRef<number>(0);
  const cbRef = useRef({ fetcher, shouldStop, onResult, onTimeout });
  cbRef.current = { fetcher, shouldStop, onResult, onTimeout };

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    stop();
    startRef.current = Date.now();
    intervalRef.current = setInterval(async () => {
      if (Date.now() - startRef.current > timeoutMs) {
        stop();
        cbRef.current.onTimeout();
        return;
      }
      try {
        const data = await cbRef.current.fetcher();
        cbRef.current.onResult(data);
        if (cbRef.current.shouldStop(data)) stop();
      } catch {
        // keep polling on transient errors
      }
    }, intervalMs);
  }, [stop, intervalMs, timeoutMs]);

  useEffect(() => () => stop(), [stop]);

  return { start, stop };
}

// ── JSON Inspector ─────────────────────────────────────────────────────────

function JsonInspector({
  logs,
  activeTab,
  onTabChange,
}: {
  logs: Record<number, ApiLogEntry[]>;
  activeTab: number;
  onTabChange: (step: number) => void;
}) {
  const tabs = Object.entries(logs)
    .filter(([, entries]) => entries.length > 0)
    .map(([step]) => Number(step));

  const activeEntries = logs[activeTab] ?? [];

  return (
    <div className="bg-gray-950 rounded-lg border border-gray-800 overflow-hidden">
      <div className="px-3 py-2 bg-gray-900 text-xs font-mono text-gray-400 border-b border-gray-800">
        API Inspector
      </div>
      {tabs.length === 0 ? (
        <div className="p-4 text-xs text-gray-500 font-mono">No requests yet...</div>
      ) : (
        <>
          <div className="flex flex-wrap gap-1 px-2 pt-2 pb-0">
            {tabs.map((step) => (
              <button
                key={step}
                onClick={() => onTabChange(step)}
                className={`text-xs px-2 py-1 rounded-t font-mono ${
                  activeTab === step
                    ? "bg-gray-700 text-green-300"
                    : "bg-gray-900 text-gray-500 hover:text-gray-300"
                }`}
              >
                Step {step}
              </button>
            ))}
          </div>
          <div className="overflow-y-auto max-h-[calc(100vh-160px)] space-y-3 p-3">
            {activeEntries.map((entry, i) => (
              <div key={i} className="text-xs font-mono border border-gray-800 rounded">
                <div className="flex items-center justify-between bg-gray-800 px-2 py-1">
                  <span>
                    <span className="text-yellow-400">{entry.method}</span>{" "}
                    <span className="text-gray-300">{entry.url.replace("http://localhost:8000/api/v1", "")}</span>{" "}
                    <span className={entry.status < 300 ? "text-green-400" : "text-red-400"}>
                      {entry.status}
                    </span>{" "}
                    <span className="text-gray-500">{entry.latencyMs}ms</span>
                  </span>
                </div>
                {entry.requestBody !== undefined && (
                  <LogSection label="Request" data={entry.requestBody} />
                )}
                <LogSection label="Response" data={entry.responseBody} />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function LogSection({ label, data }: { label: string; data: unknown }) {
  const text = JSON.stringify(data, null, 2);
  return (
    <div>
      <div className="flex items-center justify-between px-2 py-0.5 bg-gray-900 text-gray-500">
        <span>{label}</span>
        <button
          onClick={() => navigator.clipboard.writeText(text)}
          className="hover:text-gray-300 text-xs"
        >
          copy
        </button>
      </div>
      <pre className="text-green-300 px-2 py-2 overflow-x-auto text-[11px] leading-relaxed">
        {text}
      </pre>
    </div>
  );
}

// ── Help popover ───────────────────────────────────────────────────────────

interface FieldHelp {
  field: string;
  description: string;
  example: string;
}

function HelpPopover({
  fields,
  onFillDefaults,
}: {
  fields: FieldHelp[];
  onFillDefaults?: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-5 h-5 rounded-full bg-gray-100 hover:bg-indigo-100 text-gray-500 hover:text-indigo-600 text-xs font-bold flex items-center justify-center"
        title="What goes in these fields?"
      >
        ?
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-7 z-20 w-80 bg-white border border-gray-200 rounded-lg shadow-lg p-4">
            <div className="text-xs font-semibold uppercase text-gray-500 mb-2">Field reference</div>
            <div className="space-y-2 text-xs">
              {fields.map((f) => (
                <div key={f.field}>
                  <div className="font-mono font-semibold text-indigo-700">{f.field}</div>
                  <div className="text-gray-600">{f.description}</div>
                  <div className="text-gray-400 font-mono mt-0.5">e.g. {f.example}</div>
                </div>
              ))}
            </div>
            {onFillDefaults && (
              <button
                onClick={() => {
                  onFillDefaults();
                  setOpen(false);
                }}
                className="mt-3 w-full text-xs px-3 py-1.5 bg-indigo-600 text-white rounded hover:bg-indigo-700"
              >
                Fill with defaults
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ── Step card wrapper ──────────────────────────────────────────────────────

function StepCard({
  step,
  title,
  status,
  help,
  children,
}: {
  step: number;
  title: string;
  status: StepStatus;
  help?: React.ReactNode;
  children: React.ReactNode;
}) {
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (status === "idle") {
      cardRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [status]);

  const badge: Record<StepStatus, string> = {
    locked: "bg-gray-100 text-gray-400",
    idle: "bg-blue-50 text-blue-600",
    loading: "bg-yellow-50 text-yellow-600",
    success: "bg-green-50 text-green-700",
    error: "bg-red-50 text-red-700",
  };

  const label: Record<StepStatus, string> = {
    locked: "locked",
    idle: "ready",
    loading: "running…",
    success: "✓ done",
    error: "✗ error",
  };

  return (
    <div
      ref={cardRef}
      className={`bg-white border rounded-lg transition-all ${
        status === "locked" ? "opacity-40 pointer-events-none" : ""
      }`}
    >
      <div className="flex items-center gap-3 px-4 py-3 border-b">
        <span className="text-sm font-mono text-gray-400">0{step}</span>
        <span className="font-semibold text-sm flex-1">{title}</span>
        {help}
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge[status]}`}>
          {label[status]}
        </span>
      </div>
      {status !== "locked" && <div className="px-4 py-4">{children}</div>}
    </div>
  );
}

// ── Small UI helpers ───────────────────────────────────────────────────────

function Btn({
  onClick,
  loading,
  disabled,
  children,
  variant = "primary",
}: {
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  variant?: "primary" | "secondary";
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className={`px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50 ${
        variant === "primary"
          ? "bg-indigo-600 text-white hover:bg-indigo-700"
          : "border text-gray-700 hover:bg-gray-50"
      }`}
    >
      {loading ? "…" : children}
    </button>
  );
}

function Input({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
      />
    </label>
  );
}

function SuccessBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3 bg-green-50 border border-green-200 rounded px-3 py-2 text-sm text-green-800">
      {children}
    </div>
  );
}

function ErrorBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3 bg-red-50 border border-red-200 rounded px-3 py-2 text-sm text-red-800">
      {children}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function HarnessPage() {
  const [state, dispatch] = useReducer(reducer, undefined, initState);
  const currentStepRef = useRef(1);
  const [stepError, setStepError] = useState<Record<number, string>>({});

  // Register API capture hook on mount
  useEffect(() => {
    setApiCaptureHook((entry) => {
      dispatch({ type: "APPEND_LOG", step: currentStepRef.current, entry });
      dispatch({ type: "SET_ACTIVE_LOG_TAB", step: currentStepRef.current });
    });
    return () => setApiCaptureHook(null);
  }, []);

  function setStep(n: number, status: StepStatus, err?: string) {
    currentStepRef.current = n;
    dispatch({ type: "SET_STEP_STATUS", step: n, status });
    if (err) setStepError((p) => ({ ...p, [n]: err }));
    else setStepError((p) => { const c = { ...p }; delete c[n]; return c; });
  }

  // ── Step 1: Auth ───────────────────────────────────────────────────────

  const [tenantInput, setTenantInput] = useState(state.tenantId);

  async function handleSetTenant() {
    currentStepRef.current = 1;
    setStep(1, "loading");
    try {
      setDevTenantId(tenantInput);
      dispatch({ type: "SET_TENANT_ID", id: tenantInput });
      const res = await fetch("http://localhost:8000/health", {
        headers: { "X-Dev-Tenant-Id": tenantInput },
      });
      if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
      setStep(1, "success");
    } catch (e) {
      setDevTenantId(null);
      setStep(1, "error", String(e));
    }
  }

  // ── Step 2: Configure Source ──────────────────────────────────────────

  const [srcName, setSrcName] = useState("My GA4 Property");
  const [srcPropertyId, setSrcPropertyId] = useState("123456789");
  const [connWarning, setConnWarning] = useState<string | null>(null);

  async function handleAddSource() {
    currentStepRef.current = 2;
    setStep(2, "loading");
    setConnWarning(null);
    try {
      const source = await sources.create({
        connector_type: "ga4",
        display_name: srcName,
        config: { property_id: srcPropertyId },
        credentials: {},
      });
      dispatch({ type: "SET_STEP_DATA", key: "source", value: source });

      // Test connection (non-blocking)
      try {
        const { connected } = await sources.test(source.id);
        if (!connected) setConnWarning("Connection test failed — credentials may be missing. You can still proceed.");
      } catch {
        setConnWarning("Could not test connection, but source was saved.");
      }

      setStep(2, "success");
    } catch (e) {
      setStep(2, "error", String(e));
    }
  }

  // ── Step 3: Explore Schema ────────────────────────────────────────────

  const schemaPoller = usePoll<DataSource>(
    () => sources.get(state.stepData.source?.id ?? ""),
    (s) => s.schema_map !== null,
    (s) => dispatch({ type: "SET_STEP_DATA", key: "source", value: s }),
    () => setStep(3, "error", "Timed out after 60s — is the Celery worker running?")
  );

  async function handleExploreSchema() {
    currentStepRef.current = 3;
    setStep(3, "loading");
    try {
      await ingestion.exploreSchema(state.stepData.source!.id);
      schemaPoller.start();
    } catch (e) {
      setStep(3, "error", String(e));
    }
  }

  // Watch for schema_map to appear
  useEffect(() => {
    if (state.stepStatuses[3] === "loading" && state.stepData.source?.schema_map) {
      schemaPoller.stop();
      setStep(3, "success");
    }
  }, [state.stepData.source?.schema_map, state.stepStatuses[3]]);

  // ── Step 4: Ingest ────────────────────────────────────────────────────

  const today = new Date().toISOString().slice(0, 10);
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const [ingestStart, setIngestStart] = useState(thirtyDaysAgo);
  const [ingestEnd, setIngestEnd] = useState(today);

  const jobPoller = usePoll<IngestionJob>(
    () => ingestion.getJob(state.stepData.ingestionJob?.id ?? ""),
    (j) => j.status === "success" || j.status === "failed",
    (j) => dispatch({ type: "SET_STEP_DATA", key: "ingestionJob", value: j }),
    () => setStep(4, "error", "Timed out after 60s — is the Celery worker running?")
  );

  async function handleIngest() {
    currentStepRef.current = 4;
    setStep(4, "loading");
    try {
      const job = await ingestion.trigger({
        source_id: state.stepData.source!.id,
        start_date: ingestStart,
        end_date: ingestEnd,
      });
      dispatch({ type: "SET_STEP_DATA", key: "ingestionJob", value: job });
      jobPoller.start();
    } catch (e) {
      setStep(4, "error", String(e));
    }
  }

  useEffect(() => {
    const job = state.stepData.ingestionJob;
    if (state.stepStatuses[4] === "loading" && job) {
      if (job.status === "success") {
        jobPoller.stop();
        setStep(4, "success");
      } else if (job.status === "failed") {
        jobPoller.stop();
        setStep(4, "error", job.error_message ?? "Ingestion failed");
      }
    }
  }, [state.stepData.ingestionJob?.status, state.stepStatuses[4]]);

  // ── Step 5: Query Data ────────────────────────────────────────────────

  const [queryGroupBy, setQueryGroupBy] = useState("campaign");

  async function handleQuery() {
    currentStepRef.current = 5;
    setStep(5, "loading");
    try {
      const result = await queryData({
        start_date: ingestStart,
        end_date: ingestEnd,
        group_by: queryGroupBy,
        source_ids: [state.stepData.source!.id],
        limit: 10,
      });
      dispatch({ type: "SET_STEP_DATA", key: "queryResults", value: result.rows });
      setStep(5, "success");
    } catch (e) {
      setStep(5, "error", String(e));
    }
  }

  // ── Step 6: Generate Insights ─────────────────────────────────────────

  async function handleGenerateInsights() {
    currentStepRef.current = 6;
    setStep(6, "loading");
    try {
      const insight = await insights.generate({
        source_ids: [state.stepData.source!.id],
        start_date: ingestStart,
        end_date: ingestEnd,
        template_slug: "weekly_insights",
      });
      dispatch({ type: "SET_STEP_DATA", key: "insight", value: insight });
      setStep(6, "success");
    } catch (e) {
      setStep(6, "error", String(e));
    }
  }

  // ── Step 7: Publish Report ────────────────────────────────────────────

  const [reportTitle, setReportTitle] = useState(`Performance Report — ${today}`);

  async function handlePublishReport() {
    currentStepRef.current = 7;
    setStep(7, "loading");
    try {
      const report = await reports.publish({
        title: reportTitle,
        insight_ids: [state.stepData.insight!.id],
        format: "markdown",
      });
      dispatch({ type: "SET_STEP_DATA", key: "report", value: report });
      setStep(7, "success");
    } catch (e) {
      setStep(7, "error", String(e));
    }
  }

  // ── Step 8: Create Campaign Plan ──────────────────────────────────────

  const [planTitle, setPlanTitle] = useState("Q3 Growth Campaign");
  const [planObjective, setPlanObjective] = useState("Increase brand awareness and drive 20% more conversions");
  const [planBudget, setPlanBudget] = useState("10000");
  const [planChannels, setPlanChannels] = useState<string[]>(["paid_search", "paid_social"]);

  async function handleCreatePlan() {
    currentStepRef.current = 8;
    setStep(8, "loading");
    try {
      const plan = await campaigns.createPlan({
        title: planTitle,
        objective: planObjective,
        budget: planBudget ? Number(planBudget) : undefined,
        channels: planChannels,
        duration_weeks: 4,
      });
      dispatch({ type: "SET_STEP_DATA", key: "campaignPlan", value: plan });
      setStep(8, "success");
    } catch (e) {
      setStep(8, "error", String(e));
    }
  }

  const CHANNEL_OPTIONS = ["paid_search", "paid_social", "email", "organic", "display"];

  // ── Seed mock data (fast-forwards through steps 2-4) ─────────────────

  const [seeding, setSeeding] = useState(false);
  const [seedSummary, setSeedSummary] = useState<string | null>(null);

  async function handleSeedMockData() {
    if (state.stepStatuses[1] !== "success") {
      alert("Complete Step 1 (auth) first.");
      return;
    }
    currentStepRef.current = 1;
    setSeeding(true);
    try {
      const result = await dev.seed();
      // Fetch the seeded source so we can populate stepData
      currentStepRef.current = 2;
      const source = await sources.get(result.source_id);

      // Mark steps 2, 3, 4 as success with stub data
      dispatch({ type: "SET_STEP_DATA", key: "source", value: source });
      setStep(2, "success");
      setStep(3, "success");

      const stubJob: IngestionJob = {
        id: "mock-job",
        source_id: result.source_id,
        status: "success",
        date_range_start: result.date_range.start,
        date_range_end: result.date_range.end,
        rows_ingested: result.fact_rows_created,
        error_message: null,
        created_at: new Date().toISOString(),
      };
      dispatch({ type: "SET_STEP_DATA", key: "ingestionJob", value: stubJob });
      setStep(4, "success");

      // Sync the ingest date inputs so step 5/6 use the seeded range
      setIngestStart(result.date_range.start);
      setIngestEnd(result.date_range.end);

      setSeedSummary(
        `${result.fact_rows_created} fact rows across ${result.campaigns_created} campaigns and ${result.channels_created} channels — jump to Step 5.`
      );
    } catch (e) {
      alert(`Seed failed: ${e}`);
    } finally {
      setSeeding(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Dev banner */}
      <div className="bg-amber-400 text-amber-900 text-center text-xs font-semibold py-2 px-4 -mx-6 -mt-8 mb-6">
        ⚠ Developer Test Harness — Not for production use
      </div>

      <div className="flex gap-6 items-start">
        {/* Left: wizard steps */}
        <div className="flex-1 min-w-0 space-y-3">
          <h1 className="text-xl font-bold mb-4">Pipeline Test Harness</h1>

          {/* Seed mock data banner — only useful if user has no real GA4 creds */}
          {state.stepStatuses[1] === "success" && state.stepStatuses[5] !== "success" && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 flex items-start gap-3">
              <div className="flex-1">
                <div className="text-sm font-semibold text-indigo-900 mb-1">
                  No GA4 credentials? Seed mock data instead.
                </div>
                <p className="text-xs text-indigo-700">
                  Steps 2–4 require real GA4 access. Click below to insert a stub source + 150 fake performance rows,
                  then jump straight to Step 5.
                </p>
                {seedSummary && (
                  <div className="text-xs text-green-700 mt-2 bg-green-50 border border-green-200 rounded px-2 py-1">
                    ✓ {seedSummary}
                  </div>
                )}
              </div>
              <Btn onClick={handleSeedMockData} loading={seeding}>
                Seed Mock Data
              </Btn>
            </div>
          )}

          {/* Step 1: Auth */}
          <StepCard
            step={1}
            title="Setup & Auth"
            status={state.stepStatuses[1]}
            help={
              <HelpPopover
                fields={[
                  {
                    field: "Tenant UUID",
                    description: "Must match DEV_TENANT_ID in the API's .env file. Bypasses JWT auth.",
                    example: "d3bc44e1-d17e-4518-88c9-bd116aba6a70",
                  },
                ]}
              />
            }
          >
            <div className="space-y-3">
              <Input
                label="Tenant UUID (from your dev database)"
                value={tenantInput}
                onChange={setTenantInput}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              />
              <p className="text-xs text-gray-400">
                Set <code className="bg-gray-100 px-1 rounded">DEV_TENANT_ID=&lt;this UUID&gt;</code> in your API&apos;s .env
              </p>
              <Btn onClick={handleSetTenant} loading={state.stepStatuses[1] === "loading"} disabled={!tenantInput}>
                Connect
              </Btn>
              {state.stepStatuses[1] === "success" && (
                <SuccessBox>Connected as tenant <code className="font-mono">{state.tenantId.slice(0, 8)}…</code></SuccessBox>
              )}
              {stepError[1] && <ErrorBox>{stepError[1]}</ErrorBox>}
            </div>
          </StepCard>

          {/* Step 2: Configure Source */}
          <StepCard
            step={2}
            title="Configure Data Source"
            status={state.stepStatuses[2]}
            help={
              <HelpPopover
                fields={[
                  { field: "connector_type", description: "Source platform — only 'ga4' is implemented day-one.", example: "ga4" },
                  { field: "display_name", description: "Human-readable label for this source.", example: "Acme Client GA4" },
                  { field: "property_id", description: "Numeric GA4 Property ID from the GA Admin UI. Real ID needed for live data.", example: "123456789" },
                ]}
                onFillDefaults={() => {
                  setSrcName("Test GA4 Source");
                  setSrcPropertyId("123456789");
                }}
              />
            }
          >
            <div className="space-y-3">
              <Input label="Display name" value={srcName} onChange={setSrcName} />
              <Input label="GA4 Property ID" value={srcPropertyId} onChange={setSrcPropertyId} placeholder="123456789" />
              <Btn onClick={handleAddSource} loading={state.stepStatuses[2] === "loading"}>
                Add Source
              </Btn>
              {connWarning && (
                <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-xs rounded px-3 py-2">
                  ⚠ {connWarning}
                </div>
              )}
              {state.stepStatuses[2] === "success" && (
                <SuccessBox>
                  Source created: <code className="font-mono text-xs">{state.stepData.source?.id}</code>
                </SuccessBox>
              )}
              {stepError[2] && <ErrorBox>{stepError[2]}</ErrorBox>}
            </div>
          </StepCard>

          {/* Step 3: Explore Schema */}
          <StepCard
            step={3}
            title="Explore Schema"
            status={state.stepStatuses[3]}
            help={
              <HelpPopover
                fields={[
                  {
                    field: "(no inputs)",
                    description: "Triggers a Celery task. Calls GA4 list_schema_fields(), then Claude maps each field to the canonical schema (date_key, campaign_name, impressions, spend, etc.). Will fail without real GA4 credentials.",
                    example: "Click 'Explore Schema' — polls every 2s.",
                  },
                ]}
              />
            }
          >
            <div className="space-y-3">
              <p className="text-sm text-gray-600">
                Claude will discover all available fields from GA4 and map them to the canonical marketing schema.
                This queues a Celery task and polls until complete.
              </p>
              <Btn onClick={handleExploreSchema} loading={state.stepStatuses[3] === "loading"}>
                {state.stepStatuses[3] === "loading" ? "Exploring (polling every 2s…)" : "Explore Schema"}
              </Btn>
              {state.stepStatuses[3] === "success" && state.stepData.source?.schema_map && (
                <SuccessBox>
                  {state.stepData.source.schema_map.length} field mappings discovered.
                  <div className="mt-2 max-h-24 overflow-y-auto">
                    {state.stepData.source.schema_map.slice(0, 5).map((m, i) => (
                      <div key={i} className="text-xs font-mono">{m.raw_field} → {m.canonical_field}</div>
                    ))}
                    {state.stepData.source.schema_map.length > 5 && (
                      <div className="text-xs text-gray-500">…and {state.stepData.source.schema_map.length - 5} more</div>
                    )}
                  </div>
                </SuccessBox>
              )}
              {stepError[3] && <ErrorBox>{stepError[3]}</ErrorBox>}
            </div>
          </StepCard>

          {/* Step 4: Ingest */}
          <StepCard
            step={4}
            title="Trigger Ingestion"
            status={state.stepStatuses[4]}
            help={
              <HelpPopover
                fields={[
                  { field: "start_date", description: "Beginning of date range to ingest (YYYY-MM-DD). Default: 30 days ago.", example: thirtyDaysAgo },
                  { field: "end_date", description: "End of date range, inclusive. Default: today.", example: today },
                ]}
                onFillDefaults={() => {
                  setIngestStart(thirtyDaysAgo);
                  setIngestEnd(today);
                }}
              />
            }
          >
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Input label="Start date" type="date" value={ingestStart} onChange={setIngestStart} />
                <Input label="End date" type="date" value={ingestEnd} onChange={setIngestEnd} />
              </div>
              <Btn onClick={handleIngest} loading={state.stepStatuses[4] === "loading"}>
                {state.stepStatuses[4] === "loading" ? "Ingesting (polling…)" : "Ingest Data"}
              </Btn>
              {state.stepStatuses[4] === "loading" && state.stepData.ingestionJob && (
                <div className="text-xs text-gray-500">
                  Job {state.stepData.ingestionJob.id.slice(0, 8)}… — {state.stepData.ingestionJob.status}
                  {state.stepData.ingestionJob.rows_ingested != null && ` — ${state.stepData.ingestionJob.rows_ingested} rows`}
                </div>
              )}
              {state.stepStatuses[4] === "success" && (
                <SuccessBox>
                  {state.stepData.ingestionJob?.rows_ingested ?? 0} rows ingested into fact_performance.
                </SuccessBox>
              )}
              {stepError[4] && <ErrorBox>{stepError[4]}</ErrorBox>}
            </div>
          </StepCard>

          {/* Step 5: Query Data */}
          <StepCard
            step={5}
            title="Query Normalized Data"
            status={state.stepStatuses[5]}
            help={
              <HelpPopover
                fields={[
                  { field: "group_by", description: "Aggregate by 'campaign', 'channel', or 'date'. Determines table grouping.", example: "campaign" },
                ]}
                onFillDefaults={() => setQueryGroupBy("campaign")}
              />
            }
          >
            <div className="space-y-3">
              <div>
                <span className="text-xs font-medium text-gray-500 uppercase">Group by</span>
                <div className="flex gap-2 mt-1">
                  {["campaign", "channel", "date"].map((g) => (
                    <button
                      key={g}
                      onClick={() => setQueryGroupBy(g)}
                      className={`px-3 py-1 rounded text-sm border ${
                        queryGroupBy === g ? "bg-indigo-600 text-white border-indigo-600" : "border-gray-200 hover:bg-gray-50"
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
              <Btn onClick={handleQuery} loading={state.stepStatuses[5] === "loading"}>
                Run Query
              </Btn>
              {state.stepStatuses[5] === "success" && state.stepData.queryResults && (
                <SuccessBox>
                  {state.stepData.queryResults.length === 0 ? (
                    <span>No rows returned. Try ingesting real data first.</span>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="text-xs w-full">
                        <thead>
                          <tr>
                            {Object.keys(state.stepData.queryResults[0]).map((k) => (
                              <th key={k} className="text-left pr-4 font-mono">{k}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {state.stepData.queryResults.slice(0, 5).map((row, i) => (
                            <tr key={i}>
                              {Object.values(row).map((v, j) => (
                                <td key={j} className="pr-4 font-mono">{String(v)}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </SuccessBox>
              )}
              {stepError[5] && <ErrorBox>{stepError[5]}</ErrorBox>}
            </div>
          </StepCard>

          {/* Step 6: Generate Insights */}
          <StepCard
            step={6}
            title="Generate AI Insights"
            status={state.stepStatuses[6]}
            help={
              <HelpPopover
                fields={[
                  {
                    field: "(no inputs)",
                    description: "Uses the 'weekly_insights' prompt template. Queries fact_performance for the ingest date range, sends aggregates + top campaigns to Claude, parses structured JSON insight. Cached by data hash.",
                    example: "Click 'Generate Insights' — single Claude call (~5-10s).",
                  },
                ]}
              />
            }
          >
            <div className="space-y-3">
              <p className="text-sm text-gray-600">
                Uses <code className="bg-gray-100 px-1 rounded text-xs">weekly_insights</code> template.
                Results are cached by data hash — identical data won&apos;t re-call the LLM.
              </p>
              <Btn onClick={handleGenerateInsights} loading={state.stepStatuses[6] === "loading"}>
                Generate Insights
              </Btn>
              {state.stepStatuses[6] === "success" && state.stepData.insight && (
                <SuccessBox>
                  <div className="font-medium mb-1">Insight generated</div>
                  {typeof state.stepData.insight.content.summary === "string" && (
                    <p className="text-xs">{state.stepData.insight.content.summary}</p>
                  )}
                  <div className="text-xs text-gray-500 mt-1">Model: {state.stepData.insight.model_used}</div>
                </SuccessBox>
              )}
              {stepError[6] && <ErrorBox>{stepError[6]}</ErrorBox>}
            </div>
          </StepCard>

          {/* Step 7: Publish Report */}
          <StepCard
            step={7}
            title="Publish Report"
            status={state.stepStatuses[7]}
            help={
              <HelpPopover
                fields={[
                  { field: "title", description: "Report title shown in the client UI.", example: `Performance Report — ${today}` },
                ]}
                onFillDefaults={() => setReportTitle(`Performance Report — ${today}`)}
              />
            }
          >
            <div className="space-y-3">
              <Input label="Report title" value={reportTitle} onChange={setReportTitle} />
              <Btn onClick={handlePublishReport} loading={state.stepStatuses[7] === "loading"}>
                Publish Report
              </Btn>
              {state.stepStatuses[7] === "success" && state.stepData.report && (
                <SuccessBox>
                  Report published: <code className="font-mono text-xs">{state.stepData.report.id}</code>
                  <div className="text-xs text-gray-500 mt-1">
                    Published at: {state.stepData.report.published_at}
                  </div>
                </SuccessBox>
              )}
              {stepError[7] && <ErrorBox>{stepError[7]}</ErrorBox>}
            </div>
          </StepCard>

          {/* Step 8: Campaign Plan */}
          <StepCard
            step={8}
            title="Create Campaign Plan"
            status={state.stepStatuses[8]}
            help={
              <HelpPopover
                fields={[
                  { field: "title", description: "Plan title used in the UI and stored in DB.", example: "Q3 Growth Campaign" },
                  { field: "objective", description: "Free-text business goal. Claude uses this verbatim in the prompt.", example: "Increase brand awareness, drive 20% more conversions" },
                  { field: "budget", description: "Total spend across all channels. Used to allocate per-phase budget percentages.", example: "10000" },
                  { field: "channels", description: "Marketing channels the plan should use. Multi-select.", example: "paid_search, paid_social" },
                ]}
                onFillDefaults={() => {
                  setPlanTitle("Q3 Growth Campaign");
                  setPlanObjective("Increase brand awareness and drive 20% more conversions");
                  setPlanBudget("10000");
                  setPlanChannels(["paid_search", "paid_social"]);
                }}
              />
            }
          >
            <div className="space-y-3">
              <Input label="Campaign title" value={planTitle} onChange={setPlanTitle} />
              <Input label="Objective" value={planObjective} onChange={setPlanObjective} />
              <Input label="Budget (optional)" value={planBudget} onChange={setPlanBudget} type="number" />
              <div>
                <span className="text-xs font-medium text-gray-500 uppercase">Channels</span>
                <div className="flex flex-wrap gap-2 mt-1">
                  {CHANNEL_OPTIONS.map((ch) => (
                    <label key={ch} className="flex items-center gap-1.5 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={planChannels.includes(ch)}
                        onChange={(e) =>
                          setPlanChannels(
                            e.target.checked ? [...planChannels, ch] : planChannels.filter((c) => c !== ch)
                          )
                        }
                      />
                      {ch}
                    </label>
                  ))}
                </div>
              </div>
              <Btn onClick={handleCreatePlan} loading={state.stepStatuses[8] === "loading"} disabled={!planTitle || !planObjective}>
                Generate Plan
              </Btn>
              {state.stepStatuses[8] === "success" && state.stepData.campaignPlan && (
                <SuccessBox>
                  <div className="font-medium">{state.stepData.campaignPlan.title}</div>
                  {typeof state.stepData.campaignPlan.plan_content.executive_summary === "string" && (
                    <p className="text-xs mt-1">{state.stepData.campaignPlan.plan_content.executive_summary}</p>
                  )}
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {state.stepData.campaignPlan.channels.map((ch) => (
                      <span key={ch} className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">{ch}</span>
                    ))}
                  </div>
                </SuccessBox>
              )}
              {stepError[8] && <ErrorBox>{stepError[8]}</ErrorBox>}
            </div>
          </StepCard>

          {/* All done */}
          {state.stepStatuses[8] === "success" && (
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg p-6 text-white text-center">
              <div className="text-2xl font-bold mb-1">🎉 Full pipeline complete!</div>
              <p className="text-indigo-200 text-sm">All 8 steps passed. The platform is working end-to-end.</p>
            </div>
          )}
        </div>

        {/* Right: JSON inspector */}
        <div className="w-80 shrink-0 sticky top-4">
          <JsonInspector
            logs={state.logs}
            activeTab={state.activeLogTab}
            onTabChange={(step) => dispatch({ type: "SET_ACTIVE_LOG_TAB", step })}
          />
        </div>
      </div>
    </div>
  );
}
