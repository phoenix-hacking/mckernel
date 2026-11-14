"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare focused tests and non-authority data; never execute actual effects.
"""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;E=D.parent
BASE=E/'bfd-default-build-normal-retirement-preparation-20261028-1/executor-source-1/image-metadata-profile-correction-source-1'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p).resolve();raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(n,v):
 p=D/n;assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n');return ref(p)
b=read(D/'BINDINGS.json');p=read(b['packet']['path']);refs=p['source_refs']
ledger=read(b['prior_ledger']['path']);ledger.update(author='TEMPLATE_NOT_ROOT_AUTHORITY',prepared_by='/root/bfd_route',status='TEMPLATE_NOT_AUTHORITY',runtime_authority=None,consumed_nonces=ledger['consumed_nonces']+[b['nonce']],current_physical_clearance_pending=True,complete_within_declared_current_boundary=True,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=True)
build=dict(operation=b['operation'],nonce=b['nonce'],container_id=b['cid'],container_name=b['name'],actual_holder_tool_join_receipt=b['parent_tool_join'],normal_retirement_pending=True,current_physical_clearance_pending=True)
for key,sourcekey in [('profile','PROFILE.SOURCE-ONLY.json'),('actual_grant','ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json'),('container_claim','output:claim.json'),('plan','output:plan.json'),('worker_result','worker_result'),('terminal','output:terminal.json'),('holder_ready','holder:HOLDER.READY.json'),('runner_join','holder:RUNNER.JOINED.json'),('holder_local_terminal','holder:BUILD-LOCAL-TERMINAL.json')]:build[key]=refs[sourcekey]
ledger[b['ledger_key']]=build;put('ROOT-PENDING-LEDGER.TEMPLATE.NOT-AUTHORITY.json',ledger)
for n in ['test_retirement_executor.py','test_review_correction.py','test_actual_census_uuid.py']:
 raw=(BASE/n).read_text().replace('retire_exact_bfd_stopped_container.py','retire_exact_current118_stopped_container.py').replace('bfd-default-build','current118-build').replace('BFD','CURRENT118')
 if n=='test_retirement_executor.py':
  start=raw.index(" old=Path(");end=raw.index(" labels=",start);raw=raw[:start]+raw[end:]
  raw=raw.replace("WorkingDir='/work'","WorkingDir=B['working_directory']").replace("len(PROTECTED['records']),363","len(PROTECTED['records']),46")
  raw=raw.replace("('primitive','normal','backend','guardian','prior_observer','packet','protected')","('primitive','normal','backend','guardian','prior_observer','packet','protected','base_reviewed_executor')")
  start=raw.index('  ledger=json.loads(Path(');end=raw.index('\n  ledger.update(',start)
  raw=raw[:start]+"  ledger=json.loads((D/'ROOT-PENDING-LEDGER.TEMPLATE.NOT-AUTHORITY.json').read_bytes())"+raw[end:]
  raw=raw.replace("['bfd_default_build']","[B['ledger_key']]")
 if n=='test_actual_census_uuid.py':
  raw=raw.replace("D.parent/'retire_exact_current118_stopped_container.py'",repr(str(BASE.parent/'retire_exact_bfd_stopped_container.py')))
 (D/n).write_text(raw)
files=dict(executor=ref(D/'retire_exact_current118_stopped_container.py'),bindings=ref(D/'BINDINGS.json'))
files.update({k:b[k] for k in ('primitive','normal','backend','guardian','prior_observer','packet','protected','base_reviewed_executor')})
release=dict(schema='mckernel.current118-build.stopped-container-retirement.release.v1',author='REQUIRED_ACTUAL_ROOT',decision='GRANT_ONE_EXACT_STOPPED_CURRENT118_CONTAINER_RETIREMENT',maximum_invocations=1,bindings=files['bindings'],files=files,parent_tool_join=b['parent_tool_join'],cid=b['cid'],nonce=b['nonce'],signals_allowed=0,records_released=[],cutoffs=b['cutoffs'],credit_run_id='7f4af94a83b14cc08f97401f5891d965',credit_ceiling='57774.852125',minimum_cumulative_spent='22812.3311',Root_attests_no_unlisted_intervening_operation='REQUIRED_ACTUAL_TRUE',actual_account_identity_operation_admission_accepted='REQUIRED_ACTUAL_TRUE',current_ledger='REQUIRED_ACTUAL_ROOT_PENDING_LEDGER_BYTEREF',source_review='REQUIRED_INDEPENDENT_PASS_SOURCE_BYTEREF',source_checkpoint='REQUIRED_ACTUAL_FETCHED_COMMIT',fetched_source_verified='REQUIRED_ACTUAL_TRUE',source_publication='REQUIRED_ACTUAL_FETCHED_PUBLICATION_BYTEREF',execution_review='REQUIRED_INDEPENDENT_PASS_EXECUTION_BYTEREF',output=str(D/'actual-retirement-root1-e984'))
put('ROOT-RELEASE.TEMPLATE.NOT-AUTHORITY.json',release)
print(json.dumps(dict(files=files,release_template=ref(D/'ROOT-RELEASE.TEMPLATE.NOT-AUTHORITY.json'))))
