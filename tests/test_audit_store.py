import asyncio
import json

import httpx
import pytest

from app import audit_store


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("FIRESTORE_PROJECT_ID", "test-project-123")


def test_disabled_storage_uses_no_credentials(monkeypatch):
    monkeypatch.delenv("FIRESTORE_PROJECT_ID", raising=False)
    monkeypatch.setattr(audit_store, "_adc_token", lambda: pytest.fail("ADC must not be called"))
    assert asyncio.run(audit_store.save_audit({"id": "case-1"})) == {"saved": False, "backend": "disabled"}
    assert asyncio.run(audit_store.load_audit("case-1")) is None


def test_round_trip_preserves_verified_report_and_uses_server_auth(configured, monkeypatch):
    report = {"id": "case-1", "provider": "gemini", "events": [{"step": 1}], "checks": [{"passed": True}]}
    document = {}
    async def request(method, url, **kwargs):
        assert url.endswith("/workflow_rescue_audits/case-1")
        if method == "PATCH":
            document.update(kwargs["json"])
            return httpx.Response(200, json=document)
        return httpx.Response(200, json=document)
    monkeypatch.setattr(audit_store, "_request", request)
    assert asyncio.run(audit_store.save_audit(report))["saved"] is True
    restored = asyncio.run(audit_store.load_audit("case-1"))
    assert restored["events"] == report["events"]
    assert restored["checks"] == report["checks"]
    assert restored["persistence"]["restored"] is True
    assert document["fields"]["synthetic_services"] == {"booleanValue": True}


@pytest.mark.parametrize("identifier", ["../other", "x/y", "x?key=secret", ""])
def test_document_id_cannot_change_endpoint(configured, monkeypatch, identifier):
    monkeypatch.setattr(audit_store, "_adc_token", lambda: pytest.fail("Invalid IDs must not authenticate"))
    result = asyncio.run(audit_store.save_audit({"id": identifier}))
    assert result["code"] == "INVALID_REPORT_ID"


def test_quota_failure_is_sanitized_and_does_not_break_recovery(configured, monkeypatch):
    async def request(*args, **kwargs):
        return httpx.Response(429, text="sensitive-upstream-detail")
    monkeypatch.setattr(audit_store, "_request", request)
    result = asyncio.run(audit_store.save_audit({"id": "case-1"}))
    assert result == {"saved": False, "backend": "firestore", "code": "HTTP_429"}
    with pytest.raises(audit_store.AuditStoreError) as caught:
        asyncio.run(audit_store.load_audit("case-1"))
    assert "sensitive-upstream-detail" not in str(caught.value)


def test_missing_document_returns_none(configured, monkeypatch):
    async def request(*args, **kwargs):
        return httpx.Response(404)
    monkeypatch.setattr(audit_store, "_request", request)
    assert asyncio.run(audit_store.load_audit("case-1")) is None


def test_mismatched_stored_document_is_rejected(configured, monkeypatch):
    async def request(*args, **kwargs):
        return httpx.Response(200, json={"fields": {"report_json": {"stringValue": json.dumps({"id": "another-case"})}}})
    monkeypatch.setattr(audit_store, "_request", request)
    with pytest.raises(audit_store.AuditStoreError) as caught:
        asyncio.run(audit_store.load_audit("case-1"))
    assert caught.value.code == "INVALID_STORED_REPORT"


def test_oversized_report_is_not_uploaded(configured, monkeypatch):
    monkeypatch.setattr(audit_store, "_adc_token", lambda: pytest.fail("Oversized reports must not authenticate"))
    result = asyncio.run(audit_store.save_audit({"id": "case-1", "payload": "x" * 800_001}))
    assert result["code"] == "REPORT_TOO_LARGE"
