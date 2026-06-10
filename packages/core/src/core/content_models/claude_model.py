import json

import anthropic

from core.config import settings
from core.content_models.base import BaseContentModel, ContentRequest, ContentResponse
from core.registry import ContentModelRegistry

_MODEL = "claude-sonnet-4-6"


def _mock_response(user_prompt: str) -> str:
    """Return canned JSON based on which template called us (detected via prompt fingerprint)."""
    p = user_prompt
    if '"summary"' in p and '"highlights"' in p and '"next_actions"' in p:
        # weekly_insights template
        return json.dumps({
            "summary": "Performance held steady week-over-week with paid_social leading on ROAS. Email campaign 'Newsletter Promo' is over-indexing on conversions while paid_search spend is trending up without proportional revenue gain.",
            "highlights": [
                {"metric": "Total spend", "value": "$295k", "change": "+8% WoW", "interpretation": "Increase driven by paid_search bid adjustments"},
                {"metric": "Blended ROAS", "value": "4.2x", "change": "-0.3 WoW", "interpretation": "Margin compression in paid_search offsetting paid_social wins"},
                {"metric": "Conversion rate", "value": "6.4%", "change": "+0.5 WoW", "interpretation": "Newsletter audience continues to outperform"}
            ],
            "anomalies": [
                {"description": "Retargeting CTR dropped 22% on Jun 6 — likely creative fatigue", "impact": "medium", "recommendation": "Rotate to fresh creative within 48h"},
                {"description": "Brand Awareness Q2 spend pacing 15% under plan", "impact": "low", "recommendation": "Reallocate underspend to top-performing ad sets"}
            ],
            "opportunities": [
                {"title": "Scale Newsletter Promo budget by 40%", "rationale": "ROAS of 4.6x sustained over 30 days with headroom on frequency cap", "expected_impact": "+$95k revenue at current efficiency"},
                {"title": "Pause bottom 20% of paid_search keywords", "rationale": "These keywords drive 18% of spend but only 4% of revenue", "expected_impact": "+0.4 blended ROAS"}
            ],
            "next_actions": [
                "Refresh Retargeting creative bank (3 new variants)",
                "Increase Newsletter Promo daily budget from $850 → $1200",
                "Audit paid_search keyword list and pause low-ROAS terms",
                "A/B test Brand Awareness Q2 landing page CTA copy"
            ]
        }, indent=2)

    if '"executive_summary"' in p and '"phases"' in p and '"audience_targeting"' in p:
        # campaign_plan template
        return json.dumps({
            "title": "Q3 Growth Campaign",
            "executive_summary": "A 4-week, $10k campaign targeting brand-aware purchase-intent audiences across paid_search and paid_social. Phased ramp moves budget from prospecting (weeks 1-2) to retargeting + conversion (weeks 3-4) to maximize ROAS at scale.",
            "phases": [
                {
                    "name": "Prospecting & Awareness",
                    "duration_weeks": 2,
                    "budget_allocation_pct": 40,
                    "tactics": [
                        {"channel": "paid_social", "format": "video ads (15s)", "budget": 2500, "kpi": "video_completion_rate >= 30%"},
                        {"channel": "paid_search", "format": "broad match brand terms", "budget": 1500, "kpi": "CTR >= 4%"}
                    ]
                },
                {
                    "name": "Consideration & Engagement",
                    "duration_weeks": 1,
                    "budget_allocation_pct": 25,
                    "tactics": [
                        {"channel": "paid_social", "format": "carousel ads", "budget": 1500, "kpi": "engagement_rate >= 6%"},
                        {"channel": "paid_search", "format": "exact match high-intent", "budget": 1000, "kpi": "conversion_rate >= 5%"}
                    ]
                },
                {
                    "name": "Conversion & Retargeting",
                    "duration_weeks": 1,
                    "budget_allocation_pct": 35,
                    "tactics": [
                        {"channel": "paid_social", "format": "dynamic product ads", "budget": 2000, "kpi": "ROAS >= 4.0x"},
                        {"channel": "paid_search", "format": "remarketing lists for search ads", "budget": 1500, "kpi": "ROAS >= 5.0x"}
                    ]
                }
            ],
            "audience_targeting": [
                {"segment": "Lookalike 1% (top customers)", "rationale": "Highest historical LTV signal"},
                {"segment": "Website visitors (90-day, no purchase)", "rationale": "Warm intent, low CAC"},
                {"segment": "Interest: marketing analytics, agency tools", "rationale": "Category-adjacent prospects"}
            ],
            "kpis": [
                {"metric": "Blended ROAS", "target": "4.0x", "measurement": "Daily via attribution report"},
                {"metric": "Total conversions", "target": "180", "measurement": "Campaign-level via platform pixels"},
                {"metric": "CAC", "target": "<= $55", "measurement": "Weekly cohort review"}
            ],
            "copy_brief": {
                "tone": "Confident, data-forward, no jargon",
                "key_messages": [
                    "Marketing data unified in one place",
                    "AI insights that drive action, not just dashboards",
                    "Built for agencies who own client outcomes"
                ],
                "cta": "Start your free 14-day trial"
            },
            "schedule": {
                "start_date": None,
                "milestones": [
                    "Week 1 Mon: Campaign launch",
                    "Week 2 Fri: Phase 1 performance review",
                    "Week 3 Wed: Budget reallocation decision",
                    "Week 4 Fri: Final report + retro"
                ]
            }
        }, indent=2)

    if '"variants"' in p and '"headline"' in p:
        # ad_copy template
        return json.dumps({
            "variants": [
                {
                    "headline": "Your data, your insights — in seconds.",
                    "body": "Unify GA4, Meta Ads, and HubSpot. Let AI surface what's working before your client asks.",
                    "cta": "Start free trial",
                    "character_count": {"headline": 38, "body": 95}
                },
                {
                    "headline": "Built for agencies who own outcomes.",
                    "body": "Cross-platform ETL + Claude-powered insights. Reports that write themselves.",
                    "cta": "See it in action",
                    "character_count": {"headline": 37, "body": 78}
                }
            ],
            "usage_notes": "Lead with variant A for cold audiences; B converts better with existing leads."
        }, indent=2)

    if '"subject_lines"' in p and '"preview_text"' in p:
        # email_copy template
        return json.dumps({
            "subject_lines": [
                "Your Q2 numbers are in (and they're interesting)",
                "AI just spotted 3 ways to lift your ROAS",
                "Quick: 5 mins to a smarter campaign"
            ],
            "preview_text": "We crunched the data so you don't have to.",
            "body": {
                "opening": "Hi {{first_name}}, your monthly performance review is ready.",
                "main_content": "This quarter saw a 12% lift in conversions driven primarily by Newsletter Promo (4.6x ROAS) — while Retargeting showed signs of creative fatigue. We've outlined 3 specific moves to make this week, with expected impact.",
                "cta_button_text": "View Full Report",
                "closing": "As always, we're here if you want to talk through any of it. — The team"
            },
            "personalization_tokens": ["{{first_name}}", "{{agency_name}}", "{{top_campaign}}"]
        }, indent=2)

    # Fallback
    return json.dumps({"mock": True, "message": "Template fingerprint not recognized by mock"}, indent=2)


class ClaudeContentModel(BaseContentModel):
    model_class = "ClaudeContentModel"

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key) if not settings.mock_claude else None

    async def generate(self, request: ContentRequest) -> ContentResponse:
        if settings.mock_claude:
            return ContentResponse(
                content=_mock_response(request.user_prompt),
                usage={"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "mock": True},
                model=f"{_MODEL} (mock)",
            )

        response = await self._client.messages.create(
            model=_MODEL,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=[
                {
                    "type": "text",
                    "text": request.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": request.user_prompt}],
        )
        return ContentResponse(
            content=response.content[0].text,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0),
                "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0),
            },
            model=response.model,
        )


ContentModelRegistry.register(ClaudeContentModel)
