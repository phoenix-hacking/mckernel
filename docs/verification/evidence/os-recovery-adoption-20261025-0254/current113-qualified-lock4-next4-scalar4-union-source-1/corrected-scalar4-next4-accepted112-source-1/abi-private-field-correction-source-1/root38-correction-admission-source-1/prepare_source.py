"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Only Root38 actual-boundary binding changes; no operational calls or source audit.
"""
import ast,copy,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;E=D.parents[3];PREV=P/'root37-correction-admission-source-1'
R=E/'ROOT-CURRENT113-ABI-PRIVATE-CORRECTION-BUILD-ADMISSION-1'
LEDGER=E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER38.json'
ADOPT=P/'root-source-adoption-1/ROOT-SOURCE-ADOPTION.json'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return write(n,json.dumps(x,indent=2)+'\n')
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
assert ref(LEDGER)['sha256']=='9b3d64ab84d59b6abbc7b1df05cf4034a9d53a2dd1cfb4d76013f554f0b7e282' and ref(LEDGER)['bytes']==4390
FREE=auth(read(LEDGER)['latest_accepted_free_boundary']);assert ref(FREE)['sha256']=='9d3aa7ff83c3bec493a575a8035ce59963e92fb2a82d549febd89ab34c8ce066'
assert ref(ADOPT)['sha256']=='b09e93956f599c6c942717ae93abc63fa7b830255abb35d5df34252d4c15e685'
p=read(P/'PROFILE.SOURCE-ONLY.json');assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256'].startswith('388c3c36')
assert not R.exists()
observer='''"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow Root38 wrapper preserves Root37 failed-container contract and adds exactV3.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,time
LEDGER=Path(%r)
FREE=Path(%r)
BASE=Path(%r)
REFS=%r

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def read(p):return json.loads(Path(p).read_bytes())
def observe():
 assert os.getuid()==os.geteuid()==1000
 for r in REFS:auth(r)
 ledger=read(LEDGER);review=read(FREE)
 assert ledger['latest_accepted_free_boundary']==ref(FREE) and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_POSITIVE_F05_V3_PRE_GUEST_FAILED_BATCH_RETIREMENT_AND_CURRENT_FREE' and review['normal_owned_retirement'] is True and review['current_free'] is True
 clients=review['owned_client_retirement'];assert clients['count']==25 and clients['all_exact_reaped'] is True and len(clients['commands'])==25
 assert all(row['command']['reaped'] is True and row['command']['returncode']==row['returncode'] for row in clients['commands'].values())
 snapshot=read(auth(review['evidence']['RETAINED-OWNER-SNAPSHOT.json']));result=snapshot['owner_records']['result.json']
 assert result['status']=='FAIL' and result['absence_verified'] is True and result['lease_retained'] is False and result['secondary']==[] and result['container']==review['container']
 spec=importlib.util.spec_from_file_location('root38_retained_root37_observer',BASE)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 original=module.observe()
 # Prior28controls+two failedbuild actors and retained363375Exit1 remain distinct.
 assert len(original['known_numeric_controls_absent'])==30 and original['retained_container_exit']==1
 actors=review['fresh_current']['all_28_owned_pids_and_groups_absent'];assert len(actors)==28 and actors[:3]==[1735781,1735836,1735840]
 assert all(not Path('/proc',str(pid)).exists() for pid in actors)
 census=original['group_membership_observation'];assert not census['errors'] and not any(row['pgrp'] in actors for row in census['rows'])
 queries=[]
 for retained in review['fresh_current']['container_queries']:
  child=subprocess.run(retained['argv'],capture_output=True,text=True,timeout=15)
  assert child.returncode==retained['returncode'] and child.stdout==retained['stdout'] and child.stderr==retained['stderr']
  queries.append(dict(argv=retained['argv'],returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 assert len(queries)==5 and Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text().strip()=='0'
 return dict(status='PASS_ROOT38_V3_PRE_GUEST_FAILED_RETIREMENT_CURRENT_PENDING_ROOT_ACCEPTANCE',scope=review['scope'],runtime_authority=None,observed_at=time.time(),Root38=ref(LEDGER),accepted_V3_retirement=ref(FREE),original_observer=ref(BASE),original_Root37_observation=original,known_numeric_controls_absent=original['known_numeric_controls_absent']+actors,group_membership_observation=census,closed_exclusive_probes=original['closed_exclusive_probes'],new_V3_25_clients_reaped=True,new_V3_exact_container_absent=review['container'],new_V3_actor_controls=actors,new_V3_queries=queries,retained_failed113_container=original['retained_stopped_container'],retained_failed113_container_exit=1,artifact_acceptance=False,native_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
'''%(str(LEDGER),str(FREE),str(PREV/'observe_root37_current.py'),[ref(LEDGER),ref(FREE),ref(PREV/'observe_root37_current.py')])
write('observe_root38_current.py',observer)
oldledger=E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER37.json';oldfree=auth(read(oldledger)['latest_accepted_free_boundary'])
capture=(PREV/'capture_resources.py').read_text();capture=once(capture,"OBSERVER=D/'observe_root37_current.py'","OBSERVER=D/'observe_root38_current.py'")
capture=once(capture,"OBSERVER_SHA='"+ref(PREV/'observe_root37_current.py')['sha256']+"'","OBSERVER_SHA='"+ref(D/'observe_root38_current.py')['sha256']+"'")
capture=once(capture,repr(ref(oldledger)),repr(ref(LEDGER)));capture=once(capture,repr(ref(oldfree)),repr(ref(FREE)));write('capture_resources.py',capture)
materializer=(PREV/'materialize_admission.py').read_text();materializer=once(materializer,repr(ref(oldledger)),repr(ref(LEDGER)));materializer=once(materializer,repr(ref(oldfree)),repr(ref(FREE)))
materializer=once(materializer," adoption=read(b['source_adoption']['path'])\n"," assert b['source_adoption']=="+repr(ref(ADOPT))+"\n adoption=read(b['source_adoption']['path'])\n")
materializer=once(materializer,'Root37=b[\'nonce_ledger\']','Root38=b[\'nonce_ledger\']');write('materialize_admission.py',materializer)
for n in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:write(n,(PREV/n).read_bytes())
bindings=read(PREV/'ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');bindings.update(status='ROOT38_ACTUAL_BOUNDARY_TEMPLATE_NOT_AUTHORITY',nonce_ledger=ref(LEDGER),native_custody_clearance=ref(FREE),source_adoption=ref(ADOPT));save('ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json',bindings)
resource=read(PREV/'ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json');resource.update(nonce_ledger=ref(LEDGER),native_custody_clearance=ref(FREE));save('ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json',resource)
# Rewrite only private helper locations in the already complete resource/publisher sequence.
sequence=read(PREV/'COMPLETE-ROOT-ENTRY-RESOURCE-PUBLISHER-SEQUENCE.NOT-GRANTED.json')
def relocate(v):
 if isinstance(v,str):return v.replace(str(PREV),str(D))
 if isinstance(v,list):return [relocate(x) for x in v]
 if isinstance(v,dict):return {k:relocate(x) for k,x in v.items()}
 return v
sequence=relocate(sequence);sequence['status']='ROOT38_COMPLETE_PREWRITTEN_SOURCE_ENTRY_RESOURCE_PUBLISHER_SEQUENCE_NOT_EXECUTED';sequence['latest_actual_boundary']=dict(Root38=ref(LEDGER),free_V3=ref(FREE),separate_prior_failed113_retirement=ref(oldfree))
save('COMPLETE-ROOT-ENTRY-RESOURCE-PUBLISHER-SEQUENCE.NOT-GRANTED.json',sequence)
helpers=[]
for n in ['observe_root38_current.py','capture_resources.py','materialize_admission.py','run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 oldpath=PREV/('observe_root37_current.py' if n=='observe_root38_current.py' else n);ast.parse((D/n).read_text(),filename=n)
 diff=write('helper-diffs/'+n+'.diff',''.join(difflib.unified_diff(oldpath.read_text().splitlines(keepends=True),(D/n).read_text().splitlines(keepends=True),fromfile='Root37/'+oldpath.name,tofile='Root38/'+n)))
 helpers.append(dict(name=n,predecessor=ref(oldpath),successor=ref(D/n),diff=ref(diff)))
save('MINIMAL-BOUNDARY-DERIVATION.json',dict(scope=SCOPE,runtime_authority=None,helpers=helpers,only_boundary_delta='Root38/9d3V3removedCID and25clients/28actors added around exact retainedRoot37/070e/stopped363375 proof. Fourcompilerargv/118oneleafmap/eightobjects/origin unchanged.',Root_source_adoption=ref(ADOPT),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),actual_queries=0,actual_guards=0,all_actual_calls=0))
context=read(PREV/'CLOSED-ROOT37-CONTEXT.NOT-AUTHORITY.json');context['Root38']=ref(LEDGER);context['latest_accepted_free']=ref(FREE);context['prior_Root37_retirement_preserved']=context.pop('Root37');context['actual_Root_source_adoption']=ref(ADOPT);context['V3_removed_container']=read(FREE)['container'];context['source_helpers_current_boundary']='Root38latestV3free; prior070e/stopped363375 independently retained'
save('CLOSED-ROOT38-CONTEXT.NOT-AUTHORITY.json',context)
files=[ref(q) for q in D.rglob('*') if q.is_file() and q.name not in ['prepare_source.py','PREPARATION-MANIFEST.json','SOURCE-READY.json']]
external=[ref(P/'PROFILE.SOURCE-ONLY.json'),ref(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json'),ref(P/'SOURCE-READY.json'),p['inputs']['source_directory_exports'][0]['manifest'],ref(p['reuse_descriptor']),p['origin_source_materialization']['actual_producer_receipt'],p['origin_source_materialization']['actual_generated_header'],ref(LEDGER),ref(FREE),ref(ADOPT),ref(PREV/'observe_root37_current.py')]
for row in external:auth(row)
save('PREPARATION-MANIFEST.json',dict(scope=SCOPE,runtime_authority=None,status='ROOT38_MINIMAL_CORRECTED113_BOUNDARY_SOURCE_SUCCESSOR',files=files,external_inputs=external,all_actual_calls=0))
save('SOURCE-READY.json',dict(scope=SCOPE,status='ROOT38_CORRECTED113_SINGLE_RETRY_BOUNDARY_SOURCE_READY_NOT_RELEASED',runtime_authority=None,manifest=ref(D/'PREPARATION-MANIFEST.json'),closed_context=ref(D/'CLOSED-ROOT38-CONTEXT.NOT-AUTHORITY.json'),boundary_derivation=ref(D/'MINIMAL-BOUNDARY-DERIVATION.json'),complete_sequence=ref(D/'COMPLETE-ROOT-ENTRY-RESOURCE-PUBLISHER-SEQUENCE.NOT-GRANTED.json'),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),Root38=ref(LEDGER),latest_free=ref(FREE),Root_source_adoption=ref(ADOPT),commands=4,new_objects=3,retained_objects=8,Rust_sources=118,passed_prefix=0,correction_count=1,genuine_origin_reused=p['origin_source_materialization']['actual_producer_receipt'],all_actual_calls=0,canonical_or_Git_edits=0))
print(json.dumps(dict(status='ROOT38_SOURCE_SUCCESSOR_READY_NO_OPERATIONS',ready=ref(D/'SOURCE-READY.json'),manifest=ref(D/'PREPARATION-MANIFEST.json'))))
