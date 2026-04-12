from __future__ import annotations

import asyncio
import json
import sys
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FIREBASE_URL = "https://bartender-leaderboard-default-rtdb.firebaseio.com"
FETCH_TIMEOUT_SECONDS = 8.0


def _leaderboard_url() -> str:
    query = urlencode({
        "orderBy": '"score"',
        "limitToLast": 10,
    })
    return f"{FIREBASE_URL}/highscores.json?{query}"


def _submit_url() -> str:
    return f"{FIREBASE_URL}/highscores.json"


def _sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        entries,
        key=lambda entry: (
            -int(entry.get("score", 0)),
            -int(entry.get("level", 0)),
            int(entry.get("timestamp", 0)),
            str(entry.get("initials", "")),
        ),
    )[:10]


def _normalize_entries(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    entries = [entry for entry in payload.values() if isinstance(entry, dict)]
    return _sort_entries(entries)


async def _browser_json_request(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> tuple[bool, Any]:
    import platform
    from pyodide.ffi import to_js

    request_options: dict[str, Any] = {
        "method": method,
    }
    if body is not None:
        request_options["headers"] = {"Content-Type": "application/json"}
        request_options["body"] = json.dumps(body)

    response = await platform.window.fetch(url, to_js(request_options))
    try:
        raw_text = await response.text()
        payload = json.loads(raw_text) if raw_text else None
    except Exception:
        payload = None
    return (response.ok, payload)


def _desktop_json_request_sync(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> tuple[bool, Any]:
    payload_bytes: bytes | None = None
    headers: dict[str, str] = {}
    if body is not None:
        payload_bytes = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=payload_bytes, headers=headers, method=method)
    with urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        raw_body = response.read().decode("utf-8")
        if not raw_body:
            return (200 <= response.status < 300, None)
        return ((200 <= response.status < 300), json.loads(raw_body))


async def _json_request(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> tuple[bool, Any]:
    if sys.platform == "emscripten":
        return await _browser_json_request(url, method=method, body=body)
    return await asyncio.to_thread(
        _desktop_json_request_sync,
        url,
        method=method,
        body=body,
    )


async def fetch_leaderboard() -> list[dict[str, Any]]:
    try:
        ok, payload = await _json_request(_leaderboard_url())
    except Exception:
        return []
    if not ok:
        return []
    return _normalize_entries(payload)


async def submit_score(initials: str, score: int, level: int) -> bool:
    payload = {
        "initials": initials,
        "score": score,
        "level": level,
        "timestamp": {".sv": "timestamp"},
    }
    try:
        ok, _ = await _json_request(
            _submit_url(),
            method="POST",
            body=payload,
        )
    except Exception:
        return False
    return ok
