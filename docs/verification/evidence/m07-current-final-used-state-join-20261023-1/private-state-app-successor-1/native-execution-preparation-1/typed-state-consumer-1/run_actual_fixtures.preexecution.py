"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,time
D=Path(__file__).resolve().parent
E=Path('/home/holden/mckernel/docs/verification/evidence/m07-current-final-used-state-join-20261023-1/private-state-app-successor-1/native-execution-preparation-1/typed-state-consumer-1')
helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=helper.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw,str(helper));selected=[x for x in tree.body if getattr(x,'lineno',999)<147]
# The reviewed prefix ends after owned_capture, before source-authority/main logic.
assert isinstance(selected[-1],ast.FunctionDef) and selected[-1].name=='owned_capture'
ns={'__file__':str(helper)};exec(compile(ast.Module(body=selected,type_ignores=[]),str(helper),'exec'),ns)
bindings=json.loads((D/'FIXTURE-INPUT-BINDINGS.json').read_text())
for name,digest in bindings.items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest
os.sched_setaffinity(0,{0})
for limit,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(limit,(value,value))
cap=D/'actual-fixtures-1';cap.mkdir()
command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'test_typed_state.py')],'purpose':__doc__,'shell':False,'profile':{'cpu':0,'jobs':1,'AS':2<<30,'CPU':30,'wall':60,'grace':6,'FSIZE':32<<20,'NOFILE':256,'core':0}}
ns['write'](cap/'command.json',command)
j=ns['owned_capture'](command,cap,60,lambda:None);ns['write'](cap/'whole-join.json',j)
result={'scope':__doc__,'status':'PASS_ACTUAL_18_TYPED_STATE_CONSUMER_FIXTURES' if j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'] else 'FAIL_ACTUAL_FIRST_FIXTURE_CAPTURE_RETAINED','whole_join':j,'source_bindings':bindings,'native_app_or_state_instructions_executed':False,'modeled_output_TESTONLY':True,'CPU0_released':j['direct_child_joined'] and j['group_absent'] and j['closed_streams']}
ns['write'](D/'ACTUAL-FIXTURE-RESULT.json',result)
for path in [D/'ACTUAL-FIXTURE-RESULT.json',D/'FIXTURE-INPUT-BINDINGS.json',D/'run_actual_fixtures.py',*cap.iterdir()]:
 target=E/path.relative_to(D);target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(path.read_bytes())
print(json.dumps(result))
