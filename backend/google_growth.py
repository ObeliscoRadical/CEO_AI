import os
from datetime import date, timedelta
from urllib.parse import urlparse

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.auth import default
from googleapiclient.discovery import build


GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
GA_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


def google_growth_config() -> dict:
    return {
        "credentials_path": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
        "gsc_site_url": os.environ.get("GSC_SITE_URL", "").strip(),
        "ga4_property_id": os.environ.get("GA4_PROPERTY_ID", "").strip(),
        "ga4_measurement_id": os.environ.get("GA4_MEASUREMENT_ID", "").strip(),
        "site_public_base_url": (os.environ.get("SITE_PUBLIC_BASE_URL") or os.environ.get("FRONTEND_URL") or "").rstrip("/"),
    }


def google_growth_status() -> dict:
    config = google_growth_config()
    credentials_ready = bool(config["credentials_path"] and os.path.exists(config["credentials_path"]))
    return {
        **config,
        "credentials_ready": credentials_ready,
        "gsc_configured": bool(config["gsc_site_url"]),
        "ga4_configured": bool(config["ga4_property_id"]),
        "ga4_measurement_installed": bool(config["ga4_measurement_id"]),
    }


def normalize_page_path(url_or_path: str) -> str:
    if not url_or_path:
        return "/"
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        parsed = urlparse(url_or_path)
        path = parsed.path or "/"
    else:
        path = url_or_path
    if not path.startswith("/"):
        path = f"/{path}"
    return path.rstrip("/") or "/"


def sync_windows() -> dict:
    end_recent = date.today() - timedelta(days=3)
    start_recent = end_recent - timedelta(days=6)
    end_baseline = start_recent - timedelta(days=1)
    start_baseline = end_baseline - timedelta(days=27)
    return {
        "recent": {"start": start_recent.isoformat(), "end": end_recent.isoformat()},
        "baseline": {"start": start_baseline.isoformat(), "end": end_baseline.isoformat()},
        "queries": {"start": (end_recent - timedelta(days=27)).isoformat(), "end": end_recent.isoformat()},
    }


class GoogleGrowthClient:
    def __init__(self):
        config = google_growth_status()
        if not (config["credentials_ready"] and config["gsc_configured"] and config["ga4_configured"]):
            raise RuntimeError("Configuração Google incompleta para o agente de Growth.")
        creds, _ = default(scopes=[GSC_SCOPE, GA_SCOPE])
        self.site_url = config["gsc_site_url"]
        self.property = f"properties/{config['ga4_property_id']}"
        self.gsc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        self.ga = BetaAnalyticsDataClient(credentials=creds)

    def search_console_pages(self, start_date: str, end_date: str, row_limit: int = 25000) -> list[dict]:
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["page"],
            "type": "web",
            "aggregationType": "auto",
            "rowLimit": min(row_limit, 25000),
        }
        response = self.gsc.searchanalytics().query(siteUrl=self.site_url, body=body).execute(num_retries=2)
        rows = []
        for row in response.get("rows", []):
            page = (row.get("keys") or [""])[0]
            rows.append({
                "page_url": page,
                "page_path": normalize_page_path(page),
                "clicks": float(row.get("clicks", 0) or 0),
                "impressions": float(row.get("impressions", 0) or 0),
                "ctr": float(row.get("ctr", 0) or 0),
                "position": float(row.get("position", 0) or 0),
            })
        return rows

    def search_console_queries(self, start_date: str, end_date: str, row_limit: int = 200) -> list[dict]:
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query", "page"],
            "type": "web",
            "aggregationType": "auto",
            "rowLimit": min(row_limit, 25000),
        }
        response = self.gsc.searchanalytics().query(siteUrl=self.site_url, body=body).execute(num_retries=2)
        rows = []
        for row in response.get("rows", []):
            keys = row.get("keys") or ["", ""]
            page = keys[1] if len(keys) > 1 else ""
            rows.append({
                "query": keys[0],
                "page_url": page,
                "page_path": normalize_page_path(page),
                "clicks": float(row.get("clicks", 0) or 0),
                "impressions": float(row.get("impressions", 0) or 0),
                "ctr": float(row.get("ctr", 0) or 0),
                "position": float(row.get("position", 0) or 0),
            })
        return rows

    def ga4_pages(self, start_date: str, end_date: str) -> list[dict]:
        request = RunReportRequest(
            property=self.property,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="pagePath")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="engagementRate"),
                Metric(name="conversions"),
            ],
            limit=10000,
        )
        response = self.ga.run_report(request)
        rows = []
        for item in response.rows:
            page_path = item.dimension_values[0].value or "/"
            rows.append({
                "page_path": normalize_page_path(page_path),
                "sessions": float(item.metric_values[0].value or 0),
                "users": float(item.metric_values[1].value or 0),
                "engagement_rate": float(item.metric_values[2].value or 0),
                "conversions": float(item.metric_values[3].value or 0),
            })
        return rows