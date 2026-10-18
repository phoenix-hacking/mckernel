from pathlib import Path
import ast,copy,hashlib,importlib.util,json,sys,types
R=Path(__file__).resolve().parent;P=R.parent
sys.path.insert(0,str(P/'adapters'))
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
g=load(R/'native_exact_scratch22_authority3_image_guard.py','packet_guard');driver=load(P/'adapters/native_rust_exact_mckernel_image_offline.py','packet_driver')
pending=json.loads((R/'pending-bindings.json').read_text());selected=json.loads((R/'selected-request-fields.json').read_text());q=copy.deepcopy(selected)
request_path=P/'image-request.json';request_sha='aecf1e46390f1d3784b768692751d524ba958acf7079a3b90f8a4d8597eea07e'
release={'schema':'fp-save-thin.image-guard-release.v1','status':'PASS_EXECUTION_RELEASE','execution_count':1,'request':{'path':str(request_path),'sha256':request_sha},'source_derivative_sha256':q['source_derivative_sha256'],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'scratch_binding':{'uuid':g.UUID,'device':g.ROOT.stat().st_dev},'source_sha256':{p:digest(Path(p)) for p in g.SOURCES},'author':'independent-author-fixture','execution_review':{'path':'review'},'prerequisites':{k:{'path':k} for k in ['preparation','cleanup','native_baseline','ordinary']},'guard_capture':pending['guard_capture'],'nonce':pending['nonce']}
statuses={'preparation':'PASS','cleanup':'PASS_EXECUTED','native_baseline':'PASS_DIAGNOSTIC_REVALIDATION','ordinary':'PASS_REMAINING_ORDINARY_CONTINUATION_ORIGINAL_CHILD_STATUS_UNKNOWN'}
def bound(pointer):
 p=pointer['path']
 if p=='release':return release
 if p==str(request_path):return q
 if p=='review':return {'decision':'PASS_EXECUTION','implementation_ownership':False,'reviewer':'independent-reviewer-fixture','reviewed_release_payload_sha256':hashlib.sha256(g.canonical({k:v for k,v in release.items() if k!='execution_review'})).hexdigest()}
 if p in statuses:return {'status':statuses[p],'candidate_sha':g.CANDIDATE,'image_id':q['image_id']}
 raise AssertionError(p)
g.bound=bound
original_run=g.subprocess.run
device=g.ROOT.stat().st_dev
g.subprocess.run=lambda *a,**kw:types.SimpleNamespace(stdout=json.dumps({'filesystems':[{'uuid':g.UUID,'maj:min':'%d:%d'%(g.os.major(device),g.os.minor(device)),'target':str(g.ROOT)}]}))
def accept():return g.authenticate(request_path,request_sha,Path('release'),'0'*64)
positive=0;negative=0
try:
 assert accept()[0]==q;positive+=1
 for key in ['source_derivative_sha256','materialization_sha256']:
  prior=q[key];q[key]='0'*64
  try:accept()
  except RuntimeError:negative+=1
  else:raise AssertionError('stale request accepted')
  q[key]=prior
 prior=release['source_sha256'];release['source_sha256']={}
 try:accept()
 except RuntimeError:negative+=1
 else:raise AssertionError('incomplete source closure accepted')
 release['source_sha256']=prior
 prior=release['status'];release['status']='PENDING_INDEPENDENT_EXECUTION_REVIEW'
 try:accept()
 except RuntimeError:negative+=1
 else:raise AssertionError('pending release accepted')
 release['status']=prior
 statuses['ordinary']='PENDING'
 try:accept()
 except RuntimeError:negative+=1
 else:raise AssertionError('unaccepted ordinary result accepted')
 statuses['ordinary']='PASS_REMAINING_ORDINARY_CONTINUATION_ORIGINAL_CHILD_STATUS_UNKNOWN'
finally:g.subprocess.run=original_run
# Invoke actual unchanged production ABI generator, never compiler.
source=Path(q['source_root']);fixtures=R/'abi-fixtures';fixtures.mkdir()
original_runner=driver._run_process
abi_positive=0;abi_negative=0
for mode in ['good','gcc9','process-failure']:
 root=fixtures/mode;build=root/'build';evidence=root/'evidence';build.mkdir(parents=True);evidence.mkdir()
 rows=[{'file':str(source/p),'directory':str(build),'arguments':['/usr/bin/cc','-DPRODUCTION','-c',str(source/p),'-o','ignored.o','-MD']} for p in ['arch/x86_64/kernel/cpu.c','kernel/process.c']]
 write(build/'compile_commands.json',rows);calls=[]
 def mock(argv,cwd,env,stdout,stderr,timeout,phase):
  assert argv[0]=='/usr/bin/cc' and '-fsyntax-only' in argv and '-DPRODUCTION' in argv
  assert not any(x in argv for x in ['-c','-MD','-o'])
  if phase=='production-abi-process':
   body=Path(argv[-1]).read_bytes();prefix=(source/'kernel/process.c').read_bytes();assert body.startswith(prefix)
   for expected in [b'ptrace_debugreg) == 5016',b'sizeof(struct thread) == 5568',b'_Alignof(struct thread) == 64',b'&sched_schedule_debug_handoff']:
    assert expected in body[len(prefix):]
  calls.append(phase)
  return 1 if mode=='process-failure' and phase=='production-abi-process' else 0
 driver._run_process=mock
 try:driver._validate_reset_production_abi(source,build,{'tools':{'cc':{'path':'/usr/bin/cc','version':'cc (GCC) '+('9.4.0' if mode=='gcc9' else '14.3.1')}}},evidence,{},None,None,19800,[])
 except driver.ImageBuildError:
  assert mode!='good';abi_negative+=1
 else:
  assert mode=='good' and calls==['production-abi-cpu','production-abi-process'];abi_positive+=1
 if mode=='gcc9':assert calls==[]
driver._run_process=original_runner
parsed=ast.parse((P/'adapters/native_rust_exact_mckernel_image_offline.py').read_text())
run=next(n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name=='_run')
loop=next(n for n in ast.walk(run) if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [x.id for x in n.target.elts if isinstance(x,ast.Name)]==['phase','command'])
assert ast.literal_eval(loop.iter.elts[0].elts[0])=='configure' and ast.literal_eval(loop.iter.elts[1].elts[0])=='build'
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_validate_reset_production_abi' for n in ast.walk(loop.body[-1]))
# Run the exact new dispatcher publication statements with private proof files.
parsed_dispatch=ast.parse((R/'dispatch-image-once.py').read_text())
start=next(i for i,n in enumerate(parsed_dispatch.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='published' for t in n.targets))
body=parsed_dispatch.body[start:start+4]
assert isinstance(body[-1],ast.For)
code=compile(ast.fix_missing_locations(ast.Module(body=body,type_ignores=[])),str(R/'dispatch-image-once.py'),'exec')
proof_path=R/'publication-proof-fixture.json'
pub={'status':'PASS','commit':'fixturecommit','fetched_commit':'fixturecommit','files':[{'path':'fixture/source.py','sha256':'a'*64,'bytes':11}]}
context={'d':{'prerequisites':{'publication':{'path':str(proof_path)}},'publication_commit':'fixturecommit','publication_rows':[{'repository_path':'fixture/source.py','sha256':'a'*64,'bytes':11}]},'json':json,'pathlib':__import__('pathlib')}
write(proof_path,pub);exec(code,context);publication_positive=1;publication_negative=0
for mode in ['hash','commit']:
 bad=copy.deepcopy(pub)
 if mode=='hash':bad['files'][0]['sha256']='b'*64
 else:bad['fetched_commit']='stalecommit'
 write(proof_path,bad)
 try:exec(code,context)
 except AssertionError:publication_negative+=1
 else:raise AssertionError('stale publication accepted')
write(proof_path,pub)
# Bounded correction1: exact dispatcher storage-admission statements.
parsed_budget=ast.parse((R/'dispatch-image-once.py').read_text())
i=next(i for i,n in enumerate(parsed_budget.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='spaces' for t in n.targets))
budget_code=compile(ast.fix_missing_locations(ast.Module(body=parsed_budget.body[i:i+2],type_ignores=[])),str(R/'dispatch-image-once.py'),'exec')
assert isinstance(parsed_budget.body[i+1],ast.For)
required={'/home/holden':16*2**30+576*2**20,'/home/holden/mckernel-work/scratch':12*2**30+576*2**20}
budget_positive=0;budget_negative=0
for mode in ['exact','host-one-low','scratch-one-low']:
 amounts=dict(required)
 if mode=='host-one-low':amounts['/home/holden']-=1
 if mode=='scratch-one-low':amounts['/home/holden/mckernel-work/scratch']-=1
 context={'pathlib':__import__('pathlib'),'os':types.SimpleNamespace(statvfs=lambda p:types.SimpleNamespace(f_bavail=amounts[str(p)],f_frsize=1))}
 try:exec(budget_code,context)
 except AssertionError:
  assert mode!='exact';budget_negative+=1
 else:
  assert mode=='exact' and all(v['after_floor_and_reserve']==0 and v['recovery_capture_reserve_bytes']==64*2**20 for v in context['spaces'].values());budget_positive+=1
write(R/'cheap-consumer-results.json',{'status':'PASS_MOCKED_CHANGED_JOINS_AND_ACTUAL_ABI_GENERATOR','actual_guard_authenticate_mock_positive':positive,'actual_guard_authenticate_mock_negatives':negative,'actual_ABI_generator_mock_positive':abi_positive,'actual_ABI_generator_mock_negatives':abi_negative,'actual_dispatcher_publication_statement_positive':publication_positive,'actual_dispatcher_publication_statement_negatives':publication_negative,'actual_driver_configure_ABI_before_build_AST':True,'actual_dispatcher_576MiB_budget_statement_positive':budget_positive,'actual_dispatcher_576MiB_budget_statement_negatives':budget_negative,'compiler_executed':False,'full_actual_owner_request_consumer':'Reused accepted ordinary-execution/consume.stdout, not rerun','root_or_Docker_or_lease':False})
print(json.dumps({'status':'PASS_CHEAP_PROPOSAL_CONSUMERS','guard_positive':positive,'guard_negative':negative,'ABI_positive':abi_positive,'ABI_negative':abi_negative,'compiler':False}))
