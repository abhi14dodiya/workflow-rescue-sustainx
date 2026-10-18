"""Enable Firebase metadata and deploy server-only Firestore rules without billing.

Requires an existing unbilled Google Cloud project and a default Firestore
database already created with freeTier=true. Does not link billing, create
Cloud Run services, or deploy an incomplete Hosting frontend.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default="gen-lang-client-0915819772")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", args.project):
        raise SystemExit("Invalid project ID.")
    gcloud = shutil.which("gcloud.cmd" if os.name == "nt" else "gcloud")
    if not gcloud:
        raise SystemExit("gcloud is required.")

    def cloud(*command):
        result = subprocess.run([gcloud, *command], capture_output=True, text=True, check=False)
        if result.returncode:
            raise SystemExit("Google Cloud authentication or project verification failed; check gcloud separately.")
        return result.stdout.strip()

    billing = cloud("billing", "projects", "describe", args.project, "--format=value(billingEnabled)")
    if billing.lower() != "false":
        raise SystemExit("Free-only guard: this script requires billingEnabled=False.")
    database = json.loads(cloud("firestore", "databases", "describe", "--database=(default)", f"--project={args.project}", "--format=json"))
    if database.get("freeTier") is not True:
        raise SystemExit("Free-only guard: the existing default database must report freeTier=true.")

    token = cloud("auth", "print-access-token")
    report = {"project": args.project, "billing_enabled": False,
              "firestore_free_tier": True, "database_location": database["locationId"]}
    with httpx.Client(verify=ssl.create_default_context(), timeout=40,
                      headers={"Authorization": f"Bearer {token}", "x-goog-user-project": args.project}) as client:
        def request(method, url, **kwargs):
            response = client.request(method, url, **kwargs)
            if response.status_code >= 400:
                raise SystemExit(f"Firebase configuration request failed with HTTP {response.status_code}; no response body or credential logged.")
            return response.json() if response.content else {}

        project_url = f"https://firebase.googleapis.com/v1beta1/projects/{args.project}"
        existing = client.get(project_url)
        if existing.status_code == 404:
            operation = request("POST", project_url + ":addFirebase", json={})
            for _ in range(30):
                operation = request("GET", "https://firebase.googleapis.com/v1beta1/" + operation["name"])
                if operation.get("done"):
                    if "error" in operation:
                        raise SystemExit("Firebase setup failed; inspect the operation in Google Cloud console.")
                    break
                time.sleep(2)
            else:
                raise SystemExit("Firebase setup still running; rerun after it completes.")
        elif existing.status_code != 200:
            raise SystemExit(f"Firebase project lookup failed with HTTP {existing.status_code}.")
        firebase_project = request("GET", project_url)
        report["firebase_project_state"] = firebase_project.get("state")
        report["firebase_hosting_site"] = firebase_project.get("resources", {}).get("hostingSite")

        rules_url = f"https://firebaserules.googleapis.com/v1/projects/{args.project}"
        ruleset = request("POST", rules_url + "/rulesets", json={
            "source": {"files": [{"name": "firestore.rules", "content": (ROOT / "firestore.rules").read_text(encoding="utf-8")}]} 
        })
        release_name = f"projects/{args.project}/releases/cloud.firestore"
        release = {"name": release_name, "rulesetName": ruleset["name"]}
        existing_release = client.get("https://firebaserules.googleapis.com/v1/" + release_name)
        if existing_release.status_code == 404:
            request("POST", rules_url + "/releases", json=release)
        elif existing_release.status_code == 200:
            request("PATCH", "https://firebaserules.googleapis.com/v1/" + release_name,
                    json={"release": release, "updateMask": "rulesetName"})
        else:
            raise SystemExit(f"Firestore rules lookup failed with HTTP {existing_release.status_code}.")
        report["firestore_client_rules"] = "deny all reads and writes; server IAM only"
        report["ruleset"] = ruleset["name"]
    report["billing_enabled_after"] = cloud("billing", "projects", "describe", args.project, "--format=value(billingEnabled)").lower() == "true"
    output = ROOT / "artifacts" / "firebase-free-setup.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
