"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,sys
D=Path(__file__).resolve().parent
E=Path('/home/holden/mckernel/docs/verification/evidence/m07-current-final-used-state-join-20261023-1/private-state-app-successor-1/native-execution-preparation-1/typed-state-consumer-1/state-case-binding-1')
assert sys.version.startswith('3.9.12 ')
h=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=h.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw,str(h));end=next(i for i,x in enumerate(tree.body) if isinstance(x,ast.FunctionDef) and x.name=='owned_capture');ns={'__file__':str(h)};exec(compile(ast.Module(body=tree.body[:end+1],type_ignores=[]),str(h),'exec'),ns)
selected=json.loads((D/'ACTUAL-SELECTED-COMMANDS.json').read_text())
for name,digest in selected['inputs'].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest
assert hashlib.sha256(Path(selected['tools']['gcc']['resolved']).read_bytes()).hexdigest()==selected['tools']['gcc']['sha256']
os.sched_setaffinity(0,{0})
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
rows=[];status='PASS_ACTUAL_26_TYPED_STATE_FIXTURES_AND_STATIC_PID1_COMPILE'
for operation in selected['commands']:
 cap=D/('actual-'+operation['label']+'-1');cap.mkdir();command=dict(operation,purpose=__doc__,shell=False);ns['write'](cap/'command.json',command)
 j=ns['owned_capture'](command,cap,90,lambda:None);ns['write'](cap/'whole-join.json',j);rows.append({'label':operation['label'],'capture':str(cap),'whole_join':j})
 if not (j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']):status='FAIL_FIRST_COMMAND_RETAINED';break
result={'scope':__doc__,'status':status,'commands':rows,'source_tool_and_profile':selected,'collector':ns['hashed'](D/'collector.init',32<<20) if status.startswith('PASS') else None,'CPU0_released':all(row['whole_join']['direct_child_joined'] and row['whole_join']['group_absent'] and row['whole_join']['closed_streams'] for row in rows),'native_or_register_state_execution':False,'model_fixture_data_TESTONLY':True,'runtime_acceptance':False}
ns['write'](D/'ACTUAL-26-FIXTURES-AND-COLLECTOR-RESULT.json',result)
for path in [D/'ACTUAL-26-FIXTURES-AND-COLLECTOR-RESULT.json',*[(Path(row['capture'])/name) for row in rows for name in ['command.json','started.json','direct-wait.json','direct-join.json','stdout','stderr','whole-join.json']]]:
 target=E/path.relative_to(D);target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(path.read_bytes())
print(json.dumps(result))
