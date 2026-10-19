#!/usr/bin/python3
"""One affected records selector fixture: complete dispatcher31 sample.
Actual records() body and actual file IO; synthetic root/current FP scope only.
No root, real records, archives, observer or unaffected fixture replays.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'exact120.py'
PROTOTYPE = json.loads((BASE / 'control-record-registry.json').read_text())
SAMPLE = json.loads((BASE / 'current-records-predicate-nonregular-ordinary-1.json').read_text())['nonregular']


def module():
    spec = importlib.util.spec_from_file_location('actual_selector', SOURCE)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def setup(out):
    out.mkdir(); root = out / 'scratch'; root.mkdir(); scope = out / 'current-fp'; scope.mkdir()
    m = module(); registry = copy.deepcopy(PROTOTYPE)
    controls = {}
    for name, role in registry['controls'].items():
        p = (root if name.startswith('/home/holden/mckernel-work/scratch/') else scope) / Path(name).name
        item = dict(role)
        if item['presence'] == 'required':
            body = ('fixture:' + p.name).encode(); p.write_bytes(body)
            item['metadata'] = m.meta(p.lstat())
            item['sha256'] = hashlib.sha256(body).hexdigest() if item['sha256'] is not None else None
        controls[str(p)] = item
    registry['controls'] = controls
    sample = []
    for original in SAMPLE:
        p = root / original['name']; p.mkdir()
        s = p.lstat(); sample.append({'name':p.name,'device':s.st_dev,'inode':s.st_ino,'type':16384})
    registry['incidental_sample']['rows'] = sample
    q = root / Path(registry['historical_quarantine_path']).name
    child = q / 'native-exact-candidate-operational-exclusion-exportset-26.json'; child.write_bytes(b'historical-preserved')
    m.RETAINED_QUARANTINE = {'path':str(q),'metadata':m.meta(q.lstat()),'child_name':child.name,
                             'child_metadata':m.meta(child.lstat()),'child_sha256':hashlib.sha256(child.read_bytes()).hexdigest()}
    registry['historical_quarantine_path'] = str(q)
    req = scope / 'image-request.json'
    fields = {field:str(scope / Path(value).name) for field,value in registry['fp_request']['guard_fields'].items()}
    req.write_text(json.dumps(fields))
    s = scope.lstat()
    registry['fp_request'] = {'path':str(req),'metadata':m.meta(req.lstat()),'sha256':hashlib.sha256(req.read_bytes()).hexdigest(),
                              'guard_fields':fields,'parent_identity':{'path':str(scope),'device':s.st_dev,'inode':s.st_ino,'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid}}
    rp = out / 'registry.json'; rp.write_text(json.dumps(registry))
    m.ROOT = root; m.CONTROL_REGISTRY_PATH = rp; m.CONTROL_REGISTRY_SHA256 = hashlib.sha256(rp.read_bytes()).hexdigest()
    return m, root, scope, registry


def run(out, case):
    m, root, scope, registry = setup(out)
    expected = None
    if case == 'unknown-real-control-path':
        (root / 'native-exact-mckernel-image-lease-unregistered.json').write_bytes(b'unknown authority')
        expected = 'unknown declared control path'
    elif case == 'known-control-nonregular':
        path = root / 'native-exact-build-lease-67589154-1.json'
        path.rename(out / 'original-control'); path.mkdir()
        expected = 'declared control not regular'
    elif case == 'stale-known-control-identity':
        path = root / 'native-exact-build-lease-67589154-1.json'
        body = path.read_bytes(); path.rename(out / 'original-control'); path.write_bytes(body)
        expected = 'declared control identity drift'
    elif case == 'external-current-fp-guard-present':
        (scope / 'common-exclusion.json').mkdir()
        expected = 'current control must be absent'
    elif case == 'scoped-evidence-identity-drift':
        path = root / SAMPLE[1]['name']; path.rename(out / 'original-evidence'); path.mkdir()
        expected = 'scoped evidence identity drift'
    before = {str(p):m.meta(p.lstat()) for p in out.rglob('*')}
    error = None
    try:
        actual = m.records()
        assert len(actual['scoped_evidence_metadata']) == 31
        assert len(actual['controls']) == len(registry['controls'])
        assert str(scope / 'common-exclusion.json') in actual['controls']
        assert str(scope / 'image-lease.json') in actual['controls']
        for row in SAMPLE:
            assert not m.control_shape(row['name']), row['name']
    except BaseException as exc:
        error = repr(exc)
    after = {str(p):m.meta(p.lstat()) for p in out.rglob('*')}
    assert before == after, 'records() mutated synthetic data'
    ok = error is None if expected is None else error is not None and expected in error
    row = {'status':'PASS' if ok else 'FAIL','case':case,'expected':expected,'error':error,
           'complete_current_nonregular_sample':31,'production_body':'records()','boundary_mocks':False,'inventory_unchanged':True}
    (out / 'result.json').write_text(json.dumps(row,indent=2)+'\n')
    if not ok:
        raise RuntimeError('stop first affected selector failure: '+repr(row))
    return row


def main():
    p = argparse.ArgumentParser(); p.add_argument('--output',required=True); a=p.parse_args()
    out=Path(a.output); out.mkdir(exist_ok=False); results=[]
    try:
        for case in ('complete-current31-and-controls','unknown-real-control-path','known-control-nonregular','stale-known-control-identity','external-current-fp-guard-present','scoped-evidence-identity-drift'):
            results.append(run(out/case,case))
    except BaseException as exc:
        (out/'result.json').write_text(json.dumps({'status':'FAIL_PRESERVED','cases':results,'error':repr(exc)},indent=2)+'\n')
        raise
    result={'status':'PASS_ACTUAL_RECORDS_SELECTOR_COMPLETE31_SYNTHETIC_ONLY','cases':results,'interpreter':sys.executable,'version':sys.version,
            'real_observer_replayed':False,'unaffected_fixtures_replayed':False,'actual31_contents_read':False}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'cases':len(results),'sample_per_case':31,'version':sys.version.split()[0]}))


if __name__=='__main__':main()
