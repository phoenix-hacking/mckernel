"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact Root41 data successor of existing admission helpers. Source preparation only.
"""
from pathlib import Path
import json,hashlib,ast,difflib
D=Path(__file__).resolve().parent;E=D.parent.parent
BASE=E/'current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/abi-private-field-correction-source-1/root38-correction-admission-source-1'
P=D.parent/'root-selective-adoption-materialization-proposal-source-1';OLD=D.parent/'outer-perf-line-restore-source-1'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def save(n,t):(D/n).write_text(t)
def js(n,x):save(n,json.dumps(x,indent=2)+'\n')
profile=read(P/'PROFILE.SOURCE-ONLY.json');PROFILE=ref(P/'PROFILE.SOURCE-ONLY.json');assert PROFILE['sha256']=='721547c8246677f55290d98ae9bc161ac0356bcb4ed493bdd28cade1f99552f7'
LEDGER=ref(E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER41.json');assert LEDGER['sha256']=='0a841176630b6c4b5a6c7bb6840d342ef5da4e5f9be7a3507932f5621e7526ba'
ledger=read(LEDGER['path']);FREE=ledger['latest_accepted_free_boundary'];assert ref(FREE['path'])==FREE and FREE['sha256']=='d9e0c9fbf7eda3f3d4ccd96b3808c6609a5641e365a75f73a02da23f3a95d081';free=read(FREE['path'])
ADOPTION=ref(P/'ROOT-ACTUAL-SELECTIVE-SOURCE-ADOPTION-1/ROOT-SOURCE-ADOPTION.json');assert ADOPTION['sha256']=='67fc6e6e6fda8e690710657978fb746960deee1efe42afae40a04de27620062c'
MECH=ref(P/'independent-source-review/REVIEW.json') if (P/'independent-source-review/REVIEW.json').exists() else None
if MECH is None:
 files=list((P/'independent-source-review').glob('*.json'));assert len(files)==1;MECH=ref(files[0])
assert MECH['sha256']=='860533ab009f35dc4ac35ce8a12617d086a3e7e5294336466389fa860d5fd552'
SOURCE=ref(OLD/'independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json');assert SOURCE['sha256']=='941b98394b1600300165d97527059822f78860da5dba03eded90abf89940a801'
EXACT=free['fresh_current']['exact_observation'];exact=read(EXACT['path']);assert ref(EXACT['path'])==EXACT
assert free['owned_client_retirement']['actual_commands']==25 and len(free['fresh_current']['all28_owned_pids_and_groups_absent'])==28
# The actual new profile already has Rust/kernelC/processC/rawlink4,3new8retained.
assert len(profile['exact_commands'])==4 and sum(r['replace'] for r in profile['inputs']['objects'])==3 and sum(not r['replace'] for r in profile['inputs']['objects'])==8
origin=profile['origin_source_materialization'];assert origin['actual_producer_receipt']['sha256']=='2c419c6405deef8d6e8c2479e57f88884e34a84fec300e0aff5311ea04b944fb'
for n in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:(D/n).write_bytes((P/n).read_bytes())
context=dict(scope=__doc__.splitlines()[0],runtime_authority=None,status='EXACT_ROOT41_CLOSED_SOURCE_CONTEXT_NOT_OPERATION_AUTHORITY',profile=PROFILE,original_reviewed_profile=ref(OLD/'PROFILE.SOURCE-ONLY.json'),original_source_review=SOURCE,mechanical_metadata_and_six_file_review=MECH,ledger=LEDGER,current_free=FREE,source_adoption=ADOPTION,exact_failed_startup_observation=EXACT,actual25clients=25,actual28actors=free['fresh_current']['all28_owned_pids_and_groups_absent'],actual113_origin=origin['actual_producer_receipt'],future_nonce=None,future_resource_authority=None)
js('CLOSED-ROOT41-CONTEXT.NOT-AUTHORITY.json',context)
# Same mechanical Root38 observer wrapper, preserving all old contracts, plus
# the exact latest25client/28actor failed startup and its five current CID queries.
observer='''"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root41 exact current-boundary wrapper; no cleanup, holder, release or retry.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,time
D=Path(__file__).resolve().parent
LEDGER_REF=LEDGER_LITERAL
FREE_REF=FREE_LITERAL
EXACT_REF=EXACT_LITERAL
BASE_REF=BASE_LITERAL

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def read(p):return json.loads(Path(p).read_bytes())
def observe():
 assert os.getuid()==os.geteuid()==1000
 ledger=read(auth(LEDGER_REF));review=read(auth(FREE_REF));exact=read(auth(EXACT_REF));auth(BASE_REF)
 assert ledger['latest_accepted_free_boundary']==FREE_REF and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_POSITIVE_CORRECTED_STARTUP_FAILED_CASE_RETIREMENT_AND_CURRENT_FREE' and review['normal_owned_retirement'] is True and review['current_free'] is True
 assert review['owned_client_retirement']['actual_commands']==25 and review['owned_client_retirement']['all_exact_reaped'] is True
 commands=exact['all_actual_Docker_commands'];assert len(commands)==25 and all(x['command']['reaped'] is True and x['command']['returncode']==x['returncode'] for x in commands)
 result=review['actual_statuses']['owner_result'];assert result['status']=='FAIL' and result['absence_verified'] is True and result['lease_retained'] is False and result['secondary']==[]
 assert review['actual_statuses']['cleanup']=={'errors':[],'reaped':True}
 spec=importlib.util.spec_from_file_location('root41_retained_original_root38_observer',auth(BASE_REF));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 original=module.observe()  # Original Root38/37/36 contracts are preserved, not latest admission authority.
 actors=review['fresh_current']['all28_owned_pids_and_groups_absent'];assert len(actors)==28 and actors[:3]==[1757372,1757368,1757186]
 assert all(not Path('/proc',str(pid)).exists() for pid in actors)
 census=original['group_membership_observation'];assert not census['errors'] and not any(x['pgrp'] in actors for x in census['rows'])
 queries=[]
 for expected in exact['queries']:
  child=subprocess.run(expected['argv'],capture_output=True,text=True,timeout=15)
  assert child.returncode==expected['returncode'] and child.stdout==expected['stdout'] and child.stderr==expected['stderr']
  queries.append(dict(argv=expected['argv'],returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 assert len(queries)==5 and Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text().strip()=='0'
 return dict(status='PASS_ROOT41_EXACT_FAILED_STARTUP_CURRENT_PENDING_ROOT_ACCEPTANCE',scope=review['scope'],runtime_authority=None,observed_at=time.time(),Root41=LEDGER_REF,accepted_failed_startup=FREE_REF,original_observer=BASE_REF,original_Root38_observation=original,known_numeric_controls_absent=original['known_numeric_controls_absent']+actors,group_membership_observation=census,closed_exclusive_probes=original['closed_exclusive_probes'],new_exact25_clients_reaped=True,new_exact28_actors=actors,new_exact_container_absent=review['container'],new_exact_queries=queries,retained_failed113_container=original['retained_failed113_container'],retained_failed113_container_exit=1,artifact_acceptance=False,native_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
'''
for key,value in [('LEDGER_LITERAL',LEDGER),('FREE_LITERAL',FREE),('EXACT_LITERAL',EXACT),('BASE_LITERAL',ref(BASE/'observe_root38_current.py'))]:observer=observer.replace(key,repr(value))
save('observe_root41_current.py',observer)
# Minimal capture changes: current exact references/observer119sources, same floors.
cap=(BASE/'capture_resources.py').read_text();newcap=cap.replace("D/'observe_root38_current.py'","D/'observe_root41_current.py'").replace("OBSERVER_SHA='eb7a8d45a065ab88d94afd905c68c18d8eb04b069eac00ccd641e6b3977d0238'","OBSERVER_SHA="+repr(ref(D/'observe_root41_current.py')['sha256']))
oldbind=read(BASE/'ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');oldresource=read(BASE/'ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json')
newcap=newcap.replace(repr(oldbind['nonce_ledger']),repr(LEDGER)).replace(repr(oldbind['native_custody_clearance']),repr(FREE)).replace("len(runner.source_directory_postimages(profile))==118","len(runner.source_directory_postimages(profile))==119")
save('capture_resources.py',newcap)
# Existing materializer source, exact data substitutions; same runtime guards.
mat=(BASE/'materialize_admission.py').read_text();newmat=mat.replace("P=Path("+repr(str(BASE.parent))+')',"P=Path("+repr(str(P))+')')
assert newmat!=mat
newmat=newmat.replace('MATERIALIZE_REVIEWED_CURRENT113_ABI_CORRECTION_STATIC_INPUTS_AND_HOLDER_ONLY','MATERIALIZE_REVIEWED_CURRENT114_GLOBAL32_PERF3_STATIC_INPUTS_AND_HOLDER_ONLY')
newmat=newmat.replace(repr(oldbind['nonce_ledger']),repr(LEDGER)).replace(repr(oldbind['native_custody_clearance']),repr(FREE)).replace(repr(oldbind['source_adoption']),repr(ADOPTION))
newmat=newmat.replace('ROOT_SOURCE_ADOPTED_CURRENT113_ABI_PRIVATE_CORRECTION_NOT_BUILT','ROOT_SOURCE_ADOPTED_NEXT114_GLOBAL32_PERF3_SIX_FILES_NOT_BUILT').replace("assert context['command']==template['exact_commands'][2]","assert context['command']==template['retained_arch_producer']['command']").replace("'388c3c364f6c981a5749b058f59f94684091a12f381f785aab181508388bad05'",repr(PROFILE['sha256'])).replace('dict(runtime_authority=None,Root38=', 'dict(runtime_authority=None,Root41=')
# New metadata/six-file mechanical review is additional authenticated source input.
needle="for key in ['native_custody_clearance','independent_source_profile_review','source_adoption']:auth(b[key])"
assert needle in newmat
newmat=newmat.replace(needle,needle+"\n assert b['independent_source_profile_review']=="+repr(SOURCE)+"\n assert b['mechanical_source_profile_review']=="+repr(MECH)+"\n auth(b['mechanical_source_profile_review'])")
save('materialize_admission.py',newmat)
for name,oldtxt,newtxt in [('materialize_admission.py',mat,newmat),('capture_resources.py',cap,newcap)]:
 save(name+'.diff',''.join(difflib.unified_diff(oldtxt.splitlines(True),newtxt.splitlines(True),fromfile='reviewedRoot38/'+name,tofile='exactRoot41/'+name)))
# Known refs are actual; only Root operation authority fields remainNULL.
bind=json.loads(json.dumps(oldbind));bind.update(status='ROOT41_EXACT_CURRENT_TEMPLATE_NOT_AUTHORITY',author=None,decision=None,nonce=None,preparation_manifest=None,admission=str(E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'),nonce_ledger=LEDGER,native_custody_clearance=FREE,source_adoption=ADOPTION,independent_source_profile_review=SOURCE,mechanical_source_profile_review=MECH,expected_actual_decision='MATERIALIZE_REVIEWED_CURRENT114_GLOBAL32_PERF3_STATIC_INPUTS_AND_HOLDER_ONLY');js('ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json',bind)
resource=json.loads(json.dumps(oldresource));resource.update(schema_label='Existing BIND_CURRENT110_ACTUAL_HELD_BUILD_RESOURCES preserved; actualRoot41/free; next114fourcommands/119sources/3new8retained',nonce_ledger=LEDGER,native_custody_clearance=FREE);js('ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json',resource)
# Bind all source helpers before observations start; source manifest grants nothing.
files=[ref(x) for x in sorted(D.iterdir()) if x.is_file() and x.name not in ['PREPARATION-MANIFEST.json','SOURCE-READY.json']]
external=[PROFILE,ref(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json'),ref(P/'EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json'),SOURCE,MECH,LEDGER,FREE,ADOPTION,EXACT,ref(BASE/'observe_root38_current.py')]+[r for k,r in origin.items() if k.startswith('actual_') and isinstance(r,dict) and set(r)=={'path','bytes','sha256'}]
js('PREPARATION-MANIFEST.json',dict(scope=__doc__.splitlines()[0],status='SOURCE_MANIFEST_NOT_AUTHORITY',runtime_authority=None,files=files,external_inputs=external))
for path in D.glob('*.py'):ast.parse(path.read_text())
ready=dict(scope=__doc__.splitlines()[0],status='ROOT41_EXACT_EXISTING_ADMISSION_SOURCE_READY_NOT_EXECUTED_NOT_GRANTED',runtime_authority=None,profile=PROFILE,source_review=SOURCE,mechanical_review=MECH,source_adoption=ADOPTION,ledger=LEDGER,current_free=FREE,manifest=ref(D/'PREPARATION-MANIFEST.json'),actual25clients=25,actual28actors=28,commands=4,new_objects=3,retained_objects=8,Rust_sources=119,original_root38_mechanics=ref(BASE/'SOURCE-READY.json'),source_helpers_valid_Python=True,actual_queries_guards_resources_holders_compilers_workloads=0,Root_actual_nonce=None,Root_actual_resource_input=None,Root_actual_execution_review=None)
js('SOURCE-READY.json',ready);print(json.dumps(dict(status=ready['status'],manifest=ready['manifest'],profile=PROFILE)))
