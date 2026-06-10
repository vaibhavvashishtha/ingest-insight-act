-- ============================================================
-- ingest-insight-act: Initial Schema
-- ============================================================

-- Enable pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- TENANTS
-- ============================================================
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- DATA SOURCES
-- ============================================================
CREATE TABLE IF NOT EXISTS data_sources (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    connector_type   TEXT NOT NULL,  -- 'ga4' | 'meta_ads' | 'google_ads' | 'hubspot'
    display_name     TEXT NOT NULL,
    credentials      JSONB NOT NULL DEFAULT '{}',  -- encrypted at application layer
    config           JSONB NOT NULL DEFAULT '{}',
    schema_map       JSONB,          -- set after explore_schema: [{raw_field, canonical_field, transform}]
    last_ingested_at TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;
CREATE POLICY data_sources_tenant_isolation ON data_sources
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- ============================================================
-- DIMENSIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_date (
    date_key    DATE PRIMARY KEY,
    year        SMALLINT NOT NULL,
    quarter     SMALLINT NOT NULL,
    month       SMALLINT NOT NULL,
    week        SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,
    is_weekend  BOOLEAN NOT NULL DEFAULT false
);

-- Pre-populate dim_date for 2020–2030
INSERT INTO dim_date (date_key, year, quarter, month, week, day_of_week, is_weekend)
SELECT
    d::DATE,
    EXTRACT(YEAR FROM d)::SMALLINT,
    EXTRACT(QUARTER FROM d)::SMALLINT,
    EXTRACT(MONTH FROM d)::SMALLINT,
    EXTRACT(WEEK FROM d)::SMALLINT,
    EXTRACT(DOW FROM d)::SMALLINT,
    EXTRACT(DOW FROM d) IN (0, 6)
FROM generate_series('2020-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) d
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS dim_campaign (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id   UUID REFERENCES data_sources(id) ON DELETE SET NULL,
    external_id TEXT NOT NULL,
    name        TEXT NOT NULL,
    channel     TEXT,   -- 'paid_search' | 'paid_social' | 'email' | 'organic' | 'display'
    status      TEXT,
    objective   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, source_id, external_id)
);
ALTER TABLE dim_campaign ENABLE ROW LEVEL SECURITY;
CREATE POLICY dim_campaign_tenant_isolation ON dim_campaign
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

CREATE TABLE IF NOT EXISTS dim_channel (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    category    TEXT,
    UNIQUE (tenant_id, name)
);
ALTER TABLE dim_channel ENABLE ROW LEVEL SECURITY;
CREATE POLICY dim_channel_tenant_isolation ON dim_channel
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

CREATE TABLE IF NOT EXISTS dim_audience (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    segment_type    TEXT,  -- 'demographic' | 'interest' | 'remarketing' | 'lookalike'
    attributes      JSONB NOT NULL DEFAULT '{}',
    UNIQUE (tenant_id, name)
);
ALTER TABLE dim_audience ENABLE ROW LEVEL SECURITY;
CREATE POLICY dim_audience_tenant_isolation ON dim_audience
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- ============================================================
-- FACTS
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_performance (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    date_key     DATE NOT NULL REFERENCES dim_date(date_key),
    campaign_id  UUID REFERENCES dim_campaign(id) ON DELETE SET NULL,
    channel_id   UUID REFERENCES dim_channel(id) ON DELETE SET NULL,
    audience_id  UUID REFERENCES dim_audience(id) ON DELETE SET NULL,
    source_id    UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    -- core metrics
    impressions  BIGINT NOT NULL DEFAULT 0,
    clicks       BIGINT NOT NULL DEFAULT 0,
    spend        NUMERIC(18, 4) NOT NULL DEFAULT 0,
    conversions  NUMERIC(18, 4) NOT NULL DEFAULT 0,
    revenue      NUMERIC(18, 4) NOT NULL DEFAULT 0,
    -- derived (stored for query performance)
    ctr          NUMERIC(10, 6) GENERATED ALWAYS AS (
                     CASE WHEN impressions > 0 THEN clicks::NUMERIC / impressions ELSE 0 END
                 ) STORED,
    cpc          NUMERIC(18, 4) GENERATED ALWAYS AS (
                     CASE WHEN clicks > 0 THEN spend / clicks ELSE 0 END
                 ) STORED,
    roas         NUMERIC(18, 4) GENERATED ALWAYS AS (
                     CASE WHEN spend > 0 THEN revenue / spend ELSE 0 END
                 ) STORED,
    raw_data     JSONB,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, date_key, campaign_id, source_id)
);
ALTER TABLE fact_performance ENABLE ROW LEVEL SECURITY;
CREATE POLICY fact_performance_tenant_isolation ON fact_performance
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
CREATE INDEX idx_fact_perf_tenant_date ON fact_performance (tenant_id, date_key);
CREATE INDEX idx_fact_perf_campaign    ON fact_performance (campaign_id);
CREATE INDEX idx_fact_perf_source      ON fact_performance (source_id);

CREATE TABLE IF NOT EXISTS fact_attribution (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    date_key               DATE NOT NULL REFERENCES dim_date(date_key),
    campaign_id            UUID REFERENCES dim_campaign(id) ON DELETE SET NULL,
    channel_id             UUID REFERENCES dim_channel(id) ON DELETE SET NULL,
    source_id              UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    model                  TEXT NOT NULL,  -- 'last_click' | 'data_driven' | 'linear' | 'first_click'
    attributed_conversions NUMERIC(18, 4) NOT NULL DEFAULT 0,
    attributed_revenue     NUMERIC(18, 4) NOT NULL DEFAULT 0,
    ingested_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE fact_attribution ENABLE ROW LEVEL SECURITY;
CREATE POLICY fact_attribution_tenant_isolation ON fact_attribution
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- ============================================================
-- PROMPT TEMPLATES
-- ============================================================
CREATE TABLE IF NOT EXISTS prompt_templates (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID REFERENCES tenants(id) ON DELETE CASCADE,  -- NULL = platform default
    slug                 TEXT NOT NULL,  -- 'weekly_insights' | 'campaign_plan' | 'ad_copy' | 'email_copy'
    model_class          TEXT NOT NULL DEFAULT 'ClaudeContentModel',
    system_prompt        TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,  -- Jinja2 template
    version              INT NOT NULL DEFAULT 1,
    is_active            BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug, version)
);
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY prompt_templates_tenant_or_platform ON prompt_templates
    USING (tenant_id IS NULL OR tenant_id = current_setting('app.tenant_id', true)::UUID);

-- ============================================================
-- INSIGHTS
-- ============================================================
CREATE TABLE IF NOT EXISTS insights (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_ids         UUID[] NOT NULL,
    date_range_start   DATE,
    date_range_end     DATE,
    prompt_template_id UUID REFERENCES prompt_templates(id) ON DELETE SET NULL,
    input_data_hash    TEXT,  -- SHA-256 of serialized query result; skip regen if unchanged
    content            JSONB NOT NULL,
    raw_llm_response   TEXT,
    model_used         TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;
CREATE POLICY insights_tenant_isolation ON insights
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
CREATE INDEX idx_insights_tenant_hash ON insights (tenant_id, input_data_hash);

-- ============================================================
-- REPORTS
-- ============================================================
CREATE TABLE IF NOT EXISTS reports (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    insight_ids   UUID[] NOT NULL DEFAULT '{}',
    content       JSONB NOT NULL,
    format        TEXT NOT NULL DEFAULT 'markdown',  -- 'markdown' | 'html' | 'pdf'
    published_at  TIMESTAMPTZ,
    published_url TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY reports_tenant_isolation ON reports
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- ============================================================
-- CAMPAIGN PLANS
-- ============================================================
CREATE TABLE IF NOT EXISTS campaign_plans (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title              TEXT NOT NULL,
    objective          TEXT,
    budget             NUMERIC(18, 2),
    channels           TEXT[] NOT NULL DEFAULT '{}',
    prompt_template_id UUID REFERENCES prompt_templates(id) ON DELETE SET NULL,
    plan_content       JSONB NOT NULL,  -- {phases, tactics, copy_variants, schedule, kpis}
    status             TEXT NOT NULL DEFAULT 'draft',  -- 'draft' | 'approved' | 'active' | 'archived'
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE campaign_plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY campaign_plans_tenant_isolation ON campaign_plans
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- ============================================================
-- INGESTION JOBS
-- ============================================================
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_id        UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    celery_task_id   TEXT,
    status           TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'running' | 'success' | 'failed'
    date_range_start DATE,
    date_range_end   DATE,
    rows_ingested    INT,
    error_message    TEXT,
    started_at       TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE ingestion_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY ingestion_jobs_tenant_isolation ON ingestion_jobs
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);
CREATE INDEX idx_ingestion_jobs_source ON ingestion_jobs (source_id, status);

-- ============================================================
-- SEED: Platform-default prompt templates
-- ============================================================
INSERT INTO prompt_templates (tenant_id, slug, model_class, system_prompt, user_prompt_template, version)
VALUES
(
    NULL,
    'weekly_insights',
    'ClaudeContentModel',
    'You are an expert marketing analyst. Analyze the provided performance data and return a structured JSON insight report. Be specific, data-driven, and actionable. Focus on trends, anomalies, and opportunities.',
    'Analyze the following marketing performance data for the period {{ date_range_start }} to {{ date_range_end }}:

METRICS SUMMARY:
{{ metrics_json }}

TOP CAMPAIGNS:
{{ top_campaigns_json }}

Return a JSON object with this exact structure:
{
  "summary": "2-3 sentence executive summary",
  "highlights": [{"metric": "...", "value": "...", "change": "...", "interpretation": "..."}],
  "anomalies": [{"description": "...", "impact": "low|medium|high", "recommendation": "..."}],
  "opportunities": [{"title": "...", "rationale": "...", "expected_impact": "..."}],
  "next_actions": ["action 1", "action 2", "action 3"]
}',
    1
),
(
    NULL,
    'campaign_plan',
    'ClaudeContentModel',
    'You are a senior performance marketing strategist. Create detailed, actionable campaign plans based on historical performance data and business objectives. Return structured JSON only.',
    'Create a comprehensive campaign plan with the following parameters:

OBJECTIVE: {{ objective }}
BUDGET: {{ budget }}
CHANNELS: {{ channels }}
DURATION: {{ duration_weeks }} weeks

HISTORICAL PERFORMANCE CONTEXT:
{{ historical_data_json }}

Return a JSON object with this exact structure:
{
  "title": "Campaign title",
  "executive_summary": "...",
  "phases": [
    {
      "name": "Phase name",
      "duration_weeks": 2,
      "budget_allocation_pct": 30,
      "tactics": [{"channel": "...", "format": "...", "budget": 0, "kpi": "..."}]
    }
  ],
  "audience_targeting": [{"segment": "...", "rationale": "..."}],
  "kpis": [{"metric": "...", "target": "...", "measurement": "..."}],
  "copy_brief": {"tone": "...", "key_messages": [], "cta": "..."},
  "schedule": {"start_date": null, "milestones": []}
}',
    1
),
(
    NULL,
    'ad_copy',
    'ClaudeContentModel',
    'You are a creative copywriter specializing in digital advertising. Generate compelling, conversion-focused ad copy variants. Return structured JSON only.',
    'Generate ad copy variants for the following brief:

PRODUCT/SERVICE: {{ product }}
TARGET AUDIENCE: {{ audience }}
CHANNEL: {{ channel }}
TONE: {{ tone }}
KEY MESSAGE: {{ key_message }}
CTA: {{ cta }}

Return a JSON object:
{
  "variants": [
    {
      "headline": "...",
      "body": "...",
      "cta": "...",
      "character_count": {"headline": 0, "body": 0}
    }
  ],
  "usage_notes": "..."
}',
    1
),
(
    NULL,
    'email_copy',
    'ClaudeContentModel',
    'You are an expert email marketer. Write high-converting email campaigns with strong subject lines and compelling body copy. Return structured JSON only.',
    'Write an email campaign for the following brief:

GOAL: {{ goal }}
AUDIENCE SEGMENT: {{ audience }}
PRODUCT/SERVICE: {{ product }}
TONE: {{ tone }}
KEY OFFER: {{ offer }}

Return a JSON object:
{
  "subject_lines": ["option 1", "option 2", "option 3"],
  "preview_text": "...",
  "body": {
    "opening": "...",
    "main_content": "...",
    "cta_button_text": "...",
    "closing": "..."
  },
  "personalization_tokens": ["{{first_name}}", "..."]
}',
    1
)
ON CONFLICT DO NOTHING;
