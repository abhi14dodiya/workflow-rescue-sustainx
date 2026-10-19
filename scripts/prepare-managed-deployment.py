"""Prepare and scan a standalone Node application; create no cloud resources."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'artifacts' / 'workflow-rescue-managed-deployment.zip'
spec = importlib.util.spec_from_file_location('source_check', ROOT / 'scripts/check-public-source.py')
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)
secrets = scan.configured_secrets()
files = {}
for name in ('package.json', 'server.mjs', 'runtime.mjs', 'domain.mjs', 'audit-store.mjs',
             'contracts.json', 'README.md', 'runtime.test.mjs', 'streaming.test.mjs', 'parity-fixtures.json'):
    files[name] = (ROOT / 'starter' / name).read_bytes()
for path in (ROOT / 'web').rglob('*'):
    if path.is_file():
        files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
files['.gitignore'] = b'.env\n.env.*\n!.env.example\nnode_modules/\n*.log\n'
files['.env.example'] = b'GEMINI_API_KEY=\nGEMINI_MODEL=gemini-3.5-flash-lite\nDEFAULT_PROVIDER=gemini\nFIRESTORE_PROJECT_ID=\nMAX_ACTIVE_RUNS=1\nMAX_MODEL_CALLS_PER_HOUR=60\n'
files['Dockerfile'] = b'FROM node:22-alpine\nWORKDIR /app\nCOPY package.json server.mjs runtime.mjs domain.mjs audit-store.mjs contracts.json ./\nCOPY web ./web\nUSER node\nENV PORT=8080\nEXPOSE 8080\nCMD ["node", "server.mjs"]\n'
issues = []
for name, data in files.items():
    if any(secret in data for secret in secrets):
        issues.append({'file': name, 'reason': 'configured credential detected'})
    for label, pattern in scan.PATTERNS.items():
        if pattern.search(data):
            issues.append({'file': name, 'reason': label})
if issues:
    raise SystemExit(json.dumps({'passed': False, 'issues': issues}))
OUTPUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for name, data in sorted(files.items()):
        archive.writestr(name, data)
result = {'passed': True, 'file': str(OUTPUT), 'files': len(files),
          'sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
          'bytes': OUTPUT.stat().st_size, 'secret_issues': issues,
          'deployed': False, 'runtime': 'Node.js 22; Gemini only; HTTP recovery stream',
          'requires': ['An authorized hosting account', 'Server-only Gemini key',
                       'Firestore project and authorized Google runtime identity']}
(ROOT / 'artifacts/managed-deployment-package.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
