"""M03-only offline derivative of the complete tested HOST66 archive.

The accepted archive is retained byte-for-byte as the BASE. The existing
canonical overlay producer appends its standard six records. The final map may
change only the bytes/size of init; no app/module/image/mcexec mix.
No process, module, VM or application is started here.
"""
from pathlib import Path
import copy
import gzip
import hashlib
import importlib.util
import json
import os

HERE = Path(__file__).resolve().parent
PARENT = Path('/home/holden/mckernel-work/host-preparation/phase5-m03-native-app-binding-20261020-1/manifest-key-correction-1/manifest.json')
PARENT_SHA = 'e414ac0854bf705da2603bde1c630904f8877f14ca3645c1d1c146627e4f333e'
OVERLAY = Path('/home/holden/mckernel/scripts/application-tests/native_diagnostic_overlay.py')
OVERLAY_SHA = '46d41bc0727fa77e4126e739f25352c53eadf2e1fa8e23ef06a6e46c9b3ba27d'
CHANGED = frozenset(('init',))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def ref(path):
    path = Path(path)
    st = path.lstat()
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                size=st.st_size, mode=st.st_mode)

def exact(row):
    if ref(row['path']) != row:
        raise ValueError('changed exact source: ' + row['path'])

def retained_map(old, new):
    if set(old) != set(new):
        raise ValueError('M03 no archive member additions/removals')
    for name in old:
        omit = {'size', 'sha256'} if name in CHANGED else set()
        if ({k:v for k,v in old[name].items() if k not in omit} !=
                {k:v for k,v in new[name].items() if k not in omit}):
            raise ValueError('M03 retained member metadata/bytes: ' + name)

def derive(ov, base, payload, collector, mcexec, output, expected_map):
    """Consumed transformation; small fixtures exercise this same body."""
    for row in (base, payload, collector, mcexec):
        exact(row)
    raw = gzip.decompress(Path(base['path']).read_bytes())
    before, _ = ov.parse_newc(raw)
    if ov._manifest(ov._replay_records(before)) != expected_map:
        raise ValueError('M03 complete accepted BASE final map')
    result = ov.build_overlay(base['path'], payload['path'], collector['path'],
        mcexec['path'], str(output), collector_sha256=collector['sha256'],
        mcexec_sha256=mcexec['sha256'], base_sha256=base['sha256'],
        base_size=base['size'], base_cpio_sha256=hashlib.sha256(raw).hexdigest(),
        base_cpio_size=len(raw), payload_sha256=payload['sha256'])
    retained_map(expected_map, result['final_map'])
    observed = gzip.decompress(Path(output).read_bytes())
    if observed[:len(raw)] != raw:
        raise ValueError('M03 original complete archive prefix changed')
    for row in (base, payload, collector, mcexec):
        exact(row)
    return result

def write(path, data):
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())

def js(path, value):
    write(path, (json.dumps(value, sort_keys=True, indent=2)+'\n').encode())

def stage(collector, output):
    """collector must be an exact freshly accepted M03 compile output row."""
    if hashlib.sha256(PARENT.read_bytes()).hexdigest() != PARENT_SHA:
        raise ValueError('M03 immutable tested parent manifest')
    if hashlib.sha256(OVERLAY.read_bytes()).hexdigest() != OVERLAY_SHA:
        raise ValueError('M03 accepted archive engine')
    binding = json.loads((HERE/'M03-FROZEN-CASE-BINDING.json').read_bytes())
    if hashlib.sha256(Path('/home/holden/mckernel-work/host-preparation/phase5-m03-prepayload-helper-export-correction-20261020-1/candidate/native_diagnostic.py').read_bytes()).hexdigest() != '1f9f46a3b3d7ed89b064bb91b32a63bd82259706216dee0799c81fdf8a5dc149':
        raise ValueError('exact source-owner c564 evaluator binding')
    nd = load('m03_typed_evaluator', Path('/home/holden/mckernel-work/host-preparation/phase5-m03-prepayload-helper-export-correction-20261020-1/candidate/native_diagnostic.py'))
    ov = load('m03_accepted_overlay', OVERLAY)
    parent = json.loads(PARENT.read_bytes())
    for row in (*parent['artifacts'].values(), *parent['modules'], *parent['staging'].values()):
        exact(row)
    for name, row in binding['matched_artifacts'].items():
        if parent['artifacts'][name] != row:
            raise ValueError('M03 matched artifact: '+name)
    if parent['modules'] != binding['matched_modules'] or parent['profile'] != binding['matched_profile']:
        raise ValueError('M03 whole tested module/profile tuple')
    if parent['staging']['derived_initramfs'] != binding['accepted_stage_base']:
        raise ValueError('M03 complete tested archive authority')
    nd._ref(collector, 'fresh M03 collector')
    payload = binding['payload_artifact']; exact(payload)
    old_overlay = json.loads(Path(parent['staging']['overlay_manifest']['path']).read_bytes())
    out = Path(output); out.mkdir(mode=0o700)
    derived = out/'m03.cpio.gz'
    overlay = derive(ov, binding['accepted_stage_base'], payload, collector,
                     binding['matched_artifacts']['mcexec'], derived, old_overlay['final_map'])
    js(out/'overlay-manifest.json', overlay)
    m = copy.deepcopy(parent)
    m['case_id'] = binding['case_id']; m['payload'] = binding['payload']
    m['artifacts']['payload'] = payload
    m['artifacts']['initramfs'] = m['artifacts']['root_base'] = binding['accepted_stage_base']
    m['staging'] = dict(base_initramfs=binding['accepted_stage_base'], collector=collector,
        derived_initramfs=ref(derived), overlay_manifest=ref(out/'overlay-manifest.json'),
        overlay_source=ref(OVERLAY))
    nd._validate_manifest(m)
    js(out/'manifest.json', m)
    used = sum(f.stat().st_size for f in out.iterdir() if f.is_file())
    if used > 64 << 20:
        raise ValueError('existing64MiB stage cap')
    js(out/'stage-result.json', dict(status='M03_STAGE_ONLY', manifest=ref(out/'manifest.json'),
        parent=ref(PARENT), original_prefix_unchanged=True,
        only_final_changed_members=sorted(CHANGED), stage_bytes=used,
        guest_runs=0, application_launches=0, native_acceptance=False))
    return ref(out/'manifest.json')

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--collector-ref', required=True,
                    help='root-frozen accepted compiled M03 collector exact JSON row')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    print(json.dumps(stage(json.loads(Path(args.collector_ref).read_bytes()), args.output)))
