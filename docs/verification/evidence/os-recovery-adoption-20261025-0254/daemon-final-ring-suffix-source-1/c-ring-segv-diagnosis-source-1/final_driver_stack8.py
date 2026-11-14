"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing source-bound BFD h990 driver specialized to one unchanged mock batch.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,sys
HERE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-sdk7-next-production-criterion-source-1/container64-owner-successor-source-1')
sys.path.insert(0,str(HERE))
sys.path.insert(0,'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-sdk7-next-production-criterion-source-1/container64-owner-successor-source-1/joined-task-observer-correction-source-1')
sys.path.insert(0,'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-sdk7-next-production-criterion-source-1/container64-owner-successor-source-1/joined-task-observer-correction-source-1/rust-output-temp-correction-source-1')
sys.path.insert(0,'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-sdk7-next-production-criterion-source-1/container64-owner-successor-source-1/joined-task-observer-correction-source-1/rust-output-temp-correction-source-1/pinned-helper-import-correction-source-1')
sys.path.insert(0,'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/daemon-final-ring-suffix-source-1/new12h-operation-preparation-1')
import final_contract as mc
import kernel_pids64

def main():
 mc.need(sys.argv[1:]==['--execute'],'exact mock driver mode')
 raw=Path('/preparation/PREPARATION.SOURCE-ONLY.json').read_bytes();mc.need(mc.sha(raw)==mc.PREPARATION_SHA,'exact mounted preparation')
 request=mc.json_bytes(Path('/request.json').read_bytes());nonce=request['nonce'];command=mc.fixture_command(nonce)
 mc.need(request['preparation']==dict(path=str(mc.PREPARATION),sha256=mc.PREPARATION_SHA),'request preparation differs')
 mc.need(request['driver']==dict(path=str(mc.DRIVER),sha256=mc.sha(Path('/driver.py').read_bytes())),'executing driver differs')
 mc.verify_mirror(Path(mc.PREP['container_source_parent']))
 mc.verify_retained_prefix('/retained-prefix')
 mc.verify_retained_mock('/retained-mock-build')
 binding=mc.json_bytes(Path('/preparation/OUTPUT-BINDING.ACTUAL.json').read_bytes());mc.need(binding['nonce']==nonce and binding['path']==mc.PREP['container_output'],'output binding nonce/path')
 capture=Path('/work/evidence');mc.need(not capture.exists(),'fresh driver capture required');capture.mkdir(mode=0o700)
 proof=kernel_pids64.observe();(capture/'kernel-pids64-before.json').write_bytes(mc.canonical(proof))
 helper_path=Path(mc.PREP['capture_helper']['path']);helper=helper_path.read_bytes();mc.need(mc.sha(helper)==mc.PREP['capture_helper']['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','exact existing capture helper')
 functions={'need','write','hashed','stop','members','cpu_used','process_start','terminal_unreaped','wait_terminal','owned_capture'}
 constants={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'};nodes=[]
 for item in ast.parse(helper).body:
  if isinstance(item,(ast.Import,ast.ImportFrom)):nodes.append(item)
  elif isinstance(item,ast.FunctionDef) and item.name in functions:nodes.append(item)
  elif isinstance(item,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in item.targets):nodes.append(item)
 mc.need({x.name for x in nodes if isinstance(x,ast.FunctionDef)}==functions,'complete h990 function closure')
 namespace={'__file__':str(helper_path),'__name__':'mock64_existing_capture'};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper_path),'exec'),namespace)
 for number in namespace['STOP_SIGNALS']:signal.signal(number,namespace['stop'])
 def limits():
  os.sched_setaffinity(0,{2})
  for kind,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,8<<20)]:resource.setrlimit(kind,(value,value))
 namespace['write'](capture/'command.json',dict(argv=command,scope=mc.PREP['scope']))
 signal.setitimer(signal.ITIMER_REAL,mc.PREP['timeout'])
 try:result=namespace['owned_capture'](dict(argv=command,scope=mc.PREP['scope']),capture,mc.PREP['timeout']-6,limits)
 finally:signal.setitimer(signal.ITIMER_REAL,0)
 namespace['write'](capture/'fixture-join.json',result)
 positive=mc.capture_ok(result) and result['captures']['stderr']['size']==0
 receipt=dict(schema='mckernel.daemon-pinned-helper-suffix64-driver-receipt.v1',scope=mc.PREP['scope'],status='FAIL_RETAINED_NO_RETRY',preparation_sha256=mc.PREPARATION_SHA,nonce=nonce,command=command,capture=result,kernel_pids64_before_sha256=mc.ref(capture/'kernel-pids64-before.json')['sha256'],production_main_executed=False,native_acceptance=False,provider_Rust_link_closure=False,M15_file_closure=False,retained_prefix_cases=26,new_corrected_daemon_cases=0,remaining_invocations_executed=0,compilers_executed=0,prefix_reexecuted=False,historical_1fff_extra_task_identity=None)
 if positive:
  summary=mc.validate_fixture_tree(Path('/work/fixture-output'),prefix=Path('/retained-prefix'),mock_prefix=Path('/retained-mock-build'),fixture_pid=result['pid'],retained=Path('/retained-current'));after=kernel_pids64.observe();namespace['write'](capture/'kernel-pids64-after.json',after)
  mc.need(after['controller_identity']==proof['controller_identity'] and after['selected_mount']==proof['selected_mount'],'pids controller changed')
  receipt.update(status='PASS_DAEMON_PINNED_HELPER_SUFFIX64_CAPTURE',remaining_invocations_executed=3,summary_sha256=mc.ref(Path('/work/fixture-output/summary.json'))['sha256'],kernel_pids64_after_sha256=mc.ref(capture/'kernel-pids64-after.json')['sha256'],fixture_cases=summary['retained_daemon_cases'])
 namespace['write'](capture/'receipt.json',receipt);print(json.dumps(dict(status=receipt['status'])))
 return 0 if receipt['status']=='PASS_DAEMON_PINNED_HELPER_SUFFIX64_CAPTURE' else 1
if __name__=='__main__':raise SystemExit(main())
