"""Lambda entry: /health fast path does not load FastAPI."""
import json

import lambda_entry as lh


def _apigw_v2_get_health():
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/health",
        "requestContext": {"http": {"method": "GET"}},
    }


def test_health_get_no_db_url_degraded(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    out = lh.handler(_apigw_v2_get_health(), None)
    assert out["statusCode"] == 200
    body = json.loads(out["body"])
    assert body["status"] == "degraded"
    assert body["database"] == "disconnected"
    assert body["service"] == "trading-card-api"


def test_health_get_other_routes_use_mangum(monkeypatch):
    called = []

    def fake_mangum():
        def inner(ev, ctx):
            called.append(True)
            return {"statusCode": 200, "headers": {}, "body": "{}"}

        return inner

    monkeypatch.setattr(lh, "_get_mangum", fake_mangum)
    ev = {
        "version": "2.0",
        "rawPath": "/api/cards",
        "requestContext": {"http": {"method": "GET"}},
    }
    lh.handler(ev, None)
    assert called == [True]
