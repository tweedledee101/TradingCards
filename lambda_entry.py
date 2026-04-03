"""
Lambda container entrypoint (lives at /var/task — loaded first, no backend.* import at init).

API Gateway returns {\"message\":\"Internal Server Error\"} when Lambda throws or times out
before emitting a valid proxy response; this module catches failures and returns JSON.
"""
from __future__ import annotations

import json
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict

_mangum_handler = None


def _normalize_path(event: Dict[str, Any]) -> str:
    path = event.get("rawPath") or event.get("path") or ""
    if not path:
        rc = event.get("requestContext") or {}
        http = rc.get("http") or {}
        path = http.get("path") or rc.get("path") or ""
    path = (path or "/").rstrip("/") or "/"
    return path


def _http_method(event: Dict[str, Any]) -> str:
    rc = event.get("requestContext") or {}
    http = rc.get("http") or {}
    return (http.get("method") or event.get("httpMethod") or "").upper()


def _cors_headers_json() -> Dict[str, str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "*")
    origin = raw.split(",")[0].strip() or "*"
    return {
        "content-type": "application/json",
        "access-control-allow-origin": origin,
        "access-control-allow-credentials": "true",
    }


def _health_payload() -> Dict[str, Any]:
    db_status = "disconnected"
    url = os.environ.get("DATABASE_URL")
    if url:
        try:
            import psycopg2

            conn = psycopg2.connect(url, connect_timeout=2)
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                db_status = "connected"
            finally:
                conn.close()
        except Exception:
            db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "trading-card-api",
        "database": db_status,
        "retention": "skipped",
    }


def _json_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": _cors_headers_json(),
        "body": json.dumps(body),
        "isBase64Encoded": False,
    }


def _get_mangum():
    global _mangum_handler
    if _mangum_handler is None:
        from mangum import Mangum
        from backend.api.main import app

        _mangum_handler = Mangum(app, lifespan="off")
    return _mangum_handler


def _dispatch(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    if not isinstance(event, dict):
        return _json_response(
            500,
            {"error": "invalid_event", "detail": type(event).__name__},
        )

    method = _http_method(event)
    path = _normalize_path(event)

    if path == "/health":
        if method == "GET":
            return _json_response(200, _health_payload())
        if method == "OPTIONS":
            raw = os.environ.get("CORS_ALLOW_ORIGINS", "*")
            origin = raw.split(",")[0].strip() or "*"
            return {
                "statusCode": 204,
                "headers": {
                    "access-control-allow-origin": origin,
                    "access-control-allow-credentials": "true",
                    "access-control-allow-methods": "GET,OPTIONS",
                    "access-control-allow-headers": "*",
                },
                "body": "",
                "isBase64Encoded": False,
            }

    return _get_mangum()(event, context)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Always emit one line first — if you see API Gateway 500 but never this line in
    # /aws/lambda/ragnarok-trading-api, the break is before user code (invoke/permission/init).
    rid = getattr(context, "aws_request_id", None) if context else None
    raw_path = event.get("rawPath") if isinstance(event, dict) else None
    print(
        json.dumps(
            {"lambda_diag": "handler_entry", "aws_request_id": rid, "rawPath": raw_path},
            default=str,
        ),
        flush=True,
    )
    try:
        return _dispatch(event, context)
    except Exception:
        tb = traceback.format_exc()
        print(tb, flush=True)
        return {
            "statusCode": 500,
            "headers": {"content-type": "application/json"},
            "body": json.dumps(
                {
                    "error": "unhandled",
                    "detail": tb[-4000:],
                }
            ),
            "isBase64Encoded": False,
        }
