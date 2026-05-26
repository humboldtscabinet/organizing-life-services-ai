"""One-off: break down GA4 conversions by event name & source for paid traffic."""
import os
from datetime import datetime, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, Filter, FilterExpression, RunReportRequest

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/app/credentials/google-service-account.json")
client = BetaAnalyticsDataClient()
prop = os.environ["GA4_PROPERTY_ID"]
end = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
start = (datetime.utcnow().date() - timedelta(days=31)).isoformat()

def run(label, dims, metrics, dim_filter=None):
    req = RunReportRequest(
        property=f"properties/{prop}",
        dimensions=[Dimension(name=d) for d in dims],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimension_filter=dim_filter,
        limit=50,
    )
    resp = client.run_report(req)
    print(f"\n=== {label} ===")
    print(" | ".join(dims + metrics))
    for row in resp.rows:
        vals = [v.value for v in row.dimension_values] + [v.value for v in row.metric_values]
        print(" | ".join(vals))

# 1. Conversions by event name (all traffic)
run("Conversions by event name (all traffic, 30d)",
    ["eventName"], ["conversions", "eventCount"])

# 2. Conversions by source/medium
run("Conversions by sessionSource/sessionMedium (30d)",
    ["sessionSource", "sessionMedium"], ["conversions", "sessions"])

# 3. Conversions by campaign + event for paid only
paid_filter = FilterExpression(filter=Filter(
    field_name="sessionMedium",
    string_filter=Filter.StringFilter(value="cpc")))
run("Conversions by campaign + event for sessionMedium=cpc (30d)",
    ["sessionGoogleAdsCampaignName", "eventName"], ["conversions", "eventCount"],
    dim_filter=paid_filter)
