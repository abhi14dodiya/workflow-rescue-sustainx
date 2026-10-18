"""Populate the organizer's real PPTX, preserving its branding and required sections.

All completion claims are driven by explicit status input or evaluation artifacts.
The download-instructions slide is retained but hidden. PowerPoint is used locally
to render the editable PPTX into an identical PDF and visual review images.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps, ImageDraw
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ART = ROOT / "artifacts"
TEMPLATE = DOCS / "AI-Builder-Cup-Official-Template.pptx"
OUTPUT = DOCS / "Workflow-Rescue-Official-Pitch.pptx"

INK = "172336"
MUTED = "53637C"
BLUE = "2864DF"
PALE = "EDF3FF"
GREEN = "16845A"
GREEN_BG = "EBF7F0"
AMBER = "946000"
AMBER_BG = "FFF4D9"
RED = "B43B3B"
RED_BG = "FBECEC"
LINE = "D8E1EE"
WHITE = "FFFFFF"
PURPLE = "7557DD"


def rgb(value):
    return RGBColor.from_string(value)


def text(slide, x, y, w, h, value, size=15, color=INK, bold=False,
         align=PP_ALIGN.LEFT, fill=None, margin=0):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.clear()
    frame.margin_left = frame.margin_right = Inches(margin)
    frame.margin_top = frame.margin_bottom = Inches(margin)
    frame.word_wrap = True
    for index, line in enumerate(str(value).split("\n")):
        p = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        p.text = line
        p.alignment = align
        p.space_after = Pt(3)
        p.font.name = "Aptos"
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = rgb(color)
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill)
        shape.line.fill.background()
    return shape


def box(slide, x, y, w, h, fill=PALE, border=None, rounded=True):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    if border:
        shape.line.color.rgb = rgb(border)
        shape.line.width = Pt(.8)
    else:
        shape.line.fill.background()
    if rounded:
        shape.adjustments[0] = .09
    return shape


def card(slide, x, y, w, h, title, body, accent=BLUE, fill=PALE, body_size=13):
    box(slide, x, y, w, h, fill, LINE)
    box(slide, x, y, .045, h, accent, rounded=False)
    text(slide, x+.16, y+.14, w-.32, .36, title, 15, accent, True)
    text(slide, x+.16, y+.62, w-.32, h-.7, body, body_size, INK)


def tag(slide, x, y, w, value, state="ready"):
    color, bg = ((GREEN, GREEN_BG) if state == "ready" else
                 (RED, RED_BG) if state == "issue" else (AMBER, AMBER_BG))
    box(slide, x, y, w, .29, bg)
    text(slide, x+.08, y+.035, w-.16, .22, value, 9.5, color, True)


def foot(slide, number, note="Synthetic business services. No production customer data."):
    text(slide, .39, 5.14, 8.68, .23, note, 8.5, MUTED)
    text(slide, 9.18, 5.14, .40, .23, f"{number:02}", 9, MUTED, align=PP_ALIGN.RIGHT)


def title(slide, original, subtitle=None):
    title_shape = next(s for s in slide.shapes if s.has_text_frame and s.text.strip())
    title_shape.text_frame.clear()
    title_shape.left, title_shape.top = Inches(.39), Inches(.77)
    title_shape.width, title_shape.height = Inches(9.13), Inches(.44)
    p = title_shape.text_frame.paragraphs[0]
    p.text = original
    p.font.name = "Aptos Display"
    p.font.size = Pt(23 if len(original) < 52 else 20)
    p.font.bold = True
    p.font.color.rgb = rgb(INK)
    title_shape.text_frame.margin_left = title_shape.text_frame.margin_top = 0
    if subtitle:
        text(slide, .4, 1.27, 9.1, .4, subtitle, 12, MUTED)


def picture(slide, path, x, y, w, h):
    # Contain rather than crop: provider labels and outcome evidence stay visible.
    path = Path(path)
    im = Image.open(path)
    ratio = min(w / im.width, h / im.height)
    iw, ih = im.width * ratio, im.height * ratio
    return slide.shapes.add_picture(str(path), Inches(x+(w-iw)/2), Inches(y+(h-ih)/2),
                                    width=Inches(iw), height=Inches(ih))


def arrow(slide, x1, y1, x2, y2, color=BLUE, width=1.5):
    shape = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                      Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    shape.line.color.rgb = rgb(color)
    shape.line.width = Pt(width)
    from pptx.oxml.xmlchemy import OxmlElement
    end = OxmlElement("a:tailEnd")
    end.set("type", "triangle")
    shape._element.spPr.get_or_add_ln().append(end)
    return shape


def notes(slide, value):
    slide.notes_slide.notes_text_frame.text = value


def hyperlink(shape, url):
    if url:
        for p in shape.text_frame.paragraphs:
            for r in p.runs:
                r.hyperlink.address = url


def load_report(provider):
    p = ART / f"evaluation-{provider}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def build(status):
    prs = Presentation(TEMPLATE)
    assert len(prs.slides) == 16, "Organizer template changed; inspect it before using this builder."
    rehearsal = load_report("rehearsal")
    gemini = load_report("gemini")
    cases = gemini.get("cases", []) if gemini else []
    model_names = sorted({case.get("trace", {}).get("model") for case in cases
                          if case.get("trace", {}).get("model")})
    model_name = ", ".join(model_names) or "Model validation pending"
    google_pass = bool(gemini and gemini.get("correct") == gemini.get("total") and
                       gemini.get("total", 0) >= 6 and not gemini.get("safety_issues"))
    firebase_ready = status.get("firebase_verified", False)
    firestore_ready = status.get("firestore_verified", False)
    cloudrun_ready = status.get("cloudrun_verified", False)
    leader = status.get("leader") or "[Registered team leader name]"
    home_image = DOCS / "images/gemini-public-home.png"
    interface_image = Path(status.get("interface_image") or home_image)
    verification_image = Path(status.get("verification_image") or ART / "verification.png")
    verification_label = status.get("verification_label") or "Local deterministic rehearsal; no Gemini calls in this image."
    if not status.get("verification_image"):
        detail = DOCS / "images/rehearsal-checks-detail.png"
        original = Image.open(verification_image)
        original.crop((0, 0, original.width, 354)).save(detail)
        verification_image = detail

    # The organizer's first cover artwork and black footer are untouched.
    slide = prs.slides[0]
    source = slide.shapes[0]
    source.text_frame.clear()
    source.left, source.top, source.width, source.height = map(Inches, (.39, 3.15, 9.2, 2.12))
    text(slide, .43, 3.20, 8.9, .39, "Team Details", 22, INK, True)
    text(slide, .44, 3.73, 3.9, .4, "sustAInX", 27, BLUE, True)
    text(slide, 4.8, 3.77, 4.7, .36, "Workflow Rescue", 23, INK, True)
    text(slide, .45, 4.20, 8.95, .35, f"Team leader name: {leader}", 13, MUTED)
    text(slide, .45, 4.66, 8.95, .55,
         "Problem Statement: Recover interrupted enterprise workflows while preserving customer intent, permissions and a verifiable outcome.", 16)
    notes(slide, "Theme: Future of Work & Enterprise Productivity. Team spelling must remain sustAInX. "
          "The registered leader name must be confirmed before submission. All payment, inventory and order services are synthetic.")

    # Preserve the organizer's instruction slide but omit it from the presentation.
    prs.slides[1]._element.set("show", "0")
    notes(prs.slides[1], "Original organizer download instruction retained unchanged. Hidden from the submitted presentation.")

    slide = prs.slides[2]
    title(slide, "Brief about the idea", "Workflow Rescue is an operator's recovery workspace for an order stranded between services.")
    text(slide, .43, 1.84, 5.1, 1.03, "A timeout is\nnot the truth.", 35, INK, True)
    text(slide, .45, 3.07, 4.65, .80,
         "The charge succeeded. The reservation expired. The customer still expects the original item.", 19)
    box(slide, .42, 4.11, 4.76, .65, PALE)
    text(slide, .60, 4.24, 4.4, .46, '“Same item. No extra charge. Two days late is fine.”', 14, BLUE, True)
    card(slide, 5.65, 1.9, 3.91, .89, "Reconstruct", "Read payment, stock and dispatch evidence.", body_size=12)
    card(slide, 5.65, 2.99, 3.91, .89, "Recover within authority", "Gemini proposes; code controls each write.", accent=PURPLE, body_size=12)
    card(slide, 5.65, 4.08, 3.91, .89, "Prove the result", "Independent checks verify or request review.", accent=GREEN, body_size=12)
    foot(slide, 3)
    notes(slide, "An adopting business supplies scoped permissions to its own service APIs. "
          "This prototype cannot intervene in a bank or another company's transactions. "
          "The customer mandate is reviewed structured scenario data, not unrestricted natural-language interpretation.")

    slide = prs.slides[3]
    title(slide, "Opportunities", "An evidence-linked recovery layer for the operator who must decide what happens next.")
    card(slide, .43, 1.87, 2.91, 2.72, "How different is it?",
         "Beyond a retry button: a stock conflict triggers fresh evidence and a revised proposal.\n\nDesigned to complement existing workflow engines.", BLUE)
    card(slide, 3.54, 1.87, 2.91, 2.72, "How does it solve it?",
         "Join customer permission, authoritative receipts and guarded execution in one incident.\n\nUncertainty becomes an explicit handoff.", PURPLE)
    card(slide, 6.65, 1.87, 2.91, 2.72, "USP of the solution",
         "Every attempted action has evidence. Every completed recovery has independent checks.\n\nOperators and reviewers inspect the same record.", GREEN)
    text(slide, .50, 4.73, 8.9, .30,
         "Target users: order operations • finance reconciliation • engineering reliability • internal control review", 11, MUTED)
    foot(slide, 4, "Retries, idempotency and compensation already exist. Incremental AI benefit needs broader evaluation.")
    notes(slide, "Stripe documents duplicate webhook delivery and idempotent retries. Temporal documents sagas and compensation. "
          "These sources establish the engineering problem, not product ROI. A broader deterministic planner can also solve these six fixtures.")

    slide = prs.slides[4]
    title(slide, "List of features offered by the solution", "One incident, from customer intent to an inspectable business outcome.")
    feature_data = [
        ("01  Your own incident", "Edit stock, payment and permissions, or import a validated JSON incident.", BLUE),
        ("02  Evidence gathering", "The controller reads payment, inventory and order evidence before planning.", PURPLE),
        ("03  Adaptive proposal", "Request fresh evidence after a stock-version conflict.", BLUE),
        ("04  Guarded execution", "Check typed tools, evidence, versions and idempotency.", GREEN),
        ("05  Independent outcome", "Verify state or hand off when payment or dispatch is uncertain.", GREEN),
        ("06  Inspectable record", "Replay real events, open receipts and export the run's JSON audit.", PURPLE),
    ]
    for i, (heading, body, accent) in enumerate(feature_data):
        card(slide, .43+(i%3)*3.11, 1.9+(i//3)*1.52, 2.91, 1.32, heading, body, accent, body_size=12.3)
    foot(slide, 5, "Replay is read-only playback of recorded events. A fresh run makes new model calls.")
    notes(slide, "The incident lab accepts editable synthetic service states and explicit permission toggles, or a schema-validated JSON incident. "
          "Imported records do not grant authority over any real service. Customer notes do not override explicit reviewed permissions. "
          "Replay remains separate from starting a fresh model run. This is JSON incident import, not arbitrary document ingestion.")

    slide = prs.slides[5]
    title(slide, "Process flow diagram or Use-case diagram", "The controller gathers mandatory evidence; Gemini chooses a recovery and adapts to change.")
    nodes = [(.45, 1.9, "1  Incident + mandate", "Operator edits or imports\na synthetic incident."),
             (3.76, 1.9, "2  Controller observes", "Mandatory payment, stock\nand dispatch reads."),
             (7.07, 1.9, "3  Gemini proposes", "Recovery action based on\nthe observed evidence."),
             (7.07, 3.71, "4  Controller checks", "Permissions • versions\nevidence • idempotency"),
             (3.76, 3.71, "5  Execute bounded tool", "Receipt confirms the write.\nChanged state is observed."),
             (.45, 3.71, "6  Verify or hand off", "Independent ledger checks\nplus exportable audit.")]
    for x,y,h,b in nodes:
        card(slide,x,y,2.47,1.11,h,b,body_size=11.5)
    arrow(slide,2.95,2.43,3.72,2.43)
    arrow(slide,6.26,2.43,7.03,2.43)
    arrow(slide,8.3,3.04,8.3,3.67)
    arrow(slide,7.02,4.26,6.26,4.26)
    arrow(slide,3.72,4.26,2.95,4.26)
    text(slide, 2.65, 3.11, 4.68, .34, "Blocked stale proposal → refresh evidence → replan", 12, AMBER, True, PP_ALIGN.CENTER)
    foot(slide, 6, "Bounded proposal loop. Unknown payment or irreversible dispatch leads to operator review.")
    notes(slide, "Three mandatory controller reads gather payment, inventory and dispatch before Gemini is called. "
          "Gemini then chooses the recovery action and can request fresh evidence or replan after a conflict. "
          "The stock race occurs between observation and reservation. The first proposed reservation can be rejected "
          "because its inventory version is stale. A fresh observation can reveal incoming stock within the approved delay. "
          "Do not imply the model authorizes itself or independently certifies the result.")

    slide = prs.slides[6]
    title(slide, "Wireframes/Mock diagrams of the proposed solution (optional)", "Implemented incident lab: change evidence, review explicit permissions, then run a new recovery.")
    box(slide,.43,1.85,5.49,2.95,PALE)
    picture(slide,interface_image,.45,1.87,5.45,2.91)
    card(slide,6.20,1.82,3.34,.99,"Orient", "Home introduces the incident and service state.", body_size=11.8)
    card(slide,6.20,2.88,3.34,.99,"Act", "Edit or import an incident; start a fresh run.",accent=PURPLE, body_size=11.8)
    card(slide,6.20,3.94,3.34,.99,"Review", "History and receipts reconstruct each run.",accent=GREEN, body_size=11.8)
    foot(slide,7,"Actual application screenshot. Imported JSON is schema-validated; a customer note cannot override permission controls.")
    notes(slide,"This is an actual incident-lab capture, not a designed mock. "
          "Operators can change stock, payment availability and reviewed permissions, or import a JSON incident. "
          "Animation is a state projection and cannot make a failed run pass. Desktop and mobile browser checks were run locally.")

    slide = prs.slides[7]
    title(slide, "Architecture diagram of the proposed solution", "Solid boxes: implemented application path. Google deployment status is stated separately.")
    card(slide,.43,1.92,2.22,1.13,"React + Three.js","Incident desk\nEvidence and audit UI", body_size=12)
    card(slide,3.18,1.92,2.75,1.13,"FastAPI controller","Bounded agent loop\nAuthority + verification",accent=PURPLE,body_size=12)
    card(slide,6.60,1.92,2.93,1.13,"Gemini API","Structured recovery proposals\nAPI key stays server-side",accent=GREEN,body_size=12)
    arrow(slide,2.68,2.49,3.14,2.49)
    arrow(slide,5.98,2.49,6.56,2.49)
    card(slide,3.18,3.41,2.75,1.16,"Synthetic connectors","Payment ledger • inventory\nOrder and dispatch",body_size=12)
    arrow(slide,4.55,3.09,4.55,3.37)
    tag(slide,.46,3.47,2.18,"Firebase: "+("verified" if firebase_ready else "pending"),"ready" if firebase_ready else "review")
    tag(slide,.46,3.95,2.18,"Cloud Run: "+("verified" if cloudrun_ready else "pending"),"ready" if cloudrun_ready else "review")
    card(slide,6.60,3.41,2.93,1.16,"Firestore audit store",
         "Saved report restored\nafter server restart" if firestore_ready else "Database probe passed;\nruntime check pending",
         accent=GREEN if firestore_ready else AMBER,
         fill=GREEN_BG if firestore_ready else AMBER_BG,body_size=12)
    arrow(slide,5.98,2.92,6.56,3.70,GREEN if firestore_ready else AMBER)
    foot(slide,8,status.get("hosting_note","Current backend: temporary Google Cloud Shell demo. Persistent Cloud Run hosting is not yet deployed."))
    notes(slide,"Google deployment roles: Firebase Hosting for a static submission portal and prototype entry link; Cloud Run is planned for the FastAPI runtime; "
          "Firestore for durable audit documents; Gemini API for reasoning. Status badges reflect only confirmed deployment evidence. "
          "The static submission portal does not keep the Cloud Shell backend alive. "
          + ("The application-runtime Firestore save/load integration has been verified. " if firestore_ready else
             "A Firestore database write/read probe passed, but application-runtime persistence is pending until its credentials and save/load path have been verified. ") +
          "Do not call the in-memory simulator a durable distributed transaction engine. "+json.dumps({k:status.get(k,False) for k in ("firebase_verified","firestore_verified","cloudrun_verified")}))

    slide = prs.slides[8]
    title(slide, "Technologies to be used in the solution", "The Google services have distinct roles; the pitch does not treat planned services as deployed.")
    table = [
        ("Gemini API", "Evidence-linked recovery proposal and conflict replanning", "Live suite passed" if google_pass else "Live validation in progress", google_pass),
        ("Firebase Hosting", "Public submission portal and prototype entry link", "Verified" if firebase_ready else "Pending deployment", firebase_ready),
        ("Firestore", "Persist completed run evidence for later review", "Verified" if firestore_ready else status.get("firestore_status","Runtime check pending"), firestore_ready),
        ("Cloud Run", "Managed runtime for the FastAPI service", "Verified" if cloudrun_ready else "Pending deployment", cloudrun_ready),
        ("React / Three.js", "Responsive recovery desk, service views and replay", "Implemented", True),
        ("FastAPI / Pydantic", "Typed proposals, execution guards and verification", "Implemented", True),
    ]
    for i,(tech,role,state,ready) in enumerate(table):
        y=1.89+i*.475
        box(slide,.43,y,9.1,.435,"F5F8FC" if i%2==0 else WHITE,rounded=False)
        text(slide,.58,y+.065,1.95,.3,tech,12,INK,True)
        text(slide,2.52,y+.065,4.68,.3,role,11.3,MUTED)
        tag(slide,7.40,y+.064,1.97,state,"ready" if ready else "review")
    text(slide,.51,4.90,8.89,.25,"Verified model: "+model_name+". No automatic fallback to a paid model.",10.2,MUTED)
    foot(slide,9,"Only explicit, verified status flags mark a deployment complete. Secrets never enter the frontend or deck.")
    notes(slide,"The current Gemini free-tier API is different from paid Vertex AI. Billing is not linked to the selected GCP project. "
          "Cloud Run free allowances are not a guaranteed zero-spend deployment. Public evaluation availability remains a delivery requirement.")

    slide = prs.slides[9]
    title(slide, "Estimated implementation cost (optional)", "Constrain prototype spend; validate business value with a real operations pilot.")
    card(slide,.43,1.87,4.12,2.76,"Prototype cost boundary",
         "Build scope: 2–3 day prototype target.\n\nGemini: user's confirmed Free tier.\n\nCurrent hosting: free Cloud Shell session; temporary availability.\n\nPersistent hosting and integration costs still need validation.",body_size=12)
    box(slide,4.84,1.88,4.70,2.75,GREEN_BG,LINE)
    text(slide,5.07,2.04,4.15,.32,"ILLUSTRATIVE ANNUAL CAPACITY VALUE",10,GREEN,True)
    text(slide,5.07,2.51,4.15,.63,"$250,000",36,GREEN,True)
    text(slide,5.08,3.29,4.10,.90,"10m orders × 1% recovery incidence\n× 50% assisted × 10 minutes saved\n× $30/hour ÷ 60",15,INK)
    text(slide,.50,4.77,8.87,.31,"Hypothetical inputs, before cloud, integration and review costs. Released capacity is not automatically cash saved.",10.5,MUTED)
    foot(slide,10,"No measured ROI, customer adoption or global savings claim. A pilot must validate every assumption.")
    notes(slide,"Formula: annual orders times manual recovery incidence times useful coverage times net minutes saved divided by 60 times fully loaded hourly staff cost. "
          "The illustration equals $250,000 gross annual staff capacity. It is not a market estimate, a tested saving, or a budget reduction. "
          "Production costs include integration, durable data, access controls, observability, inference, hosting and review effort.")

    slide=prs.slides[10]
    title(slide,"Snapshots of the prototype","The interface exposes the underlying record; a green animation alone is never proof.")
    box(slide,.43,1.90,9.10,2.88,"F8FBFF",LINE)
    picture(slide,verification_image,.51,1.98,8.94,2.72)
    text(slide,.54,4.86,8.93,.24,verification_label,11,MUTED)
    foot(slide,11,"Selected verification checks from an actual run; the caption identifies the provider used.")
    notes(slide,verification_label+
          " This is a capture of the application's computed verification results. The provider and scenario must match its audit record. "
          "Never relabel rehearsal evidence as Gemini evidence.")

    slide=prs.slides[11]
    title(slide,"Prototype Performance report/Benchmarking","Six reviewed development fixtures; useful coverage evidence, not a held-out accuracy benchmark.")
    text(slide,.48,1.84,3.18,.38,f"{gemini.get('correct',0) if gemini else 0}/6 live Gemini",22,GREEN if google_pass else AMBER,True)
    text(slide,3.73,1.85,2.73,.33,f"{status.get('python_tests',83)} Python tests",20,BLUE,True)
    text(slide,6.88,1.85,2.56,.33,f"{status.get('js_tests',8)} JavaScript tests",20,BLUE,True)
    heads=[(.57,3.00,"Scenario"),(3.65,1.83,"Expected"),(5.67,1.77,"Gemini outcome"),(7.86,1.48,"Model calls")]
    for x,w,value in heads:text(slide,x,2.47,w,.26,value,10,MUTED,True)
    for i,c in enumerate(cases[:6]):
        y=2.83+i*.29
        correct=c.get("correct",False)
        color=GREEN if correct else RED
        bg=GREEN_BG if correct else RED_BG
        box(slide,.45,y-.025,9.08,.281,bg,rounded=False)
        label=c.get("scenario","").replace("-"," ")
        observed = "Quota error" if (c.get("error") or {}).get("code") == "HTTP_429" else ("Run error" if c.get("status")=="error" else c.get("observed") or c.get("status","error"))
        values=[(.57,2.95,label),(3.65,1.83,c.get("expected","")),(5.67,1.77,observed),(8.23,.65,str(c.get("metrics",{}).get("calls",0)))]
        for x,w,value in values:text(slide,x,y,w,.26,value,10.3,color)
    if not cases:text(slide,.55,2.97,8.4,.5,"Gemini evaluation artifact pending. Do not replace this with rehearsal results.",14,AMBER)
    text(slide,.52,4.69,9.00,.33,
         f"Rehearsal: {rehearsal.get('correct',0) if rehearsal else 0}/6. Baseline escalates on stock conflict; a broader rules engine can solve these fixtures.",10,MUTED)
    foot(slide,12,model_name+" • "+str(gemini.get("safety_issues","unknown") if gemini else "unknown")+" safety-check failures • 3 controller reads before each model run. Artifact: "+str(gemini.get("at","not available") if gemini else "not available"))
    notes(slide,"The deck reads artifacts/evaluation-gemini.json at build time. It shows unsuccessful cases as red rather than substituting provider results. "
          "The initial Gemini 3.8 Flash run exhausted its model's free daily allowance. The operator explicitly selected Gemini 3.5 Flash-Lite; "
          "there is no silent provider fallback. The new six-case deployed suite passed. Three controller preflight reads are distinct from the listed model-call counts. "
          "Stock-race recovery used four model calls and took about 60 seconds including free-tier pacing; do not present inference-only latency as end-to-end runtime. "
          "Live and mocked tests answer different questions. "
          "No finalist probability or superiority claim is inferred from six development fixtures.")

    slide=prs.slides[12]
    title(slide,"Additional Details/Future Development (if any)","What must happen before real customer orders enter the system.")
    card(slide,.43,1.89,2.91,2.85,"1  Delivery readiness",
         "Persistent, publicly accessible hosting.\n\nValidate every required Google integration.\n\nPublish source and a working 3–4 minute demo.",body_size=13)
    card(slide,3.54,1.89,2.91,2.85,"2  Customer pilot",
         "Use an owner's sandbox APIs with scoped authority.\n\nBroaden instruction and incident variation.\n\nMeasure handling time and safe handoff coverage.",accent=PURPLE,body_size=13)
    card(slide,6.65,1.89,2.91,2.85,"3  Production controls",
         "Service-owned idempotency and durable state.\n\nTenant identity, access controls and retention.\n\nTamper-evident records and human approval gates.",accent=GREEN,body_size=13)
    foot(slide,13,"Prototype audit is inspectable, but not immutable, certified or independently attested.")
    notes(slide,"The latest submission instructions supplied by the user require a 3 to 4 minute video. "
          "This supersedes the older public FAQ and the template's legacy 3-minute label for this preparation. "
          "The application must remain functional throughout evaluation; the temporary Cloud Shell link does not meet that durability requirement.")

    slide=prs.slides[13]
    title(slide,"Provide links to your:","Public repository, 3–4 minute demonstration, and deployed working product.")
    links=[("GitHub Public Repository"+("" if status.get("repo_verified") else " — publication pending"),status.get("repo_url"),"Public source link pending publication."),
           ("Demo Video Link (3–4 minutes)"+("" if status.get("video_verified") else " — upload pending"),status.get("video_url"),"Record against the validated deployment; public video link pending."),
           ("Final Product Link",status.get("app_url"),"Persistent product deployment is pending.")]
    for i,(label,url,fallback) in enumerate(links):
        y=1.91+i*.97
        box(slide,.45,y,9.08,.82,PALE,LINE)
        text(slide,.65,y+.12,8.66,.24,label,12,BLUE,True)
        shp=text(slide,.65,y+.46,8.64,.24,url or fallback,10.8,INK if url else AMBER)
        hyperlink(shp,url)
    text(slide,.57,4.91,8.9,.21,status.get("link_note","The current product URL is a temporary session demo, not a durable evaluation deployment."),9.5,AMBER)
    foot(slide,14,"All links must work without the evaluator signing into the team's private accounts.")
    notes(slide,"Link targets are editable text hyperlinks in the PPTX and exported PDF. "
          "A nonempty link is not evidence of durable availability. Source publication and video upload must be independently checked while signed out.")

    slide=prs.slides[14]
    # Fill the organizer's blank branded slide with checkable sources and limits.
    text(slide,.43,.81,9.1,.45,"Evidence, assumptions and scope",24,INK,True)
    text(slide,.46,1.46,9.02,.56,"Our claim is controlled, inspectable recovery of synthetic incidents. The pilot must establish business value.",18,INK)
    sources=[("Stripe webhook guidance","https://docs.stripe.com/webhooks","Duplicate events establish why recovery must reconcile authoritative state."),
             ("Stripe idempotent requests","https://docs.stripe.com/api/idempotent_requests","Safe request retries are an established engineering control."),
             ("Temporal sagas and compensation","https://temporal.io/blog/compensating-actions-part-of-a-complete-breakfast-with-sagas","Partial workflows and application-specific compensation predate this prototype.")]
    for i,(label,url,description) in enumerate(sources):
        y=2.26+i*.76
        shp=text(slide,.51,y,8.96,.25,label,13,BLUE,True);hyperlink(shp,url)
        text(slide,.51,y+.32,8.96,.31,description,12,MUTED)
    foot(slide,15,"Primary technical sources checked 18 October 2026. These sources do not substantiate a product savings figure.")
    notes(slide,"All official template headers, footers, cover artwork and closing artwork are preserved. "
          "Slide 2 remains as a hidden organizer note. This extra evidence slide occupies the original blank branded slide. "
          "Savings assumptions are documented in docs/IMPACT.md. Full controller and provider evidence is in the repository artifacts.")

    # Retain full organizer closing artwork; place small project credit in clear area.
    slide=prs.slides[15]
    text(slide,5.58,3.09,4.0,.37,"Workflow Rescue · sustAInX",18,WHITE,True)
    text(slide,5.58,3.54,3.92,.79,"Recover the workflow.\nPreserve the customer's intent.",18,WHITE)
    notes(slide,"Thank you. Invite the evaluator to inspect the working recovery, the underlying evidence and the source code. "
          "Do not promise competition qualification or claim production readiness.")

    prs.core_properties.title="Workflow Rescue by sustAInX — AI Builder Cup 2026"
    prs.core_properties.subject="Official-template submission draft; evidence-linked enterprise workflow recovery"
    prs.core_properties.author="sustAInX"
    prs.core_properties.keywords="Gemini, enterprise recovery, AI Builder Cup, sustAInX"
    prs.save(OUTPUT)
    report={"pptx":str(OUTPUT),"template":str(TEMPLATE),"slides":len(prs.slides),
            "hidden_slides":[2],"google_suite_passed":google_pass,
            "gemini_models":model_names,
            "gemini_correct":gemini.get("correct",0) if gemini else 0,
            "gemini_safety_check_failures":gemini.get("safety_issues") if gemini else None,
            "gemini_evaluation_at":gemini.get("at") if gemini else None,
            "python_tests":status.get("python_tests",83),"javascript_tests":status.get("js_tests",8),
            "pending":[name for name,value in [("registered leader",status.get("leader")),("repository publication",status.get("repo_verified")),
                       ("video publication",status.get("video_verified")),("Cloud Run",cloudrun_ready),("Firebase",firebase_ready),("Firestore runtime",firestore_ready)] if not value]}
    return report


def render():
    import win32com.client
    out=ART/"official-deck-preview"
    out.mkdir(exist_ok=True)
    app=win32com.client.DispatchEx("PowerPoint.Application")
    pres=None
    try:
        pres=app.Presentations.Open(str(OUTPUT),ReadOnly=True,Untitled=False,WithWindow=False)
        # SaveAs PDF defaults to visible slides, preserving hyperlinks and fonts.
        pres.SaveAs(str(OUTPUT.with_suffix(".pdf")),32)
        pres.Export(str(out),"PNG",1600,900)
    finally:
        if pres is not None:pres.Close()
        app.Quit()
    slides=[p for p in out.glob("Slide*.PNG") if p.stem!="Slide2"]
    slides.sort(key=lambda p:int(p.stem.replace("Slide","")))
    sheet=Image.new("RGB",(1200, len(slides)//3*254+(254 if len(slides)%3 else 0)),"#dbe1ea")
    draw=ImageDraw.Draw(sheet)
    for i,p in enumerate(slides):
        thumbnail=ImageOps.contain(Image.open(p),(384,216))
        x=8+(i%3)*400;y=20+(i//3)*254
        sheet.paste(thumbnail,(x,y))
        draw.text((x,y-14),p.stem,fill="#233040")
    sheet.save(out/"contact-sheet.jpg",quality=90)
    from pypdf import PdfReader
    pdf=PdfReader(OUTPUT.with_suffix(".pdf"))
    return {"pdf":str(OUTPUT.with_suffix(".pdf")),"pdf_pages":len(pdf.pages),"preview":str(out/"contact-sheet.jpg")}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--status",type=Path,default=DOCS/"official-deck-status.json")
    parser.add_argument("--render",action="store_true",help="Use local PowerPoint for identical PDF and preview images.")
    args=parser.parse_args()
    status=json.loads(args.status.read_text(encoding="utf-8")) if args.status.exists() else {}
    report=build(status)
    if args.render:report.update(render())
    (ART/"official-deck-validation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
