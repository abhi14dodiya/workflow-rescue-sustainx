"""Publish only the verified static submission portal to unbilled Firebase Hosting.

The default is a local dry run. --publish creates a Firebase Hosting version and
release, never a Cloud Run service, billing link, API key or paid fallback.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import time
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "gen-lang-client-0915819772"
PUBLIC = ROOT / "artifacts/submission-portal"
API = "https://firebasehosting.googleapis.com/v1beta1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    manifest_path = ROOT / "artifacts/submission-portal-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("site") != PROJECT or Path(manifest["public_directory"]).resolve() != PUBLIC.resolve():
        raise SystemExit("Unexpected portal directory or Firebase site.")
    actual_files = {p.relative_to(PUBLIC).as_posix(): p for p in PUBLIC.rglob("*") if p.is_file()}
    if set(actual_files) != set(manifest["files"]):
        raise SystemExit("Portal files changed after preparation; rebuild and inspect them.")
    for relative, path in actual_files.items():
        if path.is_symlink() or not path.resolve().is_relative_to(PUBLIC.resolve()):
            raise SystemExit("Portal files must remain within the generated directory.")
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["files"][relative]["sha256"]:
            raise SystemExit("A prepared portal file changed; regenerate its manifest before publishing.")
    for asset in manifest["assets"].values():
        if asset.get("ready"):
            source = ROOT / asset["source"]
            if hashlib.sha256(source.read_bytes()).hexdigest() != asset["sha256"]:
                raise SystemExit("An original deck/video file changed; prepare the final portal again.")
    if manifest["total_bytes"] >= 100_000_000:
        raise SystemExit("The portal exceeds its deliberate 100 MB package limit.")
    preview = {"url": manifest["url"], "files": list(actual_files), "total_bytes": manifest["total_bytes"],
               "assets_ready": manifest.get("assets_ready", False), "publish_requested": args.publish}
    print(json.dumps(preview, indent=2), flush=True)
    if not args.publish:
        return
    if not manifest.get("assets_ready"):
        raise SystemExit("Publication requires the final deck, PDF and validated 3-4 minute live Gemini video.")

    gcloud = shutil.which("gcloud.cmd" if os.name == "nt" else "gcloud")
    if not gcloud:
        raise SystemExit("gcloud is required for authenticated deployment.")
    def cloud(*arguments):
        result = subprocess.run([gcloud, *arguments], capture_output=True, text=True)
        if result.returncode:
            raise SystemExit("gcloud verification failed; inspect authentication separately.")
        return result.stdout.strip()
    def unbilled():
        if cloud("billing", "projects", "describe", PROJECT, "--format=value(billingEnabled)").lower() != "false":
            raise SystemExit("Free-only guard: project billing must remain disabled.")
    unbilled()
    token = cloud("auth", "print-access-token")
    config = json.loads((ROOT / "firebase.submission.json").read_text(encoding="utf-8"))["hosting"]
    if config["site"] != PROJECT or config["public"] != "artifacts/submission-portal":
        raise SystemExit("Unexpected Firebase submission configuration.")
    rest_config = {"headers": [{"glob": item["source"],
                    "headers": {h["key"]: h["value"] for h in item["headers"]}}
                   for item in config["headers"]]}
    hashes, compressed = {}, {}
    for relative, path in actual_files.items():
        data = gzip.compress(path.read_bytes(), compresslevel=6, mtime=0)
        digest = hashlib.sha256(data).hexdigest()
        hashes["/" + relative] = digest
        compressed[digest] = data
    with httpx.Client(verify=ssl.create_default_context(), timeout=120,
                      headers={"Authorization": "Bearer " + token, "x-goog-user-project": PROJECT}) as client:
        def request(method, url, **kwargs):
            response = client.request(method, url, **kwargs)
            if response.status_code >= 400:
                raise SystemExit(f"Firebase Hosting request failed: HTTP {response.status_code}. No credential or raw response was logged.")
            return response.json() if response.content else {}
        sites = request("GET", f"{API}/projects/{PROJECT}/sites")
        if not any(item.get("name", "").endswith("/sites/" + PROJECT) for item in sites.get("sites", [])):
            raise SystemExit("The expected Firebase Hosting site does not exist; no version was created.")
        version = request("POST", f"{API}/sites/{PROJECT}/versions", json={"config": rest_config})
        version_name = version["name"]
        if not version_name.startswith(f"sites/{PROJECT}/versions/"):
            raise SystemExit("Unexpected Hosting version response.")
        upload = request("POST", f"{API}/{version_name}:populateFiles", json={"files": hashes})
        upload_base = upload["uploadUrl"]
        if urlsplit(upload_base).scheme != "https" or urlsplit(upload_base).hostname != "upload-firebasehosting.googleapis.com":
            raise SystemExit("Unexpected Firebase upload endpoint; credentials were not forwarded.")
        for digest in upload.get("uploadRequiredHashes", []):
            if digest not in compressed:
                raise SystemExit("Unexpected requested file hash.")
            response = client.post(upload_base + "/" + digest, content=compressed[digest],
                                   headers={"Content-Type": "application/octet-stream"})
            if response.status_code != 200:
                raise SystemExit(f"Firebase file upload failed: HTTP {response.status_code}.")
            print(json.dumps({"uploaded_bytes": len(compressed[digest])}), flush=True)
        final = request("PATCH", f"{API}/{version_name}", params={"update_mask": "status"}, json={"status": "FINALIZED"})
        if final.get("status") != "FINALIZED":
            raise SystemExit("The Hosting version was not finalized; no release was created.")
        release = request("POST", f"{API}/sites/{PROJECT}/releases", params={"versionName": version_name})
    unbilled()
    verification = {}
    with httpx.Client(verify=ssl.create_default_context(), timeout=30, follow_redirects=True) as public:
        for attempt in range(6):
            response = public.get(manifest["url"] + "/?release=" + version_name.rsplit("/", 1)[-1])
            if response.status_code == 200 and "Workflow Rescue" in response.text:
                break
            time.sleep(2)
        else:
            raise SystemExit("Hosting release exists, but the public page did not verify yet.")
        verification["/"] = {"status": response.status_code, "content_type": response.headers.get("content-type")}
        for asset in manifest["assets"].values():
            response = public.head(manifest["url"] + asset["path"])
            verification[asset["path"]] = {"status": response.status_code,
                "content_type": response.headers.get("content-type"), "content_length": response.headers.get("content-length")}
            if response.status_code != 200:
                raise SystemExit("A published submission asset failed its public HEAD check.")
    result = {"published_at": datetime.now(timezone.utc).isoformat(), "url": manifest["url"],
              "portal_type": manifest["portal_type"], "release": release.get("name"), "version": version_name,
              "billing_enabled": False, "total_bytes": manifest["total_bytes"], "verification": verification}
    (ROOT / "artifacts/submission-portal-deployment.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    manifest["published"] = True
    manifest["release"] = release.get("name")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
