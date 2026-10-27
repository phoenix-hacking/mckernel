from pathlib import Path
import ast,json
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254');N=E/'daemon-sdk7-next-production-criterion-source-1/container64-owner-successor-source-1';old=E/'sdk7-142g-consumer-successor-source-1/daemon_sdk_owner.142G-SOURCE-ONLY.py';source=old.read_text();tree=ast.parse(source);lines=source.splitlines(True);edits=[]
def replace_node(node,text):edits.append((node.lineno-1,node.end_lineno,text.rstrip()+'\n'))
def assign(name,expr):
 n=next(x for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in x.targets));replace_node(n,name+' = '+expr)
def function(name,text):replace_node(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name),text)
assign('COMMAND',repr(['-I','-B','/driver.py','--execute']));assign('OUTPUT_PARENT','mc.OUTPUT_PARENT');assign('PREPARATION','mc.PREPARATION');assign('PREPARATION_SHA','mc.PREPARATION_SHA');assign('DRIVER','mc.DRIVER');assign('CANDIDATE','mc.CANDIDATE');assign('LIBRARY_PREPARATION','mc.PREP');assign('BFD_DRIVER_SHA','sha(DRIVER.read_bytes())');assign('COMMANDS_PATH','PREPARATION')
sources=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in n.targets)))
paths=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RUNTIME_SOURCE_PATHS' for t in n.targets)))
extra={'mock64/entry_capture.py':N/'run_mock64_owned_capture.py','mock64/contract.py':N/'mock64_contract.py','mock64/profile.py':N/'effective_profile64.py','mock64/kernel_pids64.py':N/'kernel_pids64.py','mock64/fixture_runner.py':N/'run_fixture_precreated.py','mock64/preparation.json':N/'PREPARATION.SOURCE-ONLY.json','mock64/tests.py':N/'test_mock64_successor.py','mock64/account04b5.py':E/'scratch-growth-final-copy-close-source-1/recover_growth_custody.py','mock64/canonical_account.py':Path('/home/holden/mckernel/scripts/os_goal_credits.py')}
paths.update({k:str(v) for k,v in extra.items()});paths['scripts/native_running_external_modules_owner.py']=str(N/'mock64_owner.py');paths['scripts/native_running_external_modules_offline.py']=str(N/'mock64_driver.py')
assign('SOURCES',repr(tuple(sources)+tuple(extra)));assign('RUNTIME_SOURCE_PATHS',repr(paths))
for n in tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='RUNTIME_SOURCE_PATHS' for t in n.targets):replace_node(n,"RUNTIME_SOURCE_PATHS['scripts/native_running_external_modules_owner.py'] = "+repr(str(N/'mock64_owner.py')))
function('mounts','''def mounts(request):
    prepdir=request['runtime_preparation_identity']['path']
    return [(str(mc.MIRROR),mc.PREP['container_source_parent'],True),
            (str(NIGHTLY_ROOT),'/nightly',True),(str(REPO),str(REPO),True),
            (request['candidate_root'],'/work',False),
            (str(Path(request['candidate_root'])/'fixture-output'),mc.PREP['container_output'],False),
            (prepdir,'/preparation',True),(str(DRIVER),'/driver.py',True),
            (request['request_path'],'/request.json',True),
            (mc.PREP['census_helper']['path'],mc.PREP['census_helper']['path'],True)]''')
profile=ast.get_source_segment(source,next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='profile')).replace('host.check_profile(info, IMAGE, nonce)','check_profile64(info, IMAGE, nonce)');function('profile',profile)
create=ast.get_source_segment(source,next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='create_args')).replace('*host.RESOURCE_ARGS','*RESOURCE_ARGS64');function('create_args',create)
function('validate_preparation','''def validate_preparation(prep, request):
    need(prep == mc.PREP and prep['schema']=='mckernel.daemon-mock64-preparation.v1' and prep['tool_image']==IMAGE, 'exact mock64 preparation/profile')
    for row in prep['source_files']:
        source=safe_path(row['source']['path'],False)
        need(source.stat().st_size==row['source']['bytes'] and host.digest(source)==row['source']['sha256'],'frozen fixture source differs')
    for key in ('capture_helper','census_helper'):
        row=prep[key];path=safe_path(row['path'],False)
        need(path.stat().st_size==row['bytes'] and host.digest(path)==row['sha256'],'exact mock support closure')
    return mc.verify_request_inputs(request)''')
validate=ast.get_source_segment(source,next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='validate_request'))
validate=validate.replace("'output_parent_identity','backing_identity'}","'output_parent_identity','backing_identity','fixture_output_identity','runtime_preparation_identity','output_binding'}")
validate=validate.replace('mckernel.daemon-soleheavy-sdk-request.v1','mckernel.daemon-mock64-request.v1').replace("validate_preparation(bound(request['preparation']))","validate_preparation(bound(request['preparation']),request)").replace("need(Path(request['input_root'])==PREPARATION.parent, 'exact BFD input namespace')","need(Path(request['input_root'])==mc.MIRROR, 'exact mock input namespace')").replace("need(not list(candidate.iterdir()), 'fresh empty BFD output candidate')","need({p.name for p in candidate.iterdir()}=={'fixture-output'} and not list((candidate/'fixture-output').iterdir()), 'fresh mock work/output required')")
function('validate_request',validate)
function('validate_library_receipt','''def validate_library_receipt(receipt, request):
    need(receipt.get('schema')=='mckernel.daemon-mock64-driver-receipt.v1' and receipt.get('status')=='PASS_DAEMON_MOCK64_CAPTURE' and receipt.get('scope')==mc.PREP['scope'],'exact mock64 receipt')
    need(receipt.get('preparation_sha256')==PREPARATION_SHA and receipt.get('nonce')==request['nonce'] and receipt.get('command')==mc.fixture_command(request['nonce']),'exact mock command/preparation')
    need(all(receipt.get(k) is False for k in ('production_main_executed','native_acceptance','provider_Rust_link_closure','M15_file_closure')),'mock scope inflated')
    capture=receipt['capture'];need(mc.capture_ok(capture) and capture['captures']['stderr']['size']==0,'positive owned fixture join')
    root=Path(request['candidate_root']);summary=mc.validate_fixture_tree(root/'fixture-output')
    need(mc.ref(root/'fixture-output/summary.json')['sha256']==receipt.get('summary_sha256') and receipt.get('fixture_cases')==26,'actual durable mock summary')
    proofs=[]
    for phase in ('before','after'):
        path=safe_path(str(root/'evidence'/('kernel-pids64-'+phase+'.json')),False)
        need(host.digest(path)==receipt['kernel_pids64_'+phase+'_sha256'],'actual kernel proof hash')
        proofs.append(kernel_pids64.validate_proof(mc.json_bytes(path.read_bytes())))
    need(proofs[0]['controller_identity']==proofs[1]['controller_identity'] and proofs[0]['selected_mount']==proofs[1]['selected_mount'],'actual kernel pids controller changed')
    for stream in ('stdout','stderr'):
        logical=Path(capture['captures'][stream]['path']);need(logical==Path('/work/evidence')/stream,'exact mock driver capture stream')
        actual=safe_path(str(root/logical.relative_to('/work')),False)
        need(actual.stat().st_size==capture['captures'][stream]['size'] and host.digest(actual)==capture['captures'][stream]['sha256'],'durable mock driver stream')''')
measure=ast.get_source_segment(source,next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='measure'))
start=measure.index('        root = Path(request[key]); total = count = 0');measure=measure[:start]+'''        mc.output_tree_bytes(Path(request[key]),maximum)
    return observed'''
measure=measure.replace('    output_admission(request)','    check_campaign()\n    output_admission(request)',1);function('measure',measure)
auth=ast.get_source_segment(source,next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='authenticate')).replace('mckernel.daemon-soleheavy-sdk-release.v1','mckernel.daemon-mock64-release.v1').replace('    return request, release','    check_current_admission(release,request,request_path,request_sha)\n    return request, release');function('authenticate',auth)
guarded=ast.get_source_segment(source,next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='guarded_execute')).replace('    with DeferredSignals() as latch:','    check_campaign()\n    with DeferredSignals() as latch:',1).replace('            entered = True\n            result = run_owner','            check_current_admission(release,request,request_path,request_sha)\n            entered = True\n            result = run_owner');function('guarded_execute',guarded)
# Keep every unmentioned owner/client/custody/container retirement function unchanged.
for a,b,text in sorted(edits,reverse=True):lines[a:b]=[text]
result=''.join(lines)
marker="host = image._HOST_OWNER\n";imports="import importlib.util\nsys.path.insert(0, "+repr(str(N))+" )\nimport mock64_contract as mc\nimport kernel_pids64\nfrom effective_profile64 import check_profile as check_profile64, RESOURCE_ARGS as RESOURCE_ARGS64\n\n";result=result.replace(marker,imports+marker,1)
# sha() is declared later than assignments; the driver pin needs only hashlib here.
result=result.replace('BFD_DRIVER_SHA = sha(DRIVER.read_bytes())','BFD_DRIVER_SHA = hashlib.sha256(DRIVER.read_bytes()).hexdigest()')
insert='''
_ACCOUNT=None
def check_campaign():
    global _ACCOUNT
    path=REPO/'docs/verification/evidence/os-recovery-adoption-20261025-0254/scratch-growth-final-copy-close-source-1/recover_growth_custody.py'
    need(hashlib.sha256(path.read_bytes()).hexdigest()=='04b5c6af885baca472e99e590bf07ae360dacad95487709477cf3d2bf8d6c90a','exact accepted account guard')
    if _ACCOUNT is None:
        spec=importlib.util.spec_from_file_location('accepted_mock64_account_guard',path);_ACCOUNT=importlib.util.module_from_spec(spec);spec.loader.exec_module(_ACCOUNT)
    state=json.loads((REPO/'.git/os-autopilot/state.json').read_bytes());_ACCOUNT.check_account_state(state,time.time())
    clocks=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT and all(a<b for a,b in zip(clocks,mc.CUTOFFS)),'same boot/fixed cutoff')
    return clocks

def check_current_admission(release,request,request_path,request_sha):
    a=bound(release['current_admission'])
    required={'schema','status','author','nonce','request','boot_id','profile','one_heavy','observed_clocks','expires_wall','nonce_ledger_complete','consumed_nonces','resource_physical','latest_postjoin_acceptance','source_publication'}
    need(set(a)==required and a['schema']=='mckernel.daemon-mock64-current-admission.v1' and a['status']=='ROOT_RESERVED_DAEMON_MOCK64_SOLE_HEAVY' and a['author']=='/root','actual Root mock64 admission required')
    need(a['request']==dict(path=str(request_path),sha256=request_sha) and a['nonce']==request['nonce'] and a['boot_id']==BOOT and a['profile']==mc.PREP['profile'] and a['one_heavy'] is True,'exact one-heavy request/profile admission')
    need(a['nonce_ledger_complete'] is True and isinstance(a['consumed_nonces'],list) and len(a['consumed_nonces'])==len(set(a['consumed_nonces'])) and all(re.fullmatch('[0-9a-f]{32}',str(n)) for n in a['consumed_nonces']) and request['nonce'] not in a['consumed_nonces'],'complete current nonce exclusion required')
    for reference in (a['resource_physical'],a['latest_postjoin_acceptance'],a['source_publication']):
        need(set(reference)=={'path','bytes','sha256'} and mc.ref(safe_path(reference['path'],False))==reference,'actual admission reference differs')
    resources=json.loads(Path(a['resource_physical']['path']).read_bytes())
    need(resources['observed_clocks']==a['observed_clocks'] and resources['boot_id']==BOOT and resources['no_existing_heavy'] is True,'actual fresh resources differ')
    now=check_campaign();need(len(a['observed_clocks'])==3 and all(type(x) in (int,float) and math.isfinite(x) for x in a['observed_clocks']),'three finite actual clocks')
    need(all(0<=n-o<120 for n,o in zip(now,a['observed_clocks'])) and type(a['expires_wall']) in (int,float) and now[0]<a['expires_wall']<=min(a['observed_clocks'][0]+120,mc.CUTOFFS[0]),'fresh bounded Root admission expired')
    return a
'''
result=result.replace('import json\n','import json\nimport math\n',1)
result=result.replace('\ndef main():',insert+'\ndef main():',1) if '\ndef main():' in result else result.replace("\nif __name__ == '__main__':",insert+"\nif __name__ == '__main__':",1)
# The original CLI is a main(argv=None); insert before authenticate instead if needed.
if 'def check_campaign()' not in result:raise ValueError('missing account insertion')
(N/'mock64_owner.py').write_text(result)
print('owner bytes',len(result))
