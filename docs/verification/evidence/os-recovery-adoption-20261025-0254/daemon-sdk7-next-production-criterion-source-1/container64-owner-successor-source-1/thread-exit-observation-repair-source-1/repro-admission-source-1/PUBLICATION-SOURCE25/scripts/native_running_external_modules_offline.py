"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Closed compile/observe successor using the unchanged reviewed h990 child lifecycle.
No daemon, Rust compiler, original cases, or operation on import.
"""
from pathlib import Path
import ast,json,os,resource,signal,sys
HERE=Path(__file__).resolve().parent
# /driver.py is a bind mount, so use the source directory from the immutable repo.
HERE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-sdk7-next-production-criterion-source-1/container64-owner-successor-source-1/thread-exit-observation-repair-source-1/repro-admission-source-1')
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parents[1]))
import repro_contract as mc
import kernel_pids64

def main():
 mc.need(sys.argv[1:]==['--execute'],'exact reproducer mode')
 mc.need(mc.sha(Path('/preparation/PREPARATION.SOURCE-ONLY.json').read_bytes())==mc.PREPARATION_SHA,'mounted preparation differs')
 request=mc.json_bytes(Path('/request.json').read_bytes())
 mc.need(request['schema']=='mckernel.daemon-join-procfs64-request.v1','reproducer request required')
 mc.need(request['preparation']==dict(path=str(mc.PREPARATION),sha256=mc.PREPARATION_SHA),'request preparation differs')
 mc.need(request['driver']==dict(path=str(mc.DRIVER),sha256=mc.sha(Path('/driver.py').read_bytes())),'exact driver source')
 mc.verify_mirror(Path('/repro-src'))
 pin=mc.PREP['tool_pins']['cc'];mc.need(mc.sha(Path(pin['path']).read_bytes())==pin['sha256'],'same-image GCC differs')
 binding=mc.json_bytes(Path('/preparation/OUTPUT-BINDING.ACTUAL.json').read_bytes())
 mc.need(binding['nonce']==request['nonce'] and binding['path']==mc.PREP['container_output'],'output nonce/path differs')
 mc.need(mc.node('/work/fixture-output')==dict(path='/work/fixture-output',device=binding['device'],inode=binding['inode'],uid=1000,gid=1000,mode=0o700) and not list(Path('/work/fixture-output').iterdir()),'precreated empty output binding')
 capture=Path('/work/evidence');mc.need(not capture.exists(),'fresh evidence required');capture.mkdir(mode=0o700)
 before=kernel_pids64.observe();(capture/'kernel-pids64-before.json').write_bytes(mc.canonical(before))
 helper_path=Path(mc.PREP['capture_helper']['path']);helper=helper_path.read_bytes();mc.need(mc.sha(helper)==mc.PREP['capture_helper']['sha256'],'exact h990 helper')
 functions={'need','write','hashed','stop','members','cpu_used','process_start','terminal_unreaped','wait_terminal','owned_capture'}
 constants={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'};nodes=[]
 for item in ast.parse(helper).body:
  if isinstance(item,(ast.Import,ast.ImportFrom)):nodes.append(item)
  elif isinstance(item,ast.FunctionDef) and item.name in functions:nodes.append(item)
  elif isinstance(item,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in item.targets):nodes.append(item)
 mc.need({x.name for x in nodes if isinstance(x,ast.FunctionDef)}==functions,'complete unchanged h990 closure')
 namespace={'__file__':str(helper_path),'__name__':'joined_task_existing_capture'};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper_path),'exec'),namespace)
 for number in namespace['STOP_SIGNALS']:signal.signal(number,namespace['stop'])
 def limits():
  os.sched_setaffinity(0,{2})
  for kind,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(kind,(value,value))
 clean={k:v for k,v in os.environ.items() if not k.startswith('IHKMOND_') and k not in ['LD_PRELOAD','LD_LIBRARY_PATH','POSIXLY_CORRECT']};clean['LC_ALL']='C';os.environ.clear();os.environ.update(clean)
 commands=[mc.PREP['command_template'],mc.PREP['execute_argv']];captures=[]
 receipt=dict(schema='mckernel.daemon-join-procfs64-driver-receipt.v1',status='FAIL_RETAINED_NO_RETRY',scope=mc.PREP['scope'],preparation_sha256=mc.PREPARATION_SHA,nonce=request['nonce'],commands=commands,captures=captures,production_main_executed=False,native_acceptance=False,provider_Rust_link_closure=False,M15_file_closure=False,daemon_acceptance=False,historical_extra_task_identity=None)
 signal.setitimer(signal.ITIMER_REAL,mc.PREP['timeout'])
 try:
  for label,argv,seconds in [('compile',commands[0],60),('observe',commands[1],8)]:
   target=capture/label;target.mkdir(mode=0o700)
   namespace['write'](target/'command.json',dict(argv=argv,scope=mc.PREP['scope']))
   result=namespace['owned_capture'](dict(argv=argv,scope=mc.PREP['scope']),target,seconds,limits)
   captures.append(result);namespace['write'](target/'whole-join.json',result)
   expected=0 if label=='compile' else result.get('returncode')
   mc.need(expected in (0,2) and mc.capture_ok(result,expected) and result['captures']['stderr']['size']==0,'owned compile/observe failed')
   if label=='compile':mc.need(result['captures']['stdout']['size']==0,'unexpected compiler output')
  outcome=mc.validate_observation((capture/'observe/stdout').read_bytes(),captures[1]['pid'],captures[1]['returncode'])
  after=kernel_pids64.observe();namespace['write'](capture/'kernel-pids64-after.json',after)
  mc.need(after['controller_identity']==before['controller_identity'] and after['selected_mount']==before['selected_mount'],'pids controller moved')
  receipt.update(status='PASS_JOIN_PROCFS64_OBSERVATION_CAPTURE',outcome=outcome,executable=mc.ref(Path('/work/fixture-output/join-procfs-reproducer')),kernel_pids64_before_sha256=mc.ref(capture/'kernel-pids64-before.json')['sha256'],kernel_pids64_after_sha256=mc.ref(capture/'kernel-pids64-after.json')['sha256'])
 except BaseException as error:
  receipt['error']=type(error).__name__+': '+str(error)
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);namespace['write'](capture/'receipt.json',receipt)
 print(json.dumps(dict(status=receipt['status'],outcome=receipt.get('outcome'),daemon_acceptance=False)))
 return 0 if receipt['status']=='PASS_JOIN_PROCFS64_OBSERVATION_CAPTURE' else 1
if __name__=='__main__':raise SystemExit(main())
