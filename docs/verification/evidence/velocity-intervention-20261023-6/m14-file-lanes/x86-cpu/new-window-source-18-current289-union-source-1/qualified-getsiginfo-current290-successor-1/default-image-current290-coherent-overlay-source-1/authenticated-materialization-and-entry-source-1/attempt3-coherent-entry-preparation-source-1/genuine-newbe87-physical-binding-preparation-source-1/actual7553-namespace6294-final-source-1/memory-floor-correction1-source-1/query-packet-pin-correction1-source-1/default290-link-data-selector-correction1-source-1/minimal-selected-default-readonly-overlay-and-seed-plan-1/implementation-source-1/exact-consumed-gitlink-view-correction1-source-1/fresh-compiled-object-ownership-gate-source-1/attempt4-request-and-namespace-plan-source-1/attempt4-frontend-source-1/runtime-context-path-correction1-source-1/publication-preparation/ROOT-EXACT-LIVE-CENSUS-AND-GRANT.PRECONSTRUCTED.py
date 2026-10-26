"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
D=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/runtime-context-path-correction1-source-1')
r=json.loads(next((D/'preexecution-fixture-capture-name-correction1-source-1').glob('READY*json')).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
assert ref(r['caller']['path'])==r['caller'] and ref(r['config']['path'])==r['config']
spec=importlib.util.spec_from_file_location('exact_attempt4_caller',r['caller']['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
cfg=json.loads(Path(r['config']['path']).read_bytes());root=Path(cfg['capture_root']);pub=D/'publication-preparation'
assert os.getuid()==os.geteuid()==1000
if sys.argv[1]=='census':
 assert ref(r['corrected_census_observer']['path'])==r['corrected_census_observer']
 raise SystemExit(subprocess.call(['/usr/bin/taskset','-c','2-5',cfg['interpreter']['path'],'-I','-B',r['corrected_census_observer']['path']]))
assert sys.argv[1]=='grant'
ready=m.strict(root/'INDEPENDENT-EXECUTION-REVIEW-READY.json');payload=m.strict(m.authenticate(ready['payload']));reviewpath=pub/'INDEPENDENT-ACTUAL-PAYLOAD-EXECUTION-REVIEW.json';review=m.strict(reviewpath)
assert review['existing_cleanup_source']==r['cleanup']
assert time.time()-ready['five_end_epoch']<=120 and time.time()<cfg['deadline_epoch']-30
assert m.birth(ready['holder']['pid'])==ready['holder']['starttime']
grant=dict(author='/root',decision='GRANT_ONE_CURRENT290_IMAGE_OWNER',caller_sha256=r['caller']['sha256'],payload=ready['payload'],owner_argv=cfg['commands']['owner_entry_unchanged']['argv'],holder=ready['holder'],actual_no_other_heavy=True,no_heavy_since_latest_physical=True,operation_scope=cfg['operation_scope'],independent_review=ref(reviewpath))
m.execution_grant(grant,review,ready['payload'],payload,ready['holder'],grant['owner_argv'],r['caller']['sha256'],cfg,r['config']['sha256'])
m.publish(root/'ROOT-EXECUTION-GRANT.json',grant)
print('Published exact one-owner grant; genuine current reviewed payload only')
