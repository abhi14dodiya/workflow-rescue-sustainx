"""Free offline narration and truthful screen capture of a fresh deployed Gemini run.

prepare: generate Windows SAPI narration; no network/model calls.
record: capture the actual deployed UI and one fresh Gemini run; no API mocking.
render: make a 210-second MP4, label any time compression and retain raw footage.

Dependencies for recording: playwright, Edge, Playwright's FFmpeg runtime.
Dependency for rendering: imageio-ffmpeg (or ffmpeg on PATH), Pillow.
The script neither publishes the recording nor creates cloud resources.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import wave
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts' / 'video'
MANIFEST = OUT / 'narration.json'
RECORDING = OUT / 'recording.json'
EDGES = [Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'),
         Path(r'C:\Program Files\Microsoft\Edge\Application\msedge.exe')]
SEGMENTS = [
    ('intro', 22, 'Workflow Rescue by sustAInX',
     'This is Workflow Rescue, by sustain X. A business workflow can stop between systems even when a payment succeeds. '
     'The operations team must establish what happened, what the customer allows, and which action is still safe. '
     'Our interactive recovery core connects those questions to inspectable evidence.'),
    ('incident', 28, 'Import an incident. Declare the permissions.',
     'I am importing a new synthetic incident as JSON. The customer requests original items and price, a maximum '
     'one day delay, and no second charge. The form separately declares demo permissions and service evidence. '
     'Gemini will use these inputs in a fresh run. The business services are simulated, while the AI requests are real.'),
    ('live', 75, 'Fresh Gemini requests. Actual recorded run.',
     'I am starting a fresh investigation on the deployed application. The controller first reads payment, inventory '
     'and dispatch, because these observations are required before any change. Gemini then proposes a recovery '
     'using that evidence. The payment receipt establishes that money was already captured. '
     'In this scenario, competing demand changes the stock after it was inspected. A reservation based on an older '
     'version is rejected. The controller does not accept an explanation in place of valid evidence. '
     'The planner must inspect again and adapt within the same customer mandate. '
     'The recovery uses incoming stock of the original item, within the permitted delay, and confirms the existing payment. '
     'The evidence identifiers connect proposals to observations. The trail preserves the rejected action as well as the '
     'successful one. A recovery is complete only when the independent checks agree; uncertainty belongs in an operator review. '
     'The video retains the actual activity and outcome; if the wait is accelerated, the label on screen identifies that edit.'),
    ('checks', 32, 'Proposal → execution guard → independent checks',
     'The rejected proposal remains visible in the trail. It explains why the first plan could not execute. '
     'The final checks read the simulated ledgers directly: payment, reservation, order, and customer permissions. '
     'Green means a check passed; yellow means review is needed; red means a detected issue. '
     'This separation matters: a model proposes an action, bounded code enforces it, and independent checks establish the result.'),
    ('audit', 28, 'Evidence the operator can inspect and export',
     'I can export this run with its evidence, actions, checks, and actual model-call counts. History lets the operator '
     'revisit the result. The trace is inspectable, but is not a certified immutable audit system. '
     'All six built-in scenarios passed the deployed Gemini evaluation. Missing payment evidence and cancellation '
     'after dispatch correctly required operator review.'),
    ('close', 25, 'Recover the workflow. Preserve the promise.',
     'Gemini reasons from observations. The controller enforces scope and verifies the outcome. '
     'The intended user is the app owner\'s operations team, with explicit connector permissions. '
     'Production integrations and measured savings remain future work. Workflow Rescue, by sustain X: '
     'recover the workflow, and preserve the promise.'),
]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def wav_seconds(path):
    with wave.open(str(path), 'rb') as stream:
        return stream.getnframes() / stream.getframerate()


def stamp(seconds):
    total = round(seconds * 1000)
    h, rem = divmod(total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    items = [dict(id=i, duration=d, title=title, text=text,
                  wav=str(OUT / f'{i}.wav')) for i, d, title, text in SEGMENTS]
    write_json(MANIFEST, items)
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(ROOT / 'scripts' / 'voice-demo-tts.ps1'), '-Manifest', str(MANIFEST)], check=True)
    elapsed = 0
    captions, transcript = [], []
    for item in items:
        duration = wav_seconds(item['wav'])
        item['speech_seconds'] = round(duration, 3)
        if duration > item['duration'] - .2:
            raise RuntimeError(f"{item['id']} narration is {duration:.1f}s; shorten it to fit {item['duration']}s.")
        # Approximate phrase timings from each recorded speech chunk; the actual WAV is authoritative.
        phrases = re.split(r'(?<=[.!?])\s+', item['text'])
        weights = [len(p.split()) for p in phrases]
        offset = elapsed + .4
        for phrase, weight in zip(phrases, weights):
            end = offset + duration * weight / sum(weights)
            captions.append(f'{len(captions)+1}\n{stamp(offset)} --> {stamp(end)}\n{phrase}\n')
            offset = end
        transcript.append(f"{stamp(elapsed)} | {item['title']}\n{item['text']}\n")
        elapsed += item['duration']
    write_json(MANIFEST, items)
    (OUT / 'workflow-rescue-demo.srt').write_text('\n'.join(captions), encoding='utf-8')
    (OUT / 'transcript.txt').write_text('\n'.join(transcript), encoding='utf-8')
    print(json.dumps({'narration_ready': True, 'planned_video_seconds': elapsed,
                      'voice': 'Microsoft Zira Desktop (offline)', 'model_calls': 0}))


def record(base_url, confirmed):
    from playwright.sync_api import sync_playwright, expect
    parsed = urlsplit(base_url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in {'', '/'}):
        raise ValueError('Use the public HTTPS app origin, without credentials, a path or a query.')
    if not confirmed:
        raise ValueError('Confirm the server uses the free Gemini tier with --confirm-free-gemini.')
    if not MANIFEST.exists():
        raise RuntimeError('Run prepare first.')
    OUT.mkdir(parents=True, exist_ok=True)
    origin = base_url.rstrip('/')
    timings, errors = [], []
    run = None
    with sync_playwright() as p:
        edge = next((str(e) for e in EDGES if e.exists()), None)
        browser = p.chromium.launch(headless=True, **({'executable_path': edge} if edge else {}))
        context = browser.new_context(viewport={'width': 1440, 'height': 900},
                                      record_video_dir=str(OUT / 'raw'),
                                      record_video_size={'width': 1440, 'height': 900},
                                      accept_downloads=True)
        page = context.new_page()
        video = page.video
        started = time.monotonic()
        page.on('pageerror', lambda error: errors.append(str(error)))

        def begin(identifier):
            point = time.monotonic() - started
            if timings:
                timings[-1]['end'] = point
            timings.append({'id': identifier, 'start': point})
            print(json.dumps({'recording_section': identifier}), flush=True)

        def pause(seconds=3):
            page.wait_for_timeout(seconds * 1000)

        try:
            begin('intro')
            page.goto(origin, wait_until='networkidle', timeout=60000)
            page.locator('#scenario-select').wait_for(state='attached')
            pause(4)
            page.get_by_role('button', name='Inventory 02', exact=True).click()
            pause(4)
            page.get_by_role('button', name='Payment 01', exact=True).click()
            pause(3)

            begin('incident')
            page.locator('[data-nav=recovery]').click()
            custom = {'customer_note': 'Keep the original Field Kits at the original price. A delay of at most one day is approved. Do not substitute or charge again.',
                      'available': 2, 'incoming_available': 7, 'alternative_available': 4, 'incoming_days': 1,
                      'max_delay_days': 1, 'allow_delay': True, 'allow_substitution': False,
                      'cancel_requested': False, 'payment_unknown': False, 'shipped': False, 'race': True}
            custom_path = OUT / 'custom-incident.json'
            write_json(custom_path, custom)
            page.locator('#incident-lab > summary').click()
            page.get_by_label('Import incident JSON').set_input_files(custom_path)
            expect(page.locator('#lab-max_delay_days')).to_have_value('1', timeout=30000)
            page.locator('#lab-note').scroll_into_view_if_needed()
            pause(5)
            page.locator('#apply-incident').click()
            expect(page.locator('#scenario-select')).to_have_value('custom', timeout=30000)
            page.locator('#incident-lab > summary').click()
            page.locator('#provider-select').select_option('gemini')
            page.locator('.customer-card').scroll_into_view_if_needed()
            pause(4)
            page.locator('#provider-select').scroll_into_view_if_needed()
            pause(3)

            begin('live')
            with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/runs')) as result:
                page.locator('#start-run').click()
            response = result.value
            if response.status != 202:
                raise RuntimeError(f'Fresh run rejected with HTTP {response.status}; no success recording produced.')
            run_id = response.json()['id']
            page.locator('.recovery-card').scroll_into_view_if_needed()
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                fetched = page.evaluate('async path => { const r=await fetch(path); return {status:r.status, body:await r.json()}; }', f'/api/runs/{run_id}')
                if fetched['status'] != 200:
                    raise RuntimeError(f"Run poll failed with HTTP {fetched['status']}")
                run = fetched['body']
                if run['status'] not in {'queued', 'running'}:
                    break
                pause(2)
            else:
                raise TimeoutError('The live run did not finish within ten minutes.')
            write_json(OUT / 'actual-gemini-run.json', run)
            if (run['provider'] != 'gemini' or run['metrics'].get('calls', 0) < 1
                    or run['status'] != 'completed' or run['state']['outcome'] != 'recovered'
                    or run['metrics'].get('blocked_proposals', 0) < 1
                    or any(c['status'] == 'fail' for c in run.get('checks', []))):
                raise RuntimeError('Recorded evidence does not support the stock-conflict success narration. Inspect actual-gemini-run.json.')
            pause(3)

            begin('checks')
            guard = page.locator('.trail-event.guard').first
            guard.scroll_into_view_if_needed()
            pause(5)
            if page.locator('.evidence-item').count():
                page.locator('.evidence-item').first.locator('summary').click()
                pause(5)
            page.locator('#results').scroll_into_view_if_needed()
            pause(9)

            begin('audit')
            with page.expect_download() as download:
                page.locator('#export-result').click()
            download.value.save_as(OUT / 'live-gemini-audit.json')
            pause(4)
            page.locator('[data-view=history]').click()
            pause(7)

            begin('close')
            page.locator('[data-view=design]').click()
            pause(8)
            page.locator('[data-view=desk]').click()
            pause(6)
            timings[-1]['end'] = time.monotonic() - started
        finally:
            if timings and 'end' not in timings[-1]:
                timings[-1]['end'] = time.monotonic() - started
            context.close()
            video_path = str(video.path())
            browser.close()
            write_json(RECORDING, {'base_url': origin, 'video': video_path,
                                   'segments': timings, 'browser_errors': errors,
                                   'run_id': run.get('id') if run else None,
                                   'run_status': run.get('status') if run else None,
                                   'model': run.get('model') if run else None,
                                   'elapsed_ms': run.get('metrics', {}).get('elapsed_ms') if run else None,
                                   'recorded_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
    if errors:
        raise RuntimeError(f'Recording had {len(errors)} browser errors; inspect recording.json.')
    print(json.dumps({'recorded': True, 'raw_video': video_path, 'run_id': run['id']}))


def ffmpeg_path():
    found = shutil.which('ffmpeg')
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as error:
        raise RuntimeError('Install the free local encoder: python -m pip install --user imageio-ffmpeg') from error


def make_label(path, title, subline):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('RGBA', (1440, 86), (14, 22, 36, 246))
    draw = ImageDraw.Draw(im)
    normal = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 19)
    bold = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 26)
    draw.rounded_rectangle((22, 24, 30, 61), radius=4, fill='#6fddc1')
    draw.text((46, 10), title, font=bold, fill='white')
    draw.text((47, 48), subline, font=normal, fill='#c1d7ea')
    im.save(path)


def run_ffmpeg(arguments):
    subprocess.run([ffmpeg_path(), '-hide_banner', '-loglevel', 'error', '-y', *arguments], check=True)


def render():
    narration = json.loads(MANIFEST.read_text(encoding='utf-8'))
    recording = json.loads(RECORDING.read_text(encoding='utf-8'))
    run = json.loads((OUT / 'actual-gemini-run.json').read_text(encoding='utf-8'))
    if recording['run_status'] != 'completed' or run['provider'] != 'gemini' or run['state']['outcome'] != 'recovered':
        raise RuntimeError('Refusing to narrate recovery success over an unsuccessful or non-Gemini run.')
    markers = {m['id']: m for m in recording['segments']}
    clips, edit_details = [], []
    for item in narration:
        mark = markers[item['id']]
        actual = mark['end'] - mark['start']
        target = item['duration']
        factor = min(1., target / actual)
        speed = 1 / factor
        if speed > 1.01:
            note = f'Recorded live | {speed:.2f}x playback | actual section: {actual:.1f}s | synthetic services'
        else:
            note = 'Actual deployed application | live Gemini run | synthetic business services'
        if item['id'] == 'checks':
            note += f" | {run['metrics']['steps']} Gemini proposals + {run['metrics'].get('preflight_reads', 0)} initial controller reads"
        label = OUT / f"{item['id']}-label.png"
        make_label(label, item['title'], note)
        clip = OUT / f"{item['id']}-clip.mp4"
        # Keep original playback speed unless compression is necessary; pad the last real frame.
        vf = (f'[0:v]setpts={factor:.9f}*(PTS-STARTPTS),fps=25,'
              f'tpad=stop_mode=clone:stop_duration={target},trim=duration={target},'
              'scale=1440:900,pad=1440:986:0:86:color=0x0e1624[screen];'
              '[screen][1:v]overlay=0:0[v];'
              f'[2:a]adelay=400|400,apad,atrim=duration={target}[a]')
        run_ffmpeg(['-ss', str(mark['start']), '-t', str(actual), '-i', recording['video'],
                    '-loop', '1', '-i', str(label), '-i', item['wav'],
                    '-filter_complex', vf, '-map', '[v]', '-map', '[a]',
                    '-t', str(target), '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', str(clip)])
        clips.append(clip)
        edit_details.append({'section': item['id'], 'actual_seconds': round(actual, 3),
                             'output_seconds': target, 'playback_speed': round(speed, 3)})
        print(json.dumps({'rendered_section': item['id']}), flush=True)
    concat = OUT / 'concat.txt'
    concat.write_text(''.join("file '" + str(p).replace('\\', '/').replace("'", "'\\''") + "'\n" for p in clips), encoding='utf-8')
    final = OUT / 'workflow-rescue-demo.mp4'
    run_ffmpeg(['-f', 'concat', '-safe', '0', '-i', str(concat),
                '-i', str(OUT / 'workflow-rescue-demo.srt'), '-map', '0:v', '-map', '0:a', '-map', '1:0',
                '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=eng',
                '-disposition:s:0', 'default', '-movflags', '+faststart', str(final)])
    inspection = subprocess.run([ffmpeg_path(), '-hide_banner', '-i', str(final)],
                                capture_output=True, text=True)
    match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', inspection.stderr)
    if not match:
        raise RuntimeError('Could not inspect the encoded video duration.')
    duration = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])
    if not 180 <= duration <= 240:
        raise RuntimeError('Video is outside the organizer\'s 3–4-minute requirement.')
    write_json(OUT / 'video-manifest.json', {'file': str(final), 'actual_duration_seconds': duration,
                                           'narration': 'Offline Microsoft Zira desktop voice',
                                           'base_url': recording['base_url'], 'run_id': recording['run_id'],
                                           'provider': run['provider'], 'model': run['model'],
                                           'model_calls': run['metrics']['calls'], 'edits': edit_details,
                                           'limitations': 'Synthetic services. No claim of durable hosting, production integration or competition submission.'})
    print(json.dumps({'video': str(final), 'actual_duration_seconds': duration, 'review_audio_and_video_before_upload': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('prepare')
    capture = commands.add_parser('record')
    capture.add_argument('--base-url', required=True)
    capture.add_argument('--confirm-free-gemini', action='store_true')
    commands.add_parser('render')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
    elif args.command == 'record':
        record(args.base_url, args.confirm_free_gemini)
    else:
        render()
