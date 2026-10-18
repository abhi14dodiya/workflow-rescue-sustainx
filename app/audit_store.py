"""Optional server-only Firestore persistence for synthetic recovery reports.

Enable with FIRESTORE_PROJECT_ID. Uses Application Default Credentials (ADC),
never a browser credential or the Gemini API key. Firestore client access should
remain denied; only the server's IAM identity accesses these documents.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import ssl
from typing import Any

import google.auth
from google.auth.transport.requests import Request
import httpx

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_PROJECT = re.compile(r"^[a-z][a-z0-9-]{4,61}[a-z0-9]$")
_COLLECTION = "workflow_rescue_audits"
_MAX_REPORT_BYTES = 800_000


class AuditStoreError(RuntimeError):
    """Public-safe persistence failure; never includes upstream response text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Audit persistence unavailable ({code}). Export this report locally.")


def configured() -> bool:
    return bool(os.getenv("FIRESTORE_PROJECT_ID", "").strip())


def _document_url(identifier: str) -> str:
    project = os.getenv("FIRESTORE_PROJECT_ID", "").strip()
    if not _PROJECT.fullmatch(project):
        raise AuditStoreError("INVALID_PROJECT")
    if not isinstance(identifier, str) or not _IDENTIFIER.fullmatch(identifier):
        raise AuditStoreError("INVALID_REPORT_ID")
    return (f"https://firestore.googleapis.com/v1/projects/{project}/databases/"
            f"(default)/documents/{_COLLECTION}/{identifier}")


def _adc_token() -> str:
    try:
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/datastore"])
        credentials.refresh(Request())
        if not credentials.token:
            raise ValueError("No token")
        return credentials.token
    except Exception:
        raise AuditStoreError("ADC_UNAVAILABLE") from None


async def _request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    token = await asyncio.to_thread(_adc_token)
    try:
        async with httpx.AsyncClient(verify=ssl.create_default_context(), timeout=20.0) as client:
            return await client.request(method, url, headers={"Authorization": f"Bearer {token}"}, **kwargs)
    except (httpx.HTTPError, OSError):
        raise AuditStoreError("NETWORK") from None


async def save_audit(record: dict) -> dict:
    """Persist a report; return a safe result so storage cannot abort recovery.

    Returns {saved: bool, backend: str, code?: str}. The caller can attach this
    result to the in-memory report and offer local JSON export on failure.
    """
    if not configured():
        return {"saved": False, "backend": "disabled"}
    try:
        identifier = record.get("id", "")
        url = _document_url(identifier)
        try:
            serialized = json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        except (ValueError, TypeError):
            raise AuditStoreError("INVALID_REPORT") from None
        if len(serialized.encode("utf-8")) > _MAX_REPORT_BYTES:
            raise AuditStoreError("REPORT_TOO_LARGE")
        body = {"fields": {
            "run_id": {"stringValue": identifier},
            "provider": {"stringValue": str(record.get("provider", "unknown"))},
            "created_at": {"stringValue": str(record.get("created_at", ""))},
            "report_json": {"stringValue": serialized},
            "synthetic_services": {"booleanValue": True},
        }}
        response = await _request("PATCH", url, json=body)
        if response.status_code not in (200, 201):
            raise AuditStoreError(f"HTTP_{response.status_code}")
        return {"saved": True, "backend": "firestore"}
    except AuditStoreError as error:
        return {"saved": False, "backend": "firestore", "code": error.code}


async def load_audit(identifier: str) -> dict | None:
    """Load a stored run by its opaque ID; return None when missing or disabled."""
    if not configured():
        return None
    response = await _request("GET", _document_url(identifier))
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise AuditStoreError(f"HTTP_{response.status_code}")
    try:
        serialized = response.json()["fields"]["report_json"]["stringValue"]
        if not isinstance(serialized, str) or len(serialized.encode("utf-8")) > _MAX_REPORT_BYTES:
            raise ValueError("Invalid size")
        report = json.loads(serialized)
        if not isinstance(report, dict) or report.get("id") != identifier:
            raise ValueError("Mismatched report")
        report["persistence"] = {"saved": True, "backend": "firestore", "restored": True}
        return report
    except (KeyError, ValueError, TypeError):
        raise AuditStoreError("INVALID_STORED_REPORT") from None
