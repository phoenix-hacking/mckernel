"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact conversion-build retirement source/DATA successor. No live operations.
"""
from pathlib import Path
import json,hashlib,copy,re,ast,difflib
D=Path(__file__).resolve().parent;A=D.parent
OLD=A/'CURRENT119-NORMAL-RETIREMENT-PREPARATION-1/parent-custody-data-correction-1';BUILD=A/'ROOT-CONVERSION-FIRST-BUILD-ADMISSION-1';COHORT=A/'M14-CONVERSION-FIRST-PRODUCER-BINDING-1/current-frontier-successor-1';LEDGER=A/'ROOT70-CONVERSION-BUILD-CUSTODY-1/ROOT70-NONCE-LEDGER.PENDING-CURRENT.json'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def write(n,v):(D/n).write_text(v if isinstance(v,str)else json.dumps(v,indent=2)+'\n')
def main():
 assert not (D/'BINDINGS.json').exists();lr=ref(LEDGER);assert lr['sha256']=='2a8fd880a4b028380a709ec5f358901b78d6b998536a04aad44b9c821844217f';ledger=read(LEDGER);entry=ledger['conversion_first_build'];assert entry['container']=='a7fe0b67d129afc3868d329d65f68317b6aadee6bedd7bc76330a52cdd0ae7ef'
 oldb=read(OLD/'BINDINGS.json');b=copy.deepcopy(oldb);profile=read(COHORT/'PROFILE.SOURCE-ONLY.json');free=read(A/'M14-CONVERSION-FIRST-CURRENT-FRONTIER-PREPARATION-1/parent-ownership-correction-1/actual-independent-acceptance-1/CURRENT-FREE.ACTUAL.json');nonce=profile['actual_nonce'];assert nonce=='4709c9fae2c743a7acd662e93a663358'
 refs={n:ref(COHORT/n)for n in ['PROFILE.SOURCE-ONLY.json','run_build_only.py','build_only_worker.py','hold_and_run_build_only.py']}
 for n in ['ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json','ROOT-HOLDER-BOOTSTRAP-GRANT.json','ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json','ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json','ROOT-BUILD-RESULT.ACTUAL.json']:refs[n]=ref(BUILD/n)
 refs['worker_result']=entry['worker_result']
 for n in ['claim.json','plan.json','terminal.json','container.stdout','container.stderr','container.cid']:refs['output:'+n]=ref(BUILD/'OUTPUT'/n)
 for n in ['HOLDER.READY.json','RUNNER.STARTED.json','RUNNER.JOINED.json','BUILD-LOCAL-TERMINAL.json']:refs['holder:'+n]=ref(BUILD/'HOLDER'/n)
 refs['accepted_capture_current_free']=profile['native_custody_clearance'];refs['accepted_capture_outer_parent_join']=free['capture_positive_join'];refs['independent_artifact_acceptance']=entry['independent_artifact_acceptance'];refs['current_consumed_ledger']=lr
 claim=read(BUILD/'OUTPUT/claim.json');argv=claim['argv'];mounts=[]
 for i,token in enumerate(argv):
  if token=='--mount':
   fields=argv[i+1].split(',');v=dict(x.split('=',1)for x in fields if '='in x);assert v['type']=='bind';mounts.append(dict(Source=v['source'],Destination=v['target'],RW='readonly'not in fields))
 outputs=[]
 for row in entry['outputs']:
  p=BUILD/'OUTPUT/work'/row['path'].removeprefix('/work/');r=ref(p);assert all(r[k]==row[k]for k in ['bytes','sha256']);outputs.append(r)
 packet=dict(scope=b['scope'],schema='mckernel.conversion-first-build.normal-retirement-preparation.v1',status='SOURCE_DATA_NOT_EXECUTION_RELEASE',runtime_authority=None,nonce=nonce,nonce_consumed_once=True,container_id=entry['container'],container_name='conversion-first-build-only-'+nonce,output_root=str(BUILD/'OUTPUT'),cohort=str(COHORT),source_refs=refs,expected_mounts=mounts,retained_actual_outputs=outputs,native_custody_unchanged=True)
 write('NORMAL-RETIREMENT-PACKET.json',packet)
 protected=read(OLD/'PROTECTED-ORIGINALS.json');records={r['path']:r for r in protected['records']};more=list(refs.values())+outputs+read(BUILD/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json')['qualified_readonly_files']
 for name in ['mckernel.img.map','CMakeFiles/mckernel.img.dir/link.d']:more.append(ref(BUILD/'OUTPUT/work/output/build/kernel'/name))
 for name in ['producer-contract.json']+[('%02d.%s'%(i,s))for i in range(3)for s in ['stdout','stderr']]:more.append(ref(BUILD/'OUTPUT/work/evidence'/name))
 for r in more:records[r['path']]=dict(kind='file',**r)
 protected['records']=list(records.values());protected['roots']+= [str(BUILD),str(BUILD/'OUTPUT/work'),str(COHORT)];protected['status']='SOURCE_DATA_RETAIN_ALL_ORIGINAL119_AND_CONVERSION_INPUT_OUTPUTS';write('PROTECTED-ORIGINALS.json',protected)
 b.update(packet=ref(D/'NORMAL-RETIREMENT-PACKET.json'),protected=ref(D/'PROTECTED-ORIGINALS.json'),prior_actors=free['next_full_postjoin_actor_frontier'],new_known_actors=[dict(pid=2623592,start=111558755,role='conversion_build_holder',group=None,fd=3),dict(pid=2624628,start=111575974,role='conversion_build_runner',group=None,fd=None)],actor_evidence=[refs['accepted_capture_current_free'],refs['accepted_capture_outer_parent_join']]+[refs['holder:'+n]for n in ['HOLDER.READY.json','RUNNER.STARTED.json','RUNNER.JOINED.json','BUILD-LOCAL-TERMINAL.json']],parent_tool_join=lr,output_root_parent=str(D),cid=entry['container'],name=packet['container_name'],nonce=nonce,prior_ledger=ref(A/'ROOT69-CONVERSION-FIRST-ADOPTION-1/ROOT69-NONCE-LEDGER.ACTUAL.json'),holder_pid=2623592,holder_birth=111558755,runner_pid=2624628,runner_birth=111575974,command_count=3,ledger_key='conversion_first_build',operation='CONVERSION_FIRST_THREE_COMMAND_BUILD_ONLY_NOT_NATIVE',approved_creation_argv=refs['output:claim.json'],parent_tool_session_id=74525,parent_tool_chunk_id='69417f',current_ledger=lr,current_build_ledger_entry=entry)
 b['actor_gaps']+=['Original readonly client2232653 and uninstrumented source tool identities remain UNKNOWN; no cleanup inference.','Root70 holder_tool is a typed Root attestation of tool74525 terminal chunk69417f/rc0, not an invented raw parent wait4 record.'];write('BINDINGS.json',b)
 source=(OLD/'retire_exact_current119_stopped_container.py').read_text();source=source.replace('Single CURRENT119 A3 stopped-container retirement.','Single conversion-first stopped-container retirement.').replace("SELF=D/'retire_exact_current119_stopped_container.py'","SELF=D/'retire_exact_conversion_stopped_container.py'")
 source=source.replace("BINDINGS_SHA='"+ref(OLD/'BINDINGS.json')['sha256']+"'","BINDINGS_SHA='"+ref(D/'BINDINGS.json')['sha256']+"'")
 old=""" need(parent['author']=='/root' and parent['decision']=='ROOT_ATTESTS_OBSERVED_ACTUAL_TOOL_SESSION_JOIN' and parent['session_id']==b['parent_tool_session_id'] and parent['returncode']==0 and parent['joined'] is True and parent['actual_tool_response']['chunk_id']==b['parent_tool_chunk_id'] and parent['actual_tool_response']['exit_code']==0,'saved actual Root tool join attestation')"""
 new=""" tool=parent[b['ledger_key']]['holder_tool']
 need(parent['author']=='/root' and b['parent_tool_join']==b['current_ledger'] and parent[b['ledger_key']]==b['current_build_ledger_entry'] and tool==dict(session_id=b['parent_tool_session_id'],terminal_chunk=b['parent_tool_chunk_id'],returncode=0),'exact Root70 typed holder tool closure attestation; not fabricated raw wait4')"""
 assert source.count(old)==1;source=source.replace(old,new)
 old=""" need(build['nonce']==b['nonce'] and build['container']==b['cid'] and build['normal_retirement_pending'] is True and build['current_physical_clearance_pending'] is True and build['current_free'] is None,'actual CURRENT119 consumed build remains pending physical retirement')
 need(build['worker_result']==expected_refs['worker_result'] and build['container_terminal']==expected_refs['output:terminal.json'] and build['holder_tool_join']==b['parent_tool_join'],'same actual CURRENT119 worker/terminal/positive tool join')
 need(build['actual_four_command_returncodes']==[0,0,0,0] and build['artifact_acceptance'] is False and build['native_acceptance'] is False,'actual four rc0 and no premature artifact/native claim')
 result=authenticated(expected_refs['worker_result'],True)
 need(build['actual_outputs']==[row['output'] for row in result['commands']],'same exact four retained actual output byte identities')"""
 new=""" need(len(ledger['consumed_nonces'])==74 and ledger['consumed_nonces'][-1]==b['nonce'] and build['container']==b['cid'] and ledger['current_physical_clearance_pending'] is True,'actual74 consumed conversion build remains pending physical retirement')
 need(build['worker_result']==expected_refs['worker_result'] and build['container_terminal']==expected_refs['output:terminal.json'] and build['holder_tool_join']==expected_refs['holder:RUNNER.JOINED.json'] and build['holder_local_terminal']==expected_refs['holder:BUILD-LOCAL-TERMINAL.json'],'same actual conversion worker/terminal/runner/holder closure')
 need(build['command_returncodes']==[0,0,0] and build['native_acceptance'] is False and build['unmeasured_docker_client_births']=='UNKNOWN','actual three rc0/native OPEN/unmeasured clients retained')
 acceptance=authenticated(build['independent_artifact_acceptance'],True)
 need(build['independent_artifact_acceptance']==expected_refs['independent_artifact_acceptance'] and acceptance['independent'] is True and acceptance['implementation_ownership'] is False,'exact independently accepted conversion artifact; not native/default acceptance')
 result=authenticated(expected_refs['worker_result'],True)
 need(build['outputs']==[row['output'] for row in result['commands']] and len(result['commands'])==3,'same exact three retained actual output byte identities')"""
 assert source.count(old)==1;source=source.replace(old,new)
 source=source.replace('mckernel.current119-build.','mckernel.conversion-first-build.').replace('PASS_EXACT_CURRENT119_STOPPED_CONTAINER_RETIRED_PENDING_POSTJOIN_CURRENT','PASS_EXACT_CONVERSION_FIRST_STOPPED_CONTAINER_RETIRED_PENDING_POSTJOIN_CURRENT').replace('GRANT_ONE_EXACT_STOPPED_CURRENT119_CONTAINER_RETIREMENT','GRANT_ONE_EXACT_STOPPED_CONVERSION_CONTAINER_RETIREMENT')
 ast.parse(source);write('retire_exact_conversion_stopped_container.py',source);write('EXECUTOR-DELTA.patch',''.join(difflib.unified_diff((OLD/'retire_exact_current119_stopped_container.py').read_text().splitlines(True),source.splitlines(True),fromfile='accepted119executor',tofile='conversionexecutor')))
 files=read(OLD/'RUNTIME-FILES.json')
 for k,n in [('executor','retire_exact_conversion_stopped_container.py'),('bindings','BINDINGS.json'),('packet','NORMAL-RETIREMENT-PACKET.json'),('protected','PROTECTED-ORIGINALS.json')]:files[k]=ref(D/n)
 write('RUNTIME-FILES.json',files);release=read(OLD/'RELEASE.TEMPLATE.NOT-AUTHORITY.json');release.update(schema='mckernel.conversion-first-build.stopped-container-retirement.release.v1',bindings=files['bindings'],files=files,parent_tool_join=lr,cid=b['cid'],nonce=nonce,current_ledger=lr,output=str(D/'actual-retirement-conversion-root1'));write('RELEASE.TEMPLATE.NOT-AUTHORITY.json',release)
 print('SOURCE_DATA_PREPARED_NOT_EXECUTED')
if __name__=='__main__':main()
