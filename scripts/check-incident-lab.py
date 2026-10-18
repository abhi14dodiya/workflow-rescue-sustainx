"""Exercise custom JSON import, changed outcomes and Firestore from the real UI."""
import argparse
import json
from pathlib import Path
import time
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main(base_url):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
        page = browser.new_page(viewport={'width':1440, 'height':1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base_url, wait_until='networkidle')
        page.locator('#provider-select').select_option('rehearsal')
        page.locator('#incident-lab summary').click()
        data = {'available':0, 'incoming_available':0, 'alternative_available':0,
                'race':False, 'allow_delay':False, 'allow_substitution':False,
                'customer_note':'No substitutions or delay. Keep the original price; ask for review if unavailable.'}
        page.get_by_label('Import incident JSON', exact=True).set_input_files({
            'name':'unavailable-stock.json', 'mimeType':'application/json', 'buffer':json.dumps(data).encode()})
        expect(page.locator('#lab-available')).to_have_value('0')
        page.locator('#apply-incident').click()
        expect(page.locator('#scenario-select')).to_have_value('custom')
        page.locator('#incident-lab').screenshot(path=ROOT/'artifacts/custom-incident-lab.png')
        page.locator('#start-run').click()
        expect(page.locator('#run-status')).to_have_text('Needs review', timeout=30000)
        assert page.locator('#metric-outcome').inner_text() == 'Operator review'
        page.locator('#lab-alternative_available').fill('6')
        page.locator('#lab-allow_substitution').check()
        page.locator('#lab-note').fill('Field Kit Plus is approved at the original price. No additional charge and no delay.')
        page.locator('#apply-incident').click()
        expect(page.locator('#apply-incident')).to_be_enabled()
        with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/runs')) as response:
            page.locator('#start-run').click()
        assert json.loads(response.value.request.post_data)['custom_incident']['allow_substitution'] is True
        assert response.value.status == 202, response.value.text()
        run_id = response.value.json()['id']
        expect(page.locator('#run-status')).to_have_text('Verified', timeout=30000)
        for _ in range(25):
            run = page.evaluate('async path => (await fetch(path)).json()', '/api/runs/' + run_id)
            if run.get('persistence', {}).get('saved'):
                break
            time.sleep(.4)
        assert run['state']['order']['sku'] == 'FIELD-KIT-PLUS'
        assert run['metrics']['calls'] == 0
        assert run['persistence'] == {'saved':True, 'backend':'firestore'}
        page.locator('#results').screenshot(path=ROOT/'artifacts/custom-substitute-verification.png')
        with page.expect_download() as download:
            page.locator('#export-result').click()
        download.value.save_as(ROOT/'artifacts/custom-incident-audit.json')
        assert not errors, errors
        report = {'passed':True, 'base_url':base_url, 'run_id':run_id, 'provider':'rehearsal',
                  'checks':['JSON imported and validated', 'unavailable stock escalates', 'explicit substitute permission changes outcome',
                            'same price and no new charge', 'completed audit saved in Firestore', 'audit exported'], 'browser_errors':errors}
        (ROOT/'artifacts/custom-incident-browser.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report))
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    main(parser.parse_args().base_url.rstrip('/'))
