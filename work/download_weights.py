import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE.parent / 'models'
HF = BASE / 'work' / 'hf-cli-env' / 'bin' / 'hf'
kind = sys.argv[1]
settings = {
    'h3': ('h3-blobs.json', 'MiniMax-H3'),
    'krea': ('krea-unsloth-blobs.json', 'Krea-2-Turbo'),
}
metadata_file, folder = settings[kind]
meta = json.loads((BASE / 'work' / metadata_file).read_text())
destination = OUT / folder
destination.mkdir(parents=True, exist_ok=True)
if kind == 'h3':
    chosen = [f for f in meta['siblings'] if f['rfilename'].startswith(('FL2VA/', 'Ref2VA/', 'docs/')) or f['rfilename'] in ('README.md', 'LICENSE', 'model_index.json')]
elif kind == 'krea':
    chosen = [f for f in meta['siblings'] if f['rfilename'] in ('turbo.safetensors', 'vae/config.json', 'vae/diffusion_pytorch_model.safetensors', 'README.md', 'LICENSE.pdf')]
groups = {}
for entry in chosen:
    digest = entry.get('lfs', {}).get('sha256') or entry['blobId']
    groups.setdefault(digest, []).append(entry)
status_path = OUT / (kind + '-download-status.json')
plan_path = OUT / (kind + '-download-manifest.json')
plan = {'repo_id': meta['id'], 'revision': meta['sha'], 'destination': str(destination), 'files': chosen, 'unique_bytes': sum(g[0]['size'] for g in groups.values())}
if kind == 'h3':
    plan['format'] = 'original FL2VA and Ref2VA bundles'
    plan['includes_bundled_h3_encoder'] = True
    plan['diffusers_copies_selected'] = False
if kind == 'krea':
    upstream = json.loads((BASE / 'work' / 'krea-blobs.json').read_text())
    originals = {f['rfilename']: f for f in upstream['siblings']}
    for f in chosen:
        if f['rfilename'].endswith('.safetensors') or f['rfilename'] in ('vae/config.json', 'LICENSE.pdf'):
            original = originals[f['rfilename']]
            identity = lambda item: item.get('lfs', {}).get('sha256') or item['blobId']
            if identity(original) != identity(f) or original['size'] != f['size']:
                raise RuntimeError('Mirror differs from official file: ' + f['rfilename'])
    plan['upstream_repo_id'] = upstream['id']
    plan['upstream_revision'] = upstream['sha']
    plan['upstream_weights_hash_match'] = True
plan_path.write_text(json.dumps(plan, indent=2) + '\n')

def status(stage, **extra):
    report = {'repo_id': meta['id'], 'revision': meta['sha'], 'stage': stage, 'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'destination': str(destination), 'unique_bytes': plan['unique_bytes'], **extra}
    temporary = status_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2) + '\n')
    temporary.replace(status_path)
    print(stage, extra, flush=True)

env = os.environ.copy()
env['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
env['HF_XET_CACHE'] = str(BASE / 'work' / 'hf-xet-cache')
env['HF_HUB_DOWNLOAD_TIMEOUT'] = '120'
command = [str(HF), 'download', meta['id'], *[g[0]['rfilename'] for g in groups.values()], '--revision', meta['sha'], '--local-dir', str(destination), '--max-workers', '4', '--quiet']
status('downloading', pid=os.getpid())
log_path = BASE / 'work' / (kind + '-download.log')
with log_path.open('a') as log:
    result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
if result.returncode:
    status('download_failed', returncode=result.returncode, log=str(log_path))
    sys.exit(result.returncode)
status('verifying')
verified = 0
for digest, entries in groups.items():
    source = destination / entries[0]['rfilename']
    if source.stat().st_size != entries[0]['size']:
        status('verification_failed', file=entries[0]['rfilename'], reason='size mismatch')
        sys.exit(2)
    is_lfs = bool(entries[0].get('lfs'))
    hasher = hashlib.sha256() if is_lfs else hashlib.sha1()
    if not is_lfs:
        hasher.update(f'blob {source.stat().st_size}\0'.encode())
    with source.open('rb') as stream:
        while chunk := stream.read(16 * 1024 * 1024):
            hasher.update(chunk)
    if hasher.hexdigest() != digest:
        status('verification_failed', file=entries[0]['rfilename'], reason='checksum mismatch')
        sys.exit(2)
    verified += 1
    for duplicate in entries[1:]:
        target = destination / duplicate['rfilename']
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            os.link(source, target)
        elif not os.path.samefile(source, target):
            status('verification_failed', file=duplicate['rfilename'], reason='unexpected existing duplicate; preserved')
            sys.exit(2)
    if verified % 10 == 0:
        status('verifying', unique_files_verified=verified, unique_files_total=len(groups))
status('complete', files_verified=len(chosen), unique_files_verified=verified, checksums='SHA256 for LFS; Git blob SHA1 for metadata', shared_hardlinks=sum(len(g)-1 for g in groups.values()))
