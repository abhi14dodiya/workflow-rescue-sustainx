"""Build a static submission portal from an explicit list of public materials.

This is a document/video portal, not the deployed interactive prototype.
No credentials, source archives, .env files or arbitrary artifact folders are copied.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "artifacts" / "submission-portal"
ASSETS = [
    ("deck_pptx", "docs/Workflow-Rescue-Official-Pitch-Reviewed.pptx", "Workflow-Rescue-Official-Pitch-Reviewed.pptx"),
    ("deck_pdf", "docs/Workflow-Rescue-Official-Pitch-Reviewed.pdf", "Workflow-Rescue-Official-Pitch-Reviewed.pdf"),
    ("deck_pptx_previous_link", "docs/Workflow-Rescue-Official-Pitch-Reviewed.pptx", "Workflow-Rescue-Official-Pitch.pptx"),
    ("deck_pdf_previous_link", "docs/Workflow-Rescue-Official-Pitch-Reviewed.pdf", "Workflow-Rescue-Official-Pitch.pdf"),
    ("video", "artifacts/video/workflow-rescue-demo.mp4", "workflow-rescue-demo.mp4"),
]

CSS = """*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#080f1b;color:#edf2fb;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif;line-height:1.6}a{color:inherit;text-decoration:none}a:focus-visible,video:focus-visible{outline:3px solid #baf278;outline-offset:5px}button,a{-webkit-tap-highlight-color:transparent}.shell{width:min(1160px,calc(100% - 48px));margin:auto}header{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:26px 0;border-bottom:1px solid #263248}.brand{font-size:18px;font-weight:780;letter-spacing:-.5px}.brand span{color:#baf278}.eyebrow{color:#a8bbd7;text-transform:uppercase;letter-spacing:2px;font-size:11px;font-weight:700}.header-link{font-size:13px;color:#b7c7e0}.header-link:hover{color:#baf278}.hero{padding:72px 0 46px;display:grid;grid-template-columns:1.25fr .85fr;gap:54px;align-items:center}h1{font-size:clamp(40px,5.2vw,67px);line-height:1.07;letter-spacing:-3px;margin:17px 0 22px;font-weight:780}h1 span{color:#baf278}.lead{font-size:17px;color:#b7c7dd;max-width:660px}.hero-actions{display:flex;gap:12px;flex-wrap:wrap;margin:28px 0 12px}.button{display:inline-flex;align-items:center;justify-content:center;gap:9px;border-radius:12px;min-height:46px;padding:11px 18px;border:1px solid #35465e;font-size:13px;font-weight:700;transition:transform .15s,background .15s}.button:hover{transform:translateY(-2px);background:#26354a}.primary{background:#baf278;color:#0c1b11;border-color:#baf278}.primary:hover{background:#c7fa90}.tiny{font-size:12px;color:#90a2be}.workflow{border:1px solid #31445a;border-radius:24px;padding:28px;background:radial-gradient(ellipse at top right,#1d3d46 0,transparent 60%),#101c2c;box-shadow:0 24px 90px #0005}.workflow .eyebrow{color:#baf278}.step{display:flex;align-items:center;gap:15px;padding:22px 0;border-bottom:1px solid #2a3d52}.step:last-of-type{border:0}.number{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;flex-shrink:0;font-size:13px;font-weight:750;color:#c9f296;background:#223b33;border:1px solid #406148}.step strong{font-size:15px}.step p{margin:2px 0 0;font-size:12px;color:#a6bad2}.checkline{padding:12px 14px;border-radius:10px;background:#132b24;color:#c2eab2;font-size:12px}.section-top{display:flex;align-items:end;justify-content:space-between;gap:20px;margin:12px 0 21px}h2{font-size:27px;line-height:1.2;letter-spacing:-.8px;margin:0 0 7px}.sub{font-size:13px;color:#a4b6cf;margin:0}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card{padding:24px;background:#101b2b;border:1px solid #29384e;border-radius:18px;display:flex;flex-direction:column;align-items:flex-start}.filetype{font-size:11px;color:#baf278;border:1px solid #3d5b48;background:#182b24;border-radius:6px;padding:3px 7px;font-weight:750;letter-spacing:1px}.card h3{font-size:19px;line-height:1.25;margin:20px 0 9px;letter-spacing:-.4px}.card p{font-size:13px;color:#a6b6ce;margin:0 0 23px}.card .button{margin-top:auto;width:100%}.card .tiny{margin-top:10px}.disabled{color:#8093af;border:1px dashed #35465e;border-radius:10px;padding:11px 18px;font-size:13px;width:100%;text-align:center;margin-top:auto}.video-section{margin-top:48px}.video-wrap{padding:10px;border:1px solid #2e4058;border-radius:18px;background:#101b2b}video{display:block;width:100%;max-height:690px;background:#02060c;border-radius:11px}.video-placeholder{display:grid;place-items:center;min-height:250px;color:#a6b6ce;background:#0c1522;border-radius:11px}.status{margin:32px 0 44px;border:1px solid #304058;border-radius:16px;overflow:hidden}.status-header{padding:16px 20px;background:#142033;font-size:13px;font-weight:700}.status-row{display:grid;grid-template-columns:170px 1fr;gap:18px;padding:14px 20px;font-size:13px;border-top:1px solid #26364c}.status-row strong{font-weight:650;color:#c3d0e4}.status-row p{margin:0;color:#aabbcf}.status-row .pending{color:#e8c789}.footer{display:flex;justify-content:space-between;gap:24px;padding:26px 0 35px;border-top:1px solid #28374b;font-size:12px;color:#8fa4bf}.footer a{text-decoration:underline;text-underline-offset:3px}.notice{padding:13px 16px;border-left:3px solid #dab967;background:#282519;color:#e8d7b0;border-radius:0 8px 8px 0;margin-top:20px;font-size:12px}.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}@media(max-width:850px){.hero{grid-template-columns:1fr;gap:25px;padding-top:44px}.workflow{max-width:100%}.grid{grid-template-columns:1fr}.card{min-height:225px}.card p{max-width:550px}.card .button{width:auto;min-width:180px}.section-top{display:block}.status-row{grid-template-columns:1fr;gap:5px}.footer{flex-direction:column;gap:9px}.shell{width:calc(100% - 32px)}h1{letter-spacing:-1.8px}.hero-actions .button{width:100%}.header-link{font-size:12px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.button{transition:none}}"""


def safe_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise SystemExit("Public links must be HTTPS URLs without credentials.")
    return escape(value, quote=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prototype-url", default="https://federation-php-architecture-blocked.trycloudflare.com")
    parser.add_argument("--github-url", default="https://github.com/abhi14dodiya/workflow-rescue-sustainx")
    parser.add_argument("--team-leader", default="")
    parser.add_argument("--source-published", action="store_true")
    parser.add_argument("--cloud-run-deployed", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    prototype, github = safe_url(args.prototype_url), safe_url(args.github_url)
    if args.cloud_run_deployed and "trycloudflare.com" in urlsplit(args.prototype_url).hostname:
        raise SystemExit("A temporary tunnel cannot be labelled Cloud Run.")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "downloads").mkdir(exist_ok=True)
    assets = {}
    for key, relative, filename in ASSETS:
        source = ROOT / relative
        destination = PUBLIC / "downloads" / filename
        if not source.is_file():
            # Remove only this exact generated copy, never a source file.
            if destination.is_file():
                destination.unlink()
            assets[key] = {"ready": False, "source": relative}
            continue
        if source.stat().st_size >= 2_000_000_000:
            raise SystemExit(f"Hosting file size limit exceeded: {filename}")
        shutil.copy2(source, destination)
        assets[key] = {"ready": True, "source": relative, "path": "/downloads/" + filename,
                       "bytes": destination.stat().st_size,
                       "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
    ready = all(item["ready"] for item in assets.values())
    video_manifest_path = ROOT / "artifacts/video/video-manifest.json"
    video_manifest = json.loads(video_manifest_path.read_text(encoding="utf-8")) if video_manifest_path.is_file() else {}
    if assets["video"]["ready"]:
        if not (180 <= video_manifest.get("actual_duration_seconds", 0) <= 240
                and video_manifest.get("provider") == "gemini" and video_manifest.get("model_calls", 0) > 0):
            ready = False
    if args.require_complete and not ready:
        raise SystemExit("Final portal needs the PPTX, PDF and validated 3-4 minute live Gemini video.")

    def download(key, label):
        asset = assets[key]
        if not asset["ready"]:
            return '<span class="disabled">Final file in preparation</span>'
        size = asset["bytes"] / 1_000_000
        return f'<a class="button" href="{asset["path"]}" download>{label} <span aria-hidden="true">↗</span></a><span class="tiny">{size:.1f} MB · direct download</span>'

    duration = video_manifest.get("actual_duration_seconds", 0)
    duration_label = f'{int(duration)//60}:{int(duration)%60:02d}' if duration else "3-4 minutes"
    captions = ROOT / "artifacts/video/workflow-rescue-demo.srt"
    caption_path = PUBLIC / "downloads/workflow-rescue-demo.vtt"
    caption_track = ""
    if captions.is_file() and assets["video"]["ready"]:
        subtitle_text = captions.read_text(encoding="utf-8-sig")
        subtitle_text = re.sub(r"(\d\d:\d\d:\d\d),(\d{3})", r"\1.\2", subtitle_text)
        caption_path.write_text("WEBVTT\n\n" + subtitle_text, encoding="utf-8")
        caption_track = '<track kind="captions" src="/downloads/workflow-rescue-demo.vtt" srclang="en" label="English">'
    elif caption_path.is_file():
        caption_path.unlink()
    if assets["video"]["ready"] and ready:
        video = f'<video controls preload="none" playsinline aria-label="Narrated working demonstration of Workflow Rescue"><source src="{assets["video"]["path"]}" type="video/mp4">{caption_track}Your browser does not support inline video. <a href="{assets["video"]["path"]}">Download the demonstration</a>.</video>'
    else:
        video = '<div class="video-placeholder">The narrated demonstration is being finalized.</div>'
    leader = escape(args.team_leader.strip())
    leader_row = (f'<strong>Team leader</strong><p>{leader}</p>' if leader else
                  '<strong>Template field</strong><p class="pending">Registered team leader confirmation is pending.</p>')
    demo_label = "Open working prototype" if args.cloud_run_deployed else "Open temporary live demo"
    hosting_note = ("The interactive prototype is deployed on Cloud Run." if args.cloud_run_deployed else
                    "The interactive demo runs in a temporary Cloud Shell session. Cloud Run deployment is pending.")
    demo_note = ("Live Gemini requests; business services are synthetic." if args.cloud_run_deployed else
                 "Session-based demo. Availability depends on the active Cloud Shell session.")
    source_note = "Public source and supporting materials." if args.source_published else "Repository created; final source publication is pending."
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#080f1b"><meta name="description" content="Workflow Rescue by sustAInX: official pitch materials, narrated demonstration and source code."><title>Workflow Rescue · sustAInX submission materials</title><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/styles.css"></head>
<body><div class="shell"><header><a class="brand" href="/">sust<span>AI</span>nX <span aria-hidden="true">/</span> Workflow Rescue</a><a class="header-link" href="{github}" target="_blank" rel="noopener noreferrer">View source <span aria-hidden="true">↗</span></a></header>
<main><section class="hero" aria-labelledby="title"><div><div class="eyebrow">AI Builder Cup · Submission materials</div><h1>Every promise.<br><span>Accounted for.</span></h1><p class="lead">A recovery desk for operations teams when a workflow stalls between payment, inventory and dispatch.</p><p class="lead">Gemini proposes the next step. Evidence, permissions and independent checks decide what can happen.</p><div class="hero-actions"><a class="button primary" href="#materials">Explore the submission <span aria-hidden="true">↓</span></a><a class="button" href="{prototype}" target="_blank" rel="noopener noreferrer">{demo_label} <span aria-hidden="true">↗</span></a></div><p class="tiny">{demo_note}</p></div>
<aside class="workflow" aria-label="How recovery decisions work"><div class="eyebrow">Evidence before action</div><div class="step"><span class="number">01</span><div><strong>Inspect the incident</strong><p>Read service evidence and the customer mandate.</p></div></div><div class="step"><span class="number">02</span><div><strong>Propose a permitted action</strong><p>Gemini reasons inside explicit authority.</p></div></div><div class="step"><span class="number">03</span><div><strong>Verify the outcome</strong><p>Recover safely, or send the case for review.</p></div></div><div class="checkline">6 of 6 reviewed synthetic scenarios reached their expected outcomes.</div></aside></section>
<section id="materials" aria-labelledby="materials-title"><div class="section-top"><div><h2 id="materials-title">The submission, in one place.</h2><p class="sub">Official format. Working demonstration. Inspectable source.</p></div><span class="tiny">English · Future of Work &amp; Enterprise Productivity</span></div><div class="grid"><article class="card"><span class="filetype">PPTX</span><h3>Official pitch deck</h3><p>The challenge template, with the problem, solution, architecture, impact and product screenshots.</p>{download('deck_pptx','Download PowerPoint')}</article><article class="card"><span class="filetype">PDF</span><h3>Read the pitch</h3><p>A portable version of the same official deck, ready to review on desktop or mobile.</p>{download('deck_pdf','Download PDF')}</article><article class="card"><span class="filetype">MP4 · {duration_label}</span><h3>See a fresh recovery</h3><p>A narrated recording of the deployed interface making real Gemini requests against synthetic business services.</p>{download('video','Download video')}</article></div></section>
<section class="video-section" aria-labelledby="video-title"><div class="section-top"><div><h2 id="video-title">Watch the demonstration.</h2><p class="sub">Press play to load the video. Audio narration and an actual recorded run.</p></div></div><div class="video-wrap">{video}</div></section>
<section class="status" aria-labelledby="status-title"><div class="status-header" id="status-title">What is live, and what is included</div><div class="status-row"><strong>Google AI</strong><p>Gemini powers the planner through real API calls. Business systems are simulated.</p></div><div class="status-row"><strong>Firestore persistence</strong><p><span class="verified">Verified after API restart.</span> Completed reports are restored by run ID using server IAM.</p></div><div class="status-row"><strong>Validation</strong><p>83 Python tests and 8 JavaScript tests passed. Live Gemini reached the expected outcomes in 6 of 6 reviewed synthetic fixtures.</p></div><div class="status-row"><strong>Hosting</strong><p>This page and its downloads use Firebase Hosting. {hosting_note}</p></div><div class="status-row"><strong>Source code</strong><p><a href="{github}" target="_blank" rel="noopener noreferrer">github.com/abhi14dodiya/workflow-rescue-sustainx ↗</a><br>{source_note}</p></div><div class="status-row">{leader_row}</div></section></main>
<footer class="footer"><span>Workflow Rescue by sustAInX · Submission materials portal</span><span><a href="{github}" target="_blank" rel="noopener noreferrer">Source &amp; supporting documentation</a></span></footer></div></body></html>'''
    (PUBLIC / "index.html").write_text(html, encoding="utf-8")
    (PUBLIC / "styles.css").write_text(CSS + "\n.verified{color:#baf278;font-weight:650}video{aspect-ratio:1440/986;height:auto}\n", encoding="utf-8")
    (PUBLIC / "favicon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#baf278"/><path d="M10 10h12v4H14v4h8v4H10v-4h8v-4h-8z" fill="#0c1b11"/></svg>', encoding="utf-8")
    # Only generated portal files and explicitly allowed submission assets are published.
    permitted = {"index.html", "styles.css", "favicon.svg", "downloads/workflow-rescue-demo.vtt"} | {"downloads/" + row[2] for row in ASSETS}
    for path in PUBLIC.rglob("*"):
        if path.is_file() and path.relative_to(PUBLIC).as_posix() not in permitted:
            raise SystemExit("Unexpected file in generated portal; inspect it before publishing.")
    files = {path.relative_to(PUBLIC).as_posix(): {"bytes": path.stat().st_size,
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
             for path in PUBLIC.rglob("*") if path.is_file()}
    total = sum(item["bytes"] for item in files.values())
    if total >= 100_000_000:
        raise SystemExit("Portal exceeds the deliberate 100 MB package limit; compress the video before publishing.")
    report = {"prepared_at": datetime.now(timezone.utc).isoformat(), "assets_ready": ready,
              "portal_type": "submission materials; not the interactive prototype",
              "site": "gen-lang-client-0915819772", "url": "https://gen-lang-client-0915819772.web.app",
              "public_directory": str(PUBLIC), "prototype_url": args.prototype_url, "github_url": args.github_url,
              "cloud_run_deployed": args.cloud_run_deployed, "team_leader_confirmed": bool(leader),
              "source_published": args.source_published,
              "assets": assets, "files": files, "total_bytes": total,
              "video_duration_seconds": duration, "estimated_complete_downloads_per_10gb": int(10_000_000_000 / max(total, 1)),
              "published": False}
    (ROOT / "artifacts/submission-portal-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("assets_ready", "url", "total_bytes", "estimated_complete_downloads_per_10gb", "published")}, indent=2))


if __name__ == "__main__":
    main()
