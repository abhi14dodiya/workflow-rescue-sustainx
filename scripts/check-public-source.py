"""Check Git publication candidates without printing any secret values.

Defaults to tracked and non-ignored untracked files. Use --staged immediately
before a commit to inspect the exact bytes staged for publication.
This is a practical check, not a guarantee that all possible secrets are found.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'google_api_key': re.compile(rb'AIza[0-9A-Za-z_-]{35}'),
    'github_token': re.compile(rb'gh[pousr]_[0-9A-Za-z]{30,}'),
    'github_fine_grained_token': re.compile(rb'github_pat_[0-9A-Za-z_]{40,}'),
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'aws_access_key': re.compile(rb'AKIA[0-9A-Z]{16}'),
}
SENSITIVE_NAME = re.compile(r'(API_?KEY|ACCESS_?TOKEN|AUTH_?TOKEN|PASSWORD|SECRET|PRIVATE_KEY)', re.I)


def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError('Git inspection failed; no captured output displayed.')
    return result.stdout


def configured_secrets():
    values = set()
    for name, value in os.environ.items():
        if SENSITIVE_NAME.search(name) and len(value) >= 16:
            values.add(value.encode())
    # Read known local secret configuration only to compare; never emit values.
    files = list(ROOT.glob('.env*')) + list((ROOT / 'artifacts').glob('*.env'))
    for path in files:
        if not path.is_file() or path.name == '.env.example':
            continue
        for line in path.read_text(encoding='utf-8-sig', errors='ignore').splitlines():
            if '=' not in line or line.lstrip().startswith('#'):
                continue
            name, value = line.split('=', 1)
            value = value.strip().strip('\"\'')
            if SENSITIVE_NAME.search(name) and len(value) >= 16 and not value.lower().startswith(('your-', 'your_', 'replace', 'example')):
                values.add(value.encode())
    return values


def forbidden(path):
    parts = Path(path).parts
    name = Path(path).name.lower()
    return (any(p in {'artifacts', 'node_modules', '.venv', '.git'} for p in parts)
            or (name.startswith('.env') and name != '.env.example')
            or name.endswith(('.ppk', '.p12', '.pfx'))
            or name.startswith(('service-account', 'credentials')) and name.endswith('.json'))


def surfaces(path, raw):
    yield 'file', raw
    if path.lower().endswith(('.pptx', '.docx', '.xlsx', '.zip')):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                if sum(i.file_size for i in archive.infolist()) > 100_000_000:
                    raise RuntimeError(f'Archive exceeds scan limit: {path}')
                for item in archive.infolist():
                    if not item.is_dir():
                        yield 'archive-member', archive.read(item)
        except zipfile.BadZipFile:
            raise RuntimeError(f'Invalid archive: {path}') from None
    elif path.lower().endswith('.pdf'):
        try:
            import fitz
        except ImportError:
            return
        with fitz.open(stream=raw, filetype='pdf') as document:
            for page in document:
                yield 'pdf-text', page.get_text().encode()


def main(staged):
    output = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z') if staged else git('ls-files', '--cached', '--others', '--exclude-standard', '-z')
    paths = sorted(set(p.decode('utf-8') for p in output.split(b'\0') if p))
    secrets = configured_secrets()
    issues, manifest = [], []
    for path in paths:
        if forbidden(path):
            issues.append({'file': path, 'reason': 'sensitive or generated path'})
            continue
        raw = git('show', ':' + path) if staged else (ROOT / path).read_bytes()
        manifest.append({'file': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        for surface, data in surfaces(path, raw):
            found = {name for name, pattern in PATTERNS.items() if pattern.search(data)}
            if any(value in data for value in secrets):
                found.add('configured_secret_value')
            for reason in sorted(found):
                issues.append({'file': path, 'surface': surface, 'reason': reason})
    summary = {'passed': not issues and bool(paths), 'mode': 'staged bytes' if staged else 'publication candidates',
               'files': len(paths), 'bytes': sum(x['bytes'] for x in manifest),
               'issues': issues, 'manifest': manifest,
               'limitation': 'Known configured-secret comparison and common credential patterns; manual review is still required.'}
    artifact = ROOT / 'artifacts' / ('public-source-staged-check.json' if staged else 'public-source-check.json')
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'manifest'}))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true')
    raise SystemExit(main(parser.parse_args().staged))
