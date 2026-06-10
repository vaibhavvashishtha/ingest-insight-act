const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ── Dev harness state ──────────────────────────────────────────────────────

let _devTenantId: string | null =
  typeof window !== "undefined" ? localStorage.getItem("harness_tenant_id") : null;

let _captureHook: ((entry: ApiLogEntry) => void) | null = null;

export function setDevTenantId(id: string | null) {
  _devTenantId = id;
  if (typeof window !== "undefined") {
    if (id) localStorage.setItem("harness_tenant_id", id);
    else localStorage.removeItem("harness_tenant_id");
  }
}

export function setApiCaptureHook(fn: ((entry: ApiLogEntry) => void) | null) {
  _captureHook = fn;
}

export interface ApiLogEntry {
  method: string;
  url: string;
  requestBody: unknown;
  responseBody: unknown;
  status: number;
  latencyMs: number;
}

// ── Core fetch ────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const t0 = Date.now();
  const method = init?.method ?? "GET";
  const url = `${API_BASE}${path}`;

  const token = typeof window !== "undefined" ? localStorage.getItem("sb_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };

  if (_devTenantId) {
    // Dev mode: bypass JWT with direct tenant header
    headers["X-Dev-Tenant-Id"] = _devTenantId;
  } else if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...init, headers });

  let responseBody: unknown;
  try {
    responseBody = await res.json();
  } catch {
    responseBody = null;
  }

  const entry: ApiLogEntry = {
    method,
    url,
    requestBody: init?.body ? JSON.parse(init.body as string) : undefined,
    responseBody,
    status: res.status,
    latencyMs: Date.now() - t0,
  };
  _captureHook?.(entry);

  if (!res.ok) {
    const detail = typeof responseBody === "object" && responseBody !== null
      ? JSON.stringify(responseBody)
      : String(responseBody);
    throw new Error(`API ${res.status}: ${detail}`);
  }

  return responseBody as T;
}

// ── Sources ────────────────────────────────────────────────────────────────

export interface DataSource {
  id: string;
  tenant_id: string;
  connector_type: string;
  display_name: string;
  config: Record<string, unknown>;
  schema_map: Record<string, string>[] | null;
  last_ingested_at: string | null;
  created_at: string;
}

export const sources = {
  list: () => apiFetch<DataSource[]>("/sources/"),
  get: (id: string) => apiFetch<DataSource>(`/sources/${id}`),
  create: (body: { connector_type: string; display_name: string; config: Record<string, unknown>; credentials?: Record<string, unknown> }) =>
    apiFetch<DataSource>("/sources/", { method: "POST", body: JSON.stringify(body) }),
  test: (id: string) => apiFetch<{ connected: boolean }>(`/sources/${id}/test`, { method: "POST" }),
};

// ── Ingestion ───────────────────────────────────────────────────────────────

export interface IngestionJob {
  id: string;
  source_id: string;
  status: "pending" | "running" | "success" | "failed";
  date_range_start: string | null;
  date_range_end: string | null;
  rows_ingested: number | null;
  error_message: string | null;
  created_at: string;
}

export const ingestion = {
  trigger: (body: { source_id: string; start_date: string; end_date: string }) =>
    apiFetch<IngestionJob>("/ingestion/trigger", { method: "POST", body: JSON.stringify(body) }),
  exploreSchema: (source_id: string) =>
    apiFetch<{ task_id: string; source_id: string; status: string }>("/ingestion/explore", {
      method: "POST",
      body: JSON.stringify({ source_id }),
    }),
  getJob: (id: string) => apiFetch<IngestionJob>(`/ingestion/jobs/${id}`),
  listJobs: (source_id?: string) =>
    apiFetch<IngestionJob[]>(`/ingestion/jobs${source_id ? `?source_id=${source_id}` : ""}`),
};

// ── Insights ───────────────────────────────────────────────────────────────

export interface Insight {
  id: string;
  source_ids: string[];
  date_range_start: string;
  date_range_end: string;
  content: Record<string, unknown>;
  model_used: string;
  created_at: string;
}

export const insights = {
  generate: (body: { source_ids: string[]; start_date: string; end_date: string; template_slug?: string }) =>
    apiFetch<Insight>("/insights/generate", { method: "POST", body: JSON.stringify(body) }),
  list: () => apiFetch<Insight[]>("/insights/"),
  get: (id: string) => apiFetch<Insight>(`/insights/${id}`),
};

// ── Query ───────────────────────────────────────────────────────────────────

export interface QueryResult {
  rows: Record<string, unknown>[];
  count: number;
  group_by: string | null;
}

export const queryData = (params: {
  start_date: string;
  end_date: string;
  metrics?: string[];
  group_by?: string;
  source_ids?: string[];
  limit?: number;
}) => {
  const qs = new URLSearchParams();
  qs.set("start_date", params.start_date);
  qs.set("end_date", params.end_date);
  if (params.group_by) qs.set("group_by", params.group_by);
  if (params.limit) qs.set("limit", String(params.limit));
  params.metrics?.forEach((m) => qs.append("metrics", m));
  params.source_ids?.forEach((s) => qs.append("source_ids", s));
  return apiFetch<QueryResult>(`/query?${qs}`);
};

// ── Reports ────────────────────────────────────────────────────────────────

export interface Report {
  id: string;
  title: string;
  insight_ids: string[];
  content: Record<string, unknown>;
  format: string;
  published_at: string | null;
  created_at: string;
}

export const reports = {
  publish: (body: { title: string; insight_ids: string[]; format?: string }) =>
    apiFetch<Report>("/reports/", { method: "POST", body: JSON.stringify(body) }),
  list: () => apiFetch<Report[]>("/reports/"),
  get: (id: string) => apiFetch<Report>(`/reports/${id}`),
};

// ── Dev seed ───────────────────────────────────────────────────────────────

export interface SeedResult {
  source_id: string;
  schema_map_fields: number;
  campaigns_created: number;
  channels_created: number;
  fact_rows_created: number;
  date_range: { start: string; end: string };
  message: string;
}

export const dev = {
  seed: () => apiFetch<SeedResult>("/dev/seed", { method: "POST" }),
};

// ── Campaigns ──────────────────────────────────────────────────────────────

export interface CampaignPlan {
  id: string;
  title: string;
  objective: string | null;
  budget: number | null;
  channels: string[];
  plan_content: Record<string, unknown>;
  status: string;
  created_at: string;
}

export const campaigns = {
  createPlan: (body: { title: string; objective: string; channels?: string[]; budget?: number; duration_weeks?: number }) =>
    apiFetch<CampaignPlan>("/campaigns/plans", { method: "POST", body: JSON.stringify(body) }),
  listPlans: () => apiFetch<CampaignPlan[]>("/campaigns/plans"),
  getPlan: (id: string) => apiFetch<CampaignPlan>(`/campaigns/plans/${id}`),
  generateContent: (body: { template_slug: string; context: Record<string, unknown> }) =>
    apiFetch<{ content: Record<string, unknown>; model_used: string }>("/campaigns/content/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
