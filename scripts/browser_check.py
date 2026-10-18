"""Browser verification of React, actual recovery, and optional 3D interaction."""
import argparse
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)
EDGES = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"), Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]

def seek(page, index):
    slider = page.locator('#replay-cursor')
    slider.focus()
    slider.press('Home')
    for _ in range(index + 1):
        slider.press('ArrowRight')
    expect(slider).to_have_value(str(index))

def use_rehearsal(page):
    page.locator('#provider-select').select_option('rehearsal')
    page.evaluate("() => window.scrollTo({top:0,behavior:'instant'})")

def settle_view(page):
    # Native smooth scroll and the damped camera settle independently of React state.
    page.evaluate("""() => new Promise(resolve => {
      let lastY=window.scrollY, lastRotation=0, stable=0, frames=0;
      const tick=()=>{
        const rotation=Number(document.querySelector('canvas[data-scene]')?.dataset.rotation || 0);
        stable=Math.abs(window.scrollY-lastY)<.2 && Math.abs(rotation-lastRotation)<.003 ? stable+1 : 0;
        lastY=window.scrollY; lastRotation=rotation;
        if(stable>12 || ++frames>240) resolve(); else requestAnimationFrame(tick);
      }; tick();
    })""")

def main(live_provider=None, base_url='http://127.0.0.1:8080'):
    base_url = base_url.rstrip('/')
    errors = []
    with sync_playwright() as p:
        executable = next((str(e) for e in EDGES if e.exists()), None)
        browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
        page = browser.new_page(viewport={"width":1440,"height":1000}, device_scale_factor=1)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text[:500]) if m.type == "error" else None)
        starts = []
        page.on('request', lambda r: starts.append(r.url) if r.method == 'POST' and r.url.endswith('/api/runs') else None)
        page.goto(base_url,wait_until="networkidle")
        page.locator("#scenario-select option").first.wait_for(state="attached")
        assert page.locator("#scenario-select option").count() == 6
        use_rehearsal(page)
        assert "No AI model" in page.locator("#provider-notice").inner_text()
        assert 'sustAInX' in page.locator('.site-header .brand-credit').inner_text()
        assert page.locator('#recovery').count() == page.locator('#view-history').count() == page.locator('#view-design').count() == 1
        nav = page.get_by_role('navigation', name='Main navigation', exact=True)
        for label in ('Home', 'Workspace', 'History', 'How it works'):
            expect(nav.get_by_role('button', name=label, exact=label != 'History')).to_be_visible()
        # Navigation and the empty state never start a model call.
        nav.get_by_role('button', name='History').click()
        page.locator('#history-start').click()
        expect(page.locator('#main')).to_have_attribute('data-chapter', 'recovery')
        nav.get_by_role('button', name='History').click()
        page.reload(wait_until='networkidle')
        expect(page.locator('#scenario-select')).to_be_enabled()
        expect(page.locator('#main')).to_have_attribute('data-chapter', 'experience')
        expect(page.locator('[data-view=desk]')).to_have_attribute('aria-current', 'location')
        assert page.evaluate('window.scrollY') < 5
        assert not starts
        use_rehearsal(page)
        scene = page.locator(".sculpture-panel")
        expect(scene).to_have_attribute("data-renderer",re.compile("webgl|static"),timeout=30000)
        renderer=scene.get_attribute("data-renderer")
        expect(scene).to_have_attribute('data-aligned','false')
        page.screenshot(path=ARTIFACTS/"react-hero.png")
        if renderer == "webgl":
            canvas=page.locator("canvas[data-scene]")
            expect(canvas).to_have_attribute("data-rotation",re.compile("-?[0-9.]+"))
            before=canvas.get_attribute("data-rotation")
            page.mouse.wheel(0,360)
            expect(canvas).not_to_have_attribute("data-rotation",before,timeout=5000)
            expect(scene).to_have_attribute('data-phase','idle')
            page.screenshot(path=ARTIFACTS/"react-hero-scrolled.png")
            box=canvas.bounding_box()
            before=canvas.get_attribute("data-rotation")
            page.mouse.move(box['x']+box['width']*.5,max(150,box['y']+box['height']*.5))
            page.mouse.down()
            page.mouse.move(box['x']+box['width']*.5+100,max(150,box['y']+box['height']*.5),steps=15)
            page.mouse.up()
            expect(canvas).not_to_have_attribute("data-rotation",before,timeout=5000)
        inventory=page.get_by_role("button",name="Inventory 02",exact=True)
        inventory.click()
        expect(inventory).to_have_attribute("aria-pressed","true")
        expect(page.locator('#service-value')).to_have_text('Reservation expired')
        page.get_by_role("button",name="Pause motion",exact=True).click()
        expect(scene).to_have_attribute("data-renderer","static")
        expect(page.locator("canvas[data-scene]")).to_have_count(0)
        assert page.locator('.static-crystal').is_visible()
        page.get_by_role("button",name="Enable motion",exact=True).click()
        if renderer == "webgl": expect(scene).to_have_attribute("data-renderer","webgl")
        page.locator('#watch-recovery').click()
        expect(page.locator("#run-status")).to_have_text("Verified",timeout=15000)
        expect(scene).to_have_attribute('data-phase','verified')
        expect(scene).to_have_attribute('data-aligned','true')
        page.screenshot(path=ARTIFACTS/'react-hero-verified.png')
        original_starts = len(starts)
        page.locator('#replay-run').click()
        expect(page.locator('#replay-cursor')).to_have_value('-1')
        expect(scene).to_have_attribute('data-aligned','false')
        expect(page.locator('.evidence-link')).to_have_count(0)
        expect(page.locator('#replay-cursor')).not_to_have_value('-1',timeout=5000)
        page.get_by_role('button',name='Pause replay',exact=True).click()
        paused = page.locator('#replay-cursor').input_value()
        page.wait_for_timeout(1250)
        expect(page.locator('#replay-cursor')).to_have_value(paused)
        seek(page, 8)  # The actual rejected reservation, before new inventory evidence.
        expect(scene).to_have_attribute('data-phase','replanning')
        expect(page.locator('.service-inspector')).to_have_attribute('data-status','blocked')
        expect(page.locator('#service-value')).to_have_text('Stock snapshot is stale')
        expect(page.locator('.evidence-link')).to_have_text(re.compile('EV-02'))
        page.screenshot(path=ARTIFACTS/'react-stock-conflict.png')
        seek(page, 11)
        expect(page.locator('#service-value')).to_have_text('0 original units available')
        seek(page, 15)
        expect(scene).to_have_attribute('data-phase','verifying')
        expect(scene).to_have_attribute('data-aligned','false')
        seek(page, 16)
        expect(scene).to_have_attribute('data-phase','verified')
        assert len(starts) == original_starts, 'Replay made a new run request'
        # Section navigation preserves the mounted core and exact replay cursor.
        page.locator('[data-view=history]').click()
        expect(page.locator('#main')).to_have_attribute('data-chapter','view-history')
        expect(page).to_have_url(re.compile('#view-history$'))
        expect(page.locator('#replay-cursor')).to_have_value('16')
        page.locator('[data-view=design]').click()
        expect(page.locator('#main')).to_have_attribute('data-chapter','view-design')
        expect(page.locator('[data-view=design]')).to_have_attribute('aria-current','location')
        page.locator('#view-design').screenshot(path=ARTIFACTS/'system-design.png')
        page.go_back()
        expect(page.locator('#main')).to_have_attribute('data-chapter','view-history')
        page.locator('[data-view=desk]').click()
        expect(page.locator('#main')).to_have_attribute('data-chapter','experience')
        expect(page.locator('#replay-cursor')).to_have_value('16')
        page.get_by_role('button',name='Latest',exact=True).click()
        if renderer == 'webgl':
            # Select the physical payment crystal, not its DOM label.
            page.get_by_role('button',name='Order 03',exact=True).click()
            # Selecting a lower inspector control may scroll the crystal out of view.
            page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
            settle_view(page)
            canvas=page.locator('canvas[data-scene]')
            point=json.loads(canvas.get_attribute('data-services'))[0]
            box=canvas.bounding_box()
            assert page.evaluate('([x,y]) => document.elementFromPoint(x,y)?.tagName', [box['x']+point['x'],box['y']+point['y']]) == 'CANVAS'
            page.mouse.click(box['x']+point['x'],box['y']+point['y'])
            expect(page.locator('.service-inspector')).to_have_attribute('data-service','Payment')
        else:
            page.get_by_role('button',name='Payment 01',exact=True).click()
        page.locator('.evidence-link').click()
        expect(page.locator('#evidence-EV-05')).to_have_attribute('open','')
        expect(page.locator('#evidence-EV-05 summary')).to_be_focused()
        assert "Order recovered" in page.locator("#metric-outcome").inner_text()
        assert "Captured once" in page.locator("#metric-payment").inner_text()
        assert page.locator(".check.pass").count() == 6
        assert page.locator(".trail-event.guard").count() == 1
        assert "escalated" in page.locator("#baseline-outcome").inner_text().lower()
        assert "0 model call" in page.locator("#current-detail").inner_text()
        page.locator('.workspace-shell').screenshot(path=ARTIFACTS/"desktop-recovered.png")
        page.locator("#results").screenshot(path=ARTIFACTS/"verification.png")
        with page.expect_download() as download: page.locator("#export-top").click()
        download.value.save_as(ARTIFACTS/"sample-audit.json")
        audit=json.loads((ARTIFACTS/"sample-audit.json").read_text(encoding='utf-8'))
        assert audit["report"]["provider"] == "rehearsal"
        assert audit["report"]["state"]["order"]["delivery_days"] == 1
        page.locator('.event-ref').first.click()
        expect(page.locator('#evidence-EV-01')).to_have_attribute('open','')
        page.get_by_role('button',name='Stock',exact=True).click()
        assert page.locator('.evidence-item').count() == len([e for e in audit['report']['state']['evidence'] if e['tool']=='inspect_inventory'])
        page.locator("[data-view=history]").click()
        assert page.locator(".history-item").count() >= 1
        with page.expect_response(lambda response: '/api/runs/' in response.url and not response.url.endswith('/export')):
            page.locator(".history-item").first.click()
        expect(page.locator('#main')).to_have_attribute('data-chapter','recovery')
        expect(page.locator("#results")).to_be_visible()
        page.select_option("#scenario-select","unknown-payment")
        page.locator("#start-run").click()
        expect(page.locator("#run-status")).to_have_text("Needs review",timeout=15000)
        expect(scene).to_have_attribute('data-phase','review')
        expect(scene).to_have_attribute('data-aligned','false')
        assert page.locator(".check.review").count() == 2
        assert page.locator("#metric-payment").inner_text() == "Unknown"
        page.locator('.workspace-shell').screenshot(path=ARTIFACTS/"uncertain-payment.png")
        page.select_option("#scenario-select","cancel-order")
        page.locator("#start-run").click()
        expect(page.locator("#run-status")).to_have_text("Verified",timeout=15000)
        assert page.locator("#metric-payment").inner_text() == "Refunded"
        assert page.locator("#metric-outcome").inner_text() == "Order cancelled"
        page.locator("#open-settings").click()
        expect(page.locator("#settings-dialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.locator("#settings-dialog")).not_to_be_visible()
        page.locator("[data-view=design]").click()
        assert "Reason with AI" in page.locator("#view-design h1").inner_text()
        page.locator("[data-view=desk]").click()
        page.select_option("#scenario-select","stock-race")
        page.set_viewport_size({"width":390,"height":844})
        for label in ('Home', 'Workspace', 'History', 'How it works'):
            button = nav.get_by_role('button', name=label, exact=label != 'History')
            expect(button).to_be_visible()
            assert button.bounding_box()['height'] >= 44
        page.evaluate("() => window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=ARTIFACTS/"mobile-hero.png")
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"), "Mobile horizontal overflow"
        page.locator('#watch-recovery').click()
        expect(page.locator("#run-status")).to_have_text("Verified",timeout=15000)
        seek(page,8)
        expect(page.locator('.service-inspector')).to_have_attribute('data-status','blocked')
        page.locator('.sculpture-panel').screenshot(path=ARTIFACTS/'mobile-core.png')
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        page.locator('.evidence-link').click()
        expect(page.locator('#evidence-EV-02')).to_have_attribute('open','')
        assert page.locator(".check.pass").count() == 6
        page.locator('.workspace-shell').screenshot(path=ARTIFACTS/"mobile-recovered.png")
        nav.get_by_role('button', name='History').click()
        page.reload(wait_until='networkidle')
        expect(page.locator('#main')).to_have_attribute('data-chapter','experience')
        expect(page.locator('#scenario-select')).to_be_enabled()
        assert page.evaluate('window.scrollY') < 5
        assert page.locator('.history-item').count() >= 1, 'Reload must preserve the history index'
        # Intentional deep links still open their section, unlike reload.
        linked=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
        linked.goto(base_url+'/#view-design',wait_until='networkidle')
        expect(linked.locator('#main')).to_have_attribute('data-chapter','view-design')
        assert linked.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        linked.screenshot(path=ARTIFACTS/'mobile-design.png')
        linked.set_viewport_size({'width':320,'height':740})
        linked.locator('[data-nav=recovery]').click()
        expect(linked.locator('#main')).to_have_attribute('data-chapter','recovery')
        assert linked.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), '320px workspace overflow'
        linked.close()
        # A slow history response must not overwrite a newer incident selection.
        race=browser.new_page(viewport={'width':1280,'height':900},reduced_motion='reduce')
        race.add_init_script('sessionStorage.setItem("workflow-rescue-history", '+json.dumps(json.dumps([audit['report']]))+');')
        delayed=[]
        race.route('**/api/runs/'+audit['report']['id'],lambda route: delayed.append(route))
        race.goto(base_url+'/#view-history',wait_until='networkidle')
        race.locator('.history-item').first.click()
        race.locator('[data-nav=recovery]').click()
        race.locator('#scenario-select').select_option('unknown-payment')
        assert len(delayed) == 1
        delayed[0].fulfill(json=audit['report'])
        race.wait_for_timeout(150)
        expect(race.locator('#scenario-select')).to_have_value('unknown-payment')
        expect(race.locator('#run-status')).to_have_text('Ready')
        race.close()
        quiet=browser.new_page(viewport={"width":1280,"height":900},reduced_motion='reduce')
        quiet_requests=[]
        quiet.on('request',lambda r: quiet_requests.append(r.url))
        quiet.goto(base_url,wait_until='networkidle')
        use_rehearsal(quiet)
        expect(quiet.locator('.sculpture-panel')).to_have_attribute('data-renderer','static')
        expect(quiet.locator('canvas')).to_have_count(0)
        assert not any('three-scene' in url for url in quiet_requests)
        quiet.locator('[data-view=design]').click()
        expect(quiet.locator('#main')).to_have_attribute('data-chapter','view-design')
        assert quiet.locator('.reveal-ready').count() == 0
        quiet.locator('[data-view=desk]').click()
        quiet.get_by_role('button',name='Order 03',exact=True).click()
        expect(quiet.locator('#service-value')).to_have_text('Interrupted')
        quiet.locator('#watch-recovery').click()
        expect(quiet.locator('.sculpture-panel')).to_have_attribute('data-phase','verified',timeout=15000)
        seek(quiet,8)
        expect(quiet.locator('.static-module[data-status=blocked]')).to_have_count(1)
        quiet.get_by_role('button',name='Inspect Payment',exact=True).focus()
        quiet.keyboard.press('Enter')
        expect(quiet.locator('.service-inspector')).to_have_attribute('data-service','Payment')
        quiet.close()
        fallback=browser.new_page(viewport={"width":1280,"height":900})
        fallback.add_init_script("const original=HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext=function(kind,...rest){if(kind==='webgl2'||kind==='webgl')return null;return original.call(this,kind,...rest);};")
        fallback.goto(base_url,wait_until='networkidle')
        use_rehearsal(fallback)
        expect(fallback.locator('.sculpture-panel')).to_have_attribute('data-renderer','static')
        fallback.locator('#watch-recovery').click()
        expect(fallback.locator('#run-status')).to_have_text('Verified',timeout=15000)
        expect(fallback.locator('.static-module[data-status=verified]')).to_have_count(3)
        fallback.get_by_role('button',name='Inspect Inventory',exact=True).click()
        expect(fallback.locator('.service-inspector')).to_have_attribute('data-service','Inventory')
        fallback.close()
        # Failure rendering uses a deliberately failed verification fixture, not a live model call.
        failed=browser.new_page(viewport={'width':1280,'height':900})
        failed_record=json.loads(json.dumps(audit['report']))
        failed_record.update(id='qa-failed',status='failed')
        failed_record['checks'][0]['status']='fail'
        failed.route('**/api/runs',lambda route: route.fulfill(json={'id':'qa-failed','status':'queued'}))
        failed.route('**/api/runs/qa-failed',lambda route: route.fulfill(json=failed_record))
        failed.goto(base_url,wait_until='networkidle')
        failed.locator('#watch-recovery').click()
        expect(failed.locator('.sculpture-panel')).to_have_attribute('data-phase','error')
        expect(failed.locator('.sculpture-panel')).to_have_attribute('data-aligned','false')
        expect(failed.locator('.domain-chip[data-status=error]')).to_have_count(1)
        failed.close()
        live_result = None
        if live_provider:
            live = browser.new_page(viewport={'width':1440,'height':1000})
            live.on('pageerror',lambda e: errors.append(str(e)))
            live.goto(base_url,wait_until='networkidle')
            live.locator('#provider-select').select_option(live_provider)
            live.locator('#connection-test').click()
            expect(live.locator('.connection-result')).to_contain_text('Live structured model response',timeout=240000)
            live.locator('[data-view=desk]').click()
            expect(live.locator('#main')).to_have_attribute('data-chapter','experience')
            live.screenshot(path=ARTIFACTS/f'{live_provider}-hero.png')
            live.locator('#watch-recovery').click()
            expect(live.locator('#run-status')).to_have_text('Verified',timeout=600000)
            expect(live.locator('.sculpture-panel')).to_have_attribute('data-phase','verified')
            assert live.locator('.check.pass').count() == 6
            live.screenshot(path=ARTIFACTS/f'{live_provider}-core-verified.png')
            with live.expect_download() as download:
                live.locator('#export-top').click()
            output=ARTIFACTS/f'live-{live_provider}-audit.json'
            download.value.save_as(output)
            actual=json.loads(output.read_text(encoding='utf-8'))
            assert actual['team'] == 'sustAInX'
            assert actual['report']['provider'] == live_provider
            assert actual['report']['metrics']['calls'] > 0
            assert actual['report']['state']['outcome'] == 'recovered'
            live.locator('#results').screenshot(path=ARTIFACTS/'live-verification.png')
            live_result = {'provider': live_provider, 'model':actual['report']['model'], 'calls':actual['report']['metrics']['calls'], 'status':actual['report']['status']}
            live.close()
        assert not errors, errors
        report={"interface":"React + Three.js","desktop":"passed","mobile":"passed","renderer":renderer,"console_errors":errors,
                "covered":["reload returns Home on desktop and mobile","intentional deep links are preserved","four visible mobile navigation tabs with 44px targets","320px workspace without overflow","empty History navigation makes no model calls","late history response cannot overwrite incident selection","continuous page with chapter transitions","navigation and browser back preserve replay","active chapter follows scrolling","reduced motion disables section reveals","sustAInX team branding","3D scroll and drag rotation","physical crystal click and evidence navigation","scroll cannot verify an outcome","hero starts a real rehearsal run","read-only replay with pause and keyboard scrubbing","stock conflict and post-commit verification states","mocked failed verification is red","motion toggle","system reduced motion without 3D download","keyboard accessible SVG state and selection","WebGL fallback and recovery","stock race and adaptive recovery","unknown payment escalation","cancellation and refund","audit export","evidence citation and filters","history restore","settings keyboard close","architecture view","390px responsive layout and replay"],"live_model_verified":bool(live_result),"live_run":live_result}
        (ARTIFACTS/"browser-validation.json").write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
        browser.close()

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--live-provider',choices=['azure','gemini','vertex','openai'])
    parser.add_argument('--base-url',default='http://127.0.0.1:8080')
    args=parser.parse_args()
    main(args.live_provider,args.base_url)
