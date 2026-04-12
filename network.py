from __future__ import annotations

import asyncio
import json
import sys
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FIREBASE_URL = "https://bartender-leaderboard-default-rtdb.firebaseio.com"
FETCH_TIMEOUT_SECONDS = 8.0
_BROWSER_FETCH_BRIDGE_READY = False


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

    global _BROWSER_FETCH_BRIDGE_READY
    if not _BROWSER_FETCH_BRIDGE_READY:
        platform.window.eval(
            """
if (!window.CodexFetch) {
    window.CodexFetch = {};
    window.CodexFetch.GET = function * GET(url) {
        let content = "__CODEX_FETCH_PENDING__";
        fetch(new Request(url, { method: "GET" }))
            .then((resp) => resp.text())
            .then((resp) => { content = resp; })
            .catch((err) => {
                console.log("[network] GET error", err);
                content = "__CODEX_FETCH_ERROR__";
            });
        while (content === "__CODEX_FETCH_PENDING__") {
            yield;
        }
        yield content;
    };
    window.CodexFetch.POST = function * POST(url, data) {
        let content = "__CODEX_FETCH_PENDING__";
        fetch(new Request(url, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: data
        }))
            .then((resp) => resp.text())
            .then((resp) => { content = resp; })
            .catch((err) => {
                console.log("[network] POST error", err);
                content = "__CODEX_FETCH_ERROR__";
            });
        while (content === "__CODEX_FETCH_PENDING__") {
            yield;
        }
        yield content;
    };
}
            """
        )
        _BROWSER_FETCH_BRIDGE_READY = True

    await asyncio.sleep(0)
    if method == "POST":
        raw_text = await platform.jsiter(
            platform.window.CodexFetch.POST(url, json.dumps(body or {})),
        )
    else:
        raw_text = await platform.jsiter(platform.window.CodexFetch.GET(url))

    if raw_text == "__CODEX_FETCH_ERROR__":
        print(f"[network] Browser request failed: {method} {url}")
        return (False, None)

    try:
        payload = json.loads(raw_text) if raw_text else None
    except Exception as error:
        print(f"[network] Failed to parse browser response from {url}: {error}")
        payload = None
    return (True, payload)


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
    except Exception as error:
        print(f"[network] Leaderboard fetch exception: {error}")
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
    except Exception as error:
        print(f"[network] Score submit exception: {error}")
        return False
    return ok
