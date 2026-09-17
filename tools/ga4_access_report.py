#!/usr/bin/env python3
"""GA4 access report for cookingauto.

Reads a Google service-account JSON from GA4_SERVICE_ACCOUNT_JSON and queries
Google Analytics Data API v1beta. No existing publishing workflow is touched.
"""
import json
import os
from datetime import date, timedelta
from pathlib import Path

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "15778234011")
LOOKBACK_DAYS = int(os.getenv("GA4_LOOKBACK_DAYS", "28"))
SERVICE_ACCOUNT_JSON = os.getenv("GA4_SERVICE_ACCOUNT_JSON", "")


def credentials():
    if not SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GA4_SERVICE_ACCOUNT_JSON is not configured")
    info = json.loads(SERVICE_ACCOUNT_JSON)
    return service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )


def run_report(creds, dimensions, metrics, limit=100):
    creds.refresh(Request())
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{PROPERTY_ID}:runReport"
    end = date.today()
    start = end - timedelta(days=LOOKBACK_DAYS - 1)
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": x} for x in dimensions],
        "metrics": [{"name": x} for x in metrics],
        "limit": limit,
        "orderBys": [{"metric": {"metricName": metrics[0]}, "desc": True}],
    }
    r = requests.post(url, headers={"Authorization": f"Bearer {creds.token}"}, json=body, timeout=60)
    r.raise_for_status()
    return start, end, r.json()


def value(row, key):
    for i, h in enumerate(row.get("dimensionHeaders", [])):
        if h.get("name") == key:
            return row.get("dimensionValues", [])[i].get("value", "")
    return ""


def metric(row, key):
    for i, h in enumerate(row.get("metricHeaders", [])):
        if h.get("name") == key:
            return row.get("metricValues", [])[i].get("value", "0")
    return "0"


def main():
    creds = credentials()
    reports = {}
    for name, dims, mets, limit in [
        ("pages", ["pagePath", "pageTitle"], ["screenPageViews", "sessions", "totalUsers"], 100),
        ("sources", ["sessionSource", "sessionMedium"], ["sessions", "totalUsers"], 50),
        ("events", ["eventName"], ["eventCount", "totalUsers"], 100),
        ("outbound", ["pagePath", "linkUrl"], ["eventCount", "totalUsers"], 100),
    ]:
        start, end, data = run_report(creds, dims, mets, limit)
        reports[name] = (start, end, data)

    lines = [
        "# GA4アクセス分析レポート",
        f"期間: {reports['pages'][0]} ～ {reports['pages'][1]}",
        f"GA4 Property: {PROPERTY_ID}",
        "",
        "## 1. よく読まれた記事",
        "| ページ | PV | セッション | ユーザー |",
        "|---|---:|---:|---:|",
    ]
    for row in reports["pages"][2].get("rows", []):
        lines.append(f"| {value(row,'pagePath')} — {value(row,'pageTitle')} | {metric(row,'screenPageViews')} | {metric(row,'sessions')} | {metric(row,'totalUsers')} |")

    lines += ["", "## 2. 流入元", "| source | medium | sessions | users |", "|---|---|---:|---:|"]
    for row in reports["sources"][2].get("rows", []):
        lines.append(f"| {value(row,'sessionSource')} | {value(row,'sessionMedium')} | {metric(row,'sessions')} | {metric(row,'totalUsers')} |")

    lines += ["", "## 3. イベント", "| event | count | users |", "|---|---:|---:|"]
    for row in reports["events"][2].get("rows", []):
        lines.append(f"| {value(row,'eventName')} | {metric(row,'eventCount')} | {metric(row,'totalUsers')} |")

    lines += ["", "## 4. 外部リンククリック候補", "| page | linkUrl | count | users |", "|---|---|---:|---:|"]
    for row in reports["outbound"][2].get("rows", []):
        url = value(row, "linkUrl")
        if url:
            lines.append(f"| {value(row,'pagePath')} | {url} | {metric(row,'eventCount')} | {metric(row,'totalUsers')} |")

    Path("ga4_access_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("GA4 report written to ga4_access_report.md")


if __name__ == "__main__":
    main()
