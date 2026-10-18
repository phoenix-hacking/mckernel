from pathlib import Path
import importlib.util,json,hashlib
P=Path(__file__).resolve().parent

def module(n):
 s=importlib.util.spec_from_file_location(n.replace('.','_'),P/n);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
r=module('retention_observer.py');j=module('retained_join.py');m=r.load(r.ENGINE);o=module('observe_reset_image_retirement.py');physical=json.loads((P/'actual-physical-bindings.json').read_bytes());rows=[]
for kind,fixed in r.ARTIFACT_PATHS.items():
 p=Path(fixed['original']);original=j.join_one(m,m.observe_identity(p));rows.append(dict(kind=kind,action=fixed['action'],original=original,retained=fixed['retained']))
assert len(rows)==15 and sum(x['original']['size'] for x in rows)<=r.PROFILE['max_total_bytes'];assert all(x['original']['nlink']==1 and x['original']['uid']==1000 and x['original']['device']==66306 for x in rows)
assert {x['kind'] for x in rows if x['action']=='reuse'}=={'syscall.c.o','process.c.o','mckernel_rust.o','mckernel.img'}
# Explicit absent retained authorities, not fabricated descriptors or permitted reuse.
proposal=dict(schema='mckernel.rust-image.finite-retention-release.v1',status='NOT_RELEASED',author='clear_debugreg_terminal_prepare_1726',boot_id=r.BOOT,output=str(r.DEST),resource_profile=r.PROFILE,observer=ref(P/'retention_observer.py'),engine=ref(r.ENGINE),join=ref(r.JOIN),source_review=None,execution_review=None,physical_join={k:{f:physical[k][f] for f in ('path','sha256')} for k in ('guard','owner','postjoin')},artifacts=rows)
(P/'retention-execution-release-DRAFT.json').write_text(json.dumps(proposal,indent=2,sort_keys=True)+'\n')
report=dict(status='DRAFT_ACTUAL_ORIGINALS15_PENDING_FOUR_REUSE_AUTHORITIES_AND_RELEASE',originals=15,reuse=4,copy=11,total_original_bytes=sum(x['original']['size'] for x in rows),new_copy_bytes=sum(x['original']['size'] for x in rows if x['action']=='copy'),artifacts=rows,pending_reused_authority=[x['kind'] for x in rows if x['action']=='reuse'],frozen_engine_sha256=sha(r.ENGINE),root=False,docker=False,copy_executed=False,cleanup=False)
(P/'retention-fifteen-actual-inputs.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
try:r.validate(proposal)
except RuntimeError as e:assert str(e)=='finite retention not released'
else:raise AssertionError('draft authorized')
try:r.validate_artifact_rows(rows)
except RuntimeError as e:assert str(e)=='existing retained descriptor authority required'
else:raise AssertionError('unobserved retained descriptors accepted')
print(json.dumps({k:report[k] for k in ('status','originals','reuse','copy','total_original_bytes','new_copy_bytes')}))
