"""Start a temporary Gemini demo on an existing Cloud Shell VM.

Creates no Cloud Run, Cloud Build, registry or billing resources. A free
TryCloudflare tunnel supplies HTTPS. This is session-bound demonstration
hosting, not a durable competition submission deployment.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'
ART.mkdir(exist_ok=True)

if os.getenv('USER_CONFIRMED_GEMINI_FREE_TIER') != '1':
    raise SystemExit('Confirm this key belongs to a Gemini API Free-tier project before starting.')

from dotenv import dotenv_values
values = dotenv_values(ROOT / '.env')
key = values.get('GEMINI_API_KEY')
if not key:
    raise SystemExit('GEMINI_API_KEY is missing from the server-only .env file.')
os.chmod(ROOT / '.env', 0o600)

# No other model provider is configured in this public demonstration process.
env = {k:v for k,v in os.environ.items() if not k.startswith(('AZURE_OPENAI_', 'OPENAI_', 'GOOGLE_CLOUD_', 'VERTEX_'))
       and k not in {'GOOGLE_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', 'DEMO_ACCESS_TOKEN'}}
env.update(GEMINI_API_KEY=key, GEMINI_MODEL=values.get('GEMINI_MODEL', 'gemini-3.8-flash'),
           DEFAULT_PROVIDER='gemini', MAX_ACTIVE_RUNS='1', MAX_MODEL_CALLS_PER_HOUR='60')
if values.get('FIRESTORE_PROJECT_ID'):
    env['FIRESTORE_PROJECT_ID'] = values['FIRESTORE_PROJECT_ID']
    # Cloud Shell may supply ADC through its credential-broker configuration.
    # Preserve the inherited path for Firestore, without enabling a Vertex project.
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        env['GOOGLE_APPLICATION_CREDENTIALS'] = os.environ['GOOGLE_APPLICATION_CREDENTIALS']

port = None
for candidate in (8080, 8081, 8082):
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', candidate)) != 0:
            port = candidate
            break
if port is None:
    raise SystemExit('Demo ports are already in use. No existing process was stopped.')

processes = []
success = False
try:
    with (ART / 'cloud-shell-app.log').open('ab') as log:
        app = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)],
                               cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    processes.append(app)
    base = f'http://127.0.0.1:{port}'
    for attempt in range(60):
        if app.poll() is not None:
            raise RuntimeError('Application startup failed; inspect artifacts/cloud-shell-app.log.')
        try:
            with urllib.request.urlopen(base + '/healthz', timeout=2) as response:
                if json.load(response)['status'] == 'ok':
                    break
        except (OSError, ValueError):
            time.sleep(0.5)
    else:
        raise RuntimeError('Application health check timed out.')

    # Validate Gemini before publishing the demo. The app sanitizes provider errors.
    request = urllib.request.Request(base + '/api/provider-check', data=b'{"provider":"gemini"}',
                                     headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            connection = json.load(response)
    except urllib.error.HTTPError as error:
        result = json.load(error)
        raise RuntimeError('Gemini check failed: ' + json.dumps(result)) from None
    if not connection.get('ok'):
        raise RuntimeError('Gemini did not pass its structured response check.')
    (ART / 'gemini-cloud-connection.json').write_text(json.dumps(connection, indent=2))

    # Download the official client and verify the release asset's published digest.
    metadata_request = urllib.request.Request('https://api.github.com/repos/cloudflare/cloudflared/releases/latest',
                                               headers={'User-Agent':'workflow-rescue-demo'})
    with urllib.request.urlopen(metadata_request, timeout=30) as response:
        release = json.load(response)
    asset = next(a for a in release['assets'] if a['name'] == 'cloudflared-linux-amd64')
    expected = asset.get('digest', '')
    if not expected.startswith('sha256:') or not asset['browser_download_url'].startswith('https://github.com/cloudflare/cloudflared/releases/download/'):
        raise RuntimeError('The official tunnel binary has no usable verification metadata.')
    binary = ART / 'cloudflared'
    with urllib.request.urlopen(asset['browser_download_url'], timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected.split(':', 1)[1]:
        raise RuntimeError('Tunnel binary digest mismatch.')
    binary.write_bytes(data)
    binary.chmod(0o700)
    tunnel_log = ART / 'cloud-shell-tunnel.log'
    config = ART / 'tunnel-empty.yml'
    config.write_text('{}\n')
    with tunnel_log.open('wb') as log:
        tunnel = subprocess.Popen([str(binary), '--no-autoupdate', '--config', str(config), 'tunnel',
                                   '--url', base, '--protocol', 'http2'], cwd=ROOT,
                                  stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    processes.append(tunnel)
    public_url = None
    for attempt in range(90):
        if tunnel.poll() is not None:
            raise RuntimeError('Tunnel startup failed; inspect artifacts/cloud-shell-tunnel.log.')
        match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', tunnel_log.read_text(errors='replace'))
        if match:
            public_url = match.group(0)
            break
        time.sleep(1)
    if not public_url:
        raise RuntimeError('The tunnel did not issue a public URL.')
    result = {'url':public_url, 'provider':'gemini', 'model':env['GEMINI_MODEL'],
              'hosting':'Temporary Cloud Shell VM with a free TryCloudflare HTTPS tunnel',
              'port':port, 'app_pid':app.pid, 'tunnel_pid':tunnel.pid,
              'limitation':'The link stops when Cloud Shell ends the session. This is not a durable submission deployment.'}
    (ART / 'cloud-shell-demo.json').write_text(json.dumps(result, indent=2))
    success = True
    print(json.dumps(result), flush=True)
finally:
    if not success:
        for process in processes:
            if process.poll() is None:
                process.terminate()
