"""Data-only successor preparation. Never imports or executes candidate code."""
from pathlib import Path
import ast,copy,difflib,hashlib,json,shutil,uuid
R=Path(__file__).resolve().parent
OLD=Path('/home/holden/mckernel-work/host-preparation/scheduler-current-whole-consumer-compile-preparation-20261021-1')
ROOT=Path('/home/holden/mckernel')
INTEGRATION=Path('/home/holden/mckernel-work/host-preparation/private-syscall-rust-next-20261021-2/integration-preparation-1/ROOT-ACTUAL-COHERENT-UNION-INTEGRATION.json')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def read(n):return json.loads((OLD/n).read_text())
def save(n,d):
 with (R/n).open('x') as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n')
assert sha(INTEGRATION)=='9216b6ec8254cc6bd98057381b8cd7fc5e03b5802e8cd28fd212dd23c2ecc41c'
integration=json.loads(INTEGRATION.read_text())
manifest=read('source-manifest.json'); prior=copy.deepcopy(manifest)
assert manifest['source_identity']=='25999bf8b2d57ccc64e8c1d7da9107a8e4972179b2d802a9bcb8db0df4c66814'
changes=[]
for row in manifest['rows']:
 rel=row['relative']
 if rel not in integration['files']:continue
 old=copy.deepcopy(row);live=ROOT/rel;f=integration['files'][rel]
 assert row['sha256']==f['preimage'] and sha(live)==f['integrated']
 dst=R/'source-overlays'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(live,dst)
 row.update(origin=str(dst),bytes=dst.stat().st_size,sha256=sha(dst));changes.append({'relative':rel,'old':old,'new':copy.deepcopy(row)})
assert len(changes)==2 and sum(a==b for a,b in zip(prior['rows'],manifest['rows']))==158
identity_payload=[{k:r[k] for k in ('relative','bytes','sha256')} for r in manifest['rows']]
identity=hashlib.sha256(json.dumps(identity_payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
manifest.update(source_identity=identity,source_state='Accepted scheduler current160 recipe with only reviewed NUMA C/Rust policy replacements;158 literal row dictionaries unchanged',status='NUMA_CURRENT160_RECIPE_ONLY_NOT_MATERIALIZED')
save('source-manifest.json',manifest)
for n in ['materialize_sources.py','current_fullcrate_owner.py','actual_retirement_consumer_and_FAM_assertions.h']:shutil.copy2(OLD/n,R/n)
old_driver=(OLD/'compile_retirement_current_driver.py').read_text()
new_symbol='syscall_vm_range_policy_search_body_result'
tree=ast.parse(old_driver); edits=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('RUST_DEFINITIONS','RULES') for t in node.targets):
  segment=ast.get_source_segment(old_driver,node)
  # New helper participates in exactly the same selected/policy-off boundaries as settid.
  updated=segment.replace("'syscall_settid_body_result'","'syscall_settid_body_result','"+new_symbol+"'")
  edits.append((node.lineno,node.end_lineno,updated))
lines=old_driver.splitlines(keepends=True)
for start,end,updated in reversed(edits):lines[start-1:end]=[updated+'\n']
driver=''.join(lines);(R/'compile_retirement_current_driver.py').write_text(driver)
def without_data(s):
 t=ast.parse(s);t.body=[n for n in t.body if not(isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in ('RULES','RUST_DEFINITIONS') for x in n.targets))];return ast.dump(t,include_attributes=False)
assert without_data(driver)==without_data(old_driver)
(R/'driver-DATA-only.patch').write_text(''.join(difflib.unified_diff(old_driver.splitlines(True),driver.splitlines(True),fromfile='accepted/compile_retirement_current_driver.py',tofile='candidate/compile_retirement_current_driver.py')))
symbols=read('EXPECTED-SYMBOL-DATA.json')
for name,rule in symbols['rules'].items():
 if name.startswith(('native-','legacy-')):rule['unique_global_or_weak_STT_FUNC_definitions'].append(new_symbol)
 elif name in ('selected-owned-syscall.o','fallback-owned-syscall.o'):rule['unique_undefined_global_or_weak_symbols'].append(new_symbol)
 elif name=='settid-c-fallback-syscall.o':rule['forbidden_global_or_weak_symbols'].append(new_symbol)
symbols.update(new_numa_helper=new_symbol,inherited_scheduler_and_settid_rules_unchanged=True)
save('EXPECTED-SYMBOL-DATA.json',symbols)
commands=read('guest-compiler-commands.json')
for c in commands:
 c['argv']=[('MCKERNEL_RUST_BUILDID=numa-current-source-'+identity[:12]) if a.startswith('MCKERNEL_RUST_BUILDID=') else a for a in c['argv']]
save('guest-compiler-commands.json',commands)
nonce=uuid.uuid4().hex
old_nonce=read('guest-request-proposal.json')['nonce']
def relocate(x):
 if isinstance(x,str):return x.replace(str(OLD),str(R)).replace(old_nonce,nonce).replace('mckernel-scheduler-compiler-','mckernel-numa-compiler-')
 if isinstance(x,list):return [relocate(v) for v in x]
 if isinstance(x,dict):return {k:relocate(v) for k,v in x.items()}
 return x
def repin(x):
 if isinstance(x,dict):
  if set(('path','sha256','bytes'))<=x.keys() and str(x['path']).startswith(str(R)) and Path(x['path']).is_file():x.update(ref(Path(x['path'])))
  for v in x.values():repin(v)
 elif isinstance(x,list):
  for v in x:repin(v)
request=relocate(read('guest-request-proposal.json'));repin(request)
request.update(status='NUMA_CURRENT_SIX_STAGE_PROPOSAL_NOT_RELEASED',physical_release_prerequisite='UNBOUND: current image37e must reach accepted terminal physical release, then thread-native priority first; fresh root admission required',object_contract='Same six real ELF64 ET_REL objects and inherited rules; NUMA helper unique provider/import, absent in policy-off C. No final link/default/native/retirement authority.')
request['boundary_linkage']['Rust_definitions'].append(new_symbol)
request['boundary_linkage']['numa_per_object_rules']=symbols['rules']
request['prerequisites_unbound']=[s.replace('genuine active-image positive physical clearance and latest exclusive review','currentimage37e terminal physical release, thread-native priority, and latest genuine exclusive review') for s in request['prerequisites_unbound']]
save('guest-request-proposal.json',request)
profile=relocate(read('guest-profile-proposal.json'));repin(profile)
profile.update(status='NUMA_SIX_STAGE_PROPOSAL_UNRELEASED',scope=SCOPE+' Same six compiler stages and reviewed two-file NUMA overlay; source recipe only.')
idx=profile['argv'].index('--request-sha256');profile['argv'][idx+1]=sha(R/'guest-request-proposal.json')
save('guest-profile-proposal.json',profile)
release=relocate(read('EXECUTION-RELEASE-DATA-TEMPLATE.json'));repin(release)
release.update(source_identity=identity,reason='UNBOUND source recipe only; no execution/materialization/publication/current physical/admission outcome. Preserve image37e terminal and thread-native priority.')
save('EXECUTION-RELEASE-DATA-TEMPLATE.json',release)
argv=['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=2147483648','--core=0','--nofile=256','--fsize=33554432','--','/home/holden/anaconda3/bin/python3','-I','-B',str(R/'materialize_sources.py')]
save('ORDINARY-MATERIALIZATION-PROPOSAL.json',{'scope':SCOPE,'status':'UNBOUND_NOT_RUN','argv':argv,'cpu':6,'jobs':1,'wall_seconds':35,'CPU_seconds':30,'AS':2147483648,'CORE':0,'FSIZE':33554432,'NOFILE':256,'environment':{'CARGO_BUILD_JOBS':'1','LANG':'C','LC_ALL':'C','MAKEFLAGS':'','PATH':'/usr/bin:/bin','TZ':'UTC'},'fresh_grant':None,'current_admission':None,'outer_capture_binding':None,'materialization_receipt':None,'inode_binding':None,'direct_join_and_physical':None,'template_reference':ref(OLD/'ordinary-materialization-1/grant.json'),'instruction':'Root supplies fresh reviewed ordinary owned capture and CPU6 admission; prior grant is template only. No candidate imports, no compiler.'})
save('PREPARATION-RECEIPT.json',{'scope':SCOPE,'status':'FROZEN_NUMA_SOURCE_RECIPE_ONLY','integration_receipt':ref(INTEGRATION),'accepted_manifest':ref(OLD/'source-manifest.json'),'accepted_artifact_review':ref(OLD/'independent-review-1/actual-six-stage-artifact-acceptance.json'),'accepted_physical_review':ref(OLD/'independent-review-1/actual-six-stage-physical-retirement-acceptance.json'),'source_manifest':ref(R/'source-manifest.json'),'source_identity':identity,'identity_algorithm':'SHA256 UTF8 json.dumps([{relative,bytes,sha256} in manifest row order],sort_keys=True,separators=(comma,colon)); excludes origin paths and atime','only_source_row_changes':changes,'unchanged_literal_rows':158,'retained_scheduler_helper_sha256':'a5b8ed0f048adcfa6908094f7b8b5d459b9b14aa0ed4b75e5250abe6f8387c57','source_overlays_copied':2,'owner_materializer_assertions_byte_identical':all(sha(R/n)==sha(OLD/n) for n in ['materialize_sources.py','current_fullcrate_owner.py','actual_retirement_consumer_and_FAM_assertions.h']),'driver_only_DATA_changes':['RUST_DEFINITIONS','RULES'],'driver_algorithm_AST_identical':True,'six_commands_preserved_except_Rust_buildID':True,'expected_symbol_data':ref(R/'EXPECTED-SYMBOL-DATA.json'),'request':ref(R/'guest-request-proposal.json'),'profile':ref(R/'guest-profile-proposal.json'),'ordinary_materialization':ref(R/'ORDINARY-MATERIALIZATION-PROPOSAL.json'),'materialized':False,'compiled_or_tested':False,'lease_acquired':False,'execution_release':None,'actual_publication':None,'current_physical':None,'current_admission':None,'outcomes':None,'failure_history':'Preserve all prior finite fixture/compiler/capture failures and accepted scheduler outputs. This packet has zero executed attempts. One failed candidate plus one bounded correction per family, then focused escalation; no unchanged failed replay.','priority':'Currentimage37e terminal physical release and thread-native first; no SDK capacity bypass or scratch resize; included100%/noAPI/service holds remain authoritative.'})
