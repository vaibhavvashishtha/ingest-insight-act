# Static hints mapping well-known GA4 field names to canonical schema fields.
# Used as seed context when Claude performs AI-assisted mapping in explore_schema.
GA4_CANONICAL_HINTS: dict[str, str] = {
    # dimensions
    "date": "date_key",
    "campaignName": "campaign_name",
    "sessionCampaignName": "campaign_name",
    "medium": "channel",
    "sessionMedium": "channel",
    "source": "source_name",
    "sessionSource": "source_name",
    "deviceCategory": "device_category",
    "country": "country",
    "city": "city",
    "audienceName": "audience_name",
    "adGroupName": "ad_group_name",
    # metrics
    "sessions": "clicks",
    "screenPageViews": "impressions",
    "totalUsers": "unique_users",
    "newUsers": "new_users",
    "bounceRate": "bounce_rate",
    "averageSessionDuration": "avg_session_duration_s",
    "conversions": "conversions",
    "eventCount": "event_count",
    "engagedSessions": "engaged_sessions",
    "engagementRate": "engagement_rate",
    # ecommerce / revenue
    "purchaseRevenue": "revenue",
    "ecommercePurchases": "conversions",
    "addToCarts": "add_to_carts",
    # ads cost data (requires linking GA4 to Google Ads)
    "advertiserAdCost": "spend",
    "advertiserAdClicks": "clicks",
    "advertiserAdImpressions": "impressions",
    "returnOnAdSpend": "roas",
}

# GA4 fields that map directly to canonical performance metrics
CANONICAL_METRICS = {
    "impressions",
    "clicks",
    "spend",
    "conversions",
    "revenue",
}
