"""Synthetic execution of the actual changed producer body; no compiler runs."""
from pathlib import Path
import json,hashlib,shlex,re
O=Path(__file__).parent;R=Path('/home/holden/mckernel');E=O/'producer-fixture-1';E.mkdir();real_process=R/'kernel/process.c';extension=(O/'production-driver-extension.py').read_text();contract=json.loads((O/'C-ABI-expression-contract.json').read_text());results=[]
class Refused(RuntimeError):pass

def fixture(name,expected_failure=None):
 root=E/name;root.mkdir();build=root/'build';(build/'kernel').mkdir(parents=True);evidence=root/'evidence';evidence.mkdir();crate=build/'release-fp-regs-production';crate.mkdir()
 for mode in ['native','legacy']:(crate/(mode+'-mckernel_rust.o')).write_bytes(('SYNTHETIC-NOT-COMPILED-'+mode).encode())
 rows=[dict(file=str(real_process),directory=str(build/'kernel'),arguments=['/usr/bin/cc','-DMCKERNEL_RUST_PROCESS_HELPERS','-c',str(real_process),'-o',str(build/'process.o')])]
 if name=='missing-selection':rows[0]['arguments'].remove('-DMCKERNEL_RUST_PROCESS_HELPERS')
 if name=='duplicate-row':rows*=2
 (build/'compile_commands.json').write_text(json.dumps(rows));calls=[]
 def fail(ok,msg):
  if not ok:raise Refused(msg)
 def digest(path):
  if name=='process-source-drift' and Path(path)==real_process:return '0'*64
  if name=='Rust-source-drift' and Path(path)==R/'kernel/rust/process_helpers.rs':return '0'*64
  return hashlib.sha256(Path(path).read_bytes()).hexdigest()
 def emit(path,data):Path(path).write_text(json.dumps(data,indent=2)+chr(10))
 def run(argv,cwd,env,stdout,stderr,timeout,label,**kw):
  calls.append(dict(argv=argv,cwd=str(cwd),label=label,output_fsize=kw.get('output_fsize')))
  if '-c' in argv:
   assert '-Werror=implicit-function-declaration' in argv
   src=Path(argv[argv.index('-c')+1]);prefix='#line 1 '+json.dumps(str(real_process))+chr(10)+real_process.read_text();assert src.read_text().startswith(prefix)
   assert src.read_text().endswith(ns['RELEASE_TID_PROCESS_ASSERTIONS']);assert 'struct thread {' not in ns['RELEASE_TID_PROCESS_ASSERTIONS'];assert 'extern void __release_tid' not in ns['RELEASE_TID_PROCESS_ASSERTIONS']
   if name=='compile-refused':return 1
   Path(argv[argv.index('-o')+1]).write_bytes(('SYNTHETIC-PROOF-'+label).encode());return 0
  assert argv[:2]==['/usr/bin/nm','-S'];obj=Path(argv[-1]);assert obj.is_file();kind=obj.name
  lines=[]
  if kind=='selected-process.o':
   if name!='selected-TID-reference-missing':lines.append('                 U __release_tid')
   if name=='selected-C-hash-leak':lines.append('0000000000000010 0000000000000020 T process_destroy_thread_hash_detach_bridge')
  else:
   symbols=['__release_tid','process_destroy_thread_time_account_bridge','process_destroy_thread_hash_detach_bridge']
   if name=='native-hash-missing' and kind=='native-mckernel_rust.o':symbols.remove('process_destroy_thread_hash_detach_bridge')
   if name=='legacy-time-missing' and kind=='legacy-mckernel_rust.o':symbols.remove('process_destroy_thread_time_account_bridge')
   for i,symbol in enumerate(symbols):lines.append('%016x 0000000000000020 T %s'%(0x100+i*64,symbol))
   if name=='native-TID-duplicate' and kind=='native-mckernel_rust.o':lines.append('0000000000000900 0000000000000020 T __release_tid')
   if name=='native-hash-unresolved' and kind=='native-mckernel_rust.o':lines.append('                 U process_destroy_thread_hash_detach_bridge')
   if 'mckernel_rust' in kind:
    size='10' if name=='descriptor-size' else '20';lines.append('0000000000000500 00000000000000'+size+' d _ZN17process_helpers17RELEASE_TID_DEBUGE')
  Path(stdout).write_text(chr(10).join(lines)+chr(10));Path(stderr).write_text('SYNTHETIC STDERR' if name=='nm-stderr' else '');return 0
 ns=dict(Path=Path,json=json,shlex=shlex,_fail=fail,_sha256=digest,_atomic_json=emit,_run_process=run);exec(compile(extension,str(O/'production-driver-extension.py'),'exec'),ns)
 assert ns['RELEASE_TID_PROCESS_ASSERTIONS'].count('_Static_assert(')==len(contract['facts'])+len(contract['function_and_member_type_expressions'])
 for row in contract['facts']:assert row['C_expression']+'=='+str(row['required_value']) in ns['RELEASE_TID_PROCESS_ASSERTIONS']
 tools={'tools':{'cc':{'path':'/usr/bin/cc','version':'cc GCC 13.0' if name=='wrong-GCC' else 'cc GCC 14.3.1'},'nm':{'path':'/usr/bin/nm'}}}
 error=None
 try:ns['_validate_release_tid_production'](R,build,tools,evidence,{},root/'stdout',root/'stderr',35,[])
 except Refused as ex:error=str(ex)
 if expected_failure is None:
  assert error is None,error;proof=json.loads((evidence/'release-tid-production-checks.json').read_text());assert proof['status']=='PASS';assert len(proof['three_leaf_symbols'])==3;assert len(calls)==6
 else:assert error is not None and expected_failure in error,(name,error)
 results.append(dict(case=name,expected_refusal=expected_failure is not None,actual_refusal=error,external_processes=0,mocked_command_count=len(calls)))
 (root/'result.json').write_text(json.dumps(results[-1],indent=2)+chr(10))

fixture('positive')
for n,e in [('wrong-GCC','pinned GCC14'),('missing-selection','default selected process macro'),('duplicate-row','compile row count'),('process-source-drift','process source drift'),('Rust-source-drift','lifecycle/Rust source drift'),('selected-TID-reference-missing','actual selected destroy callback reference'),('selected-C-hash-leak','normal teardown symbol definition'),('native-hash-missing','normal teardown symbol definition'),('legacy-time-missing','normal teardown symbol definition'),('native-hash-unresolved','normal teardown unresolved symbol'),('native-TID-duplicate','symbol definition'),('descriptor-size','descriptor size'),('nm-stderr','symbol capture'),('compile-refused','full-process-selected failed')]:fixture(n,e)
summary=dict(status='PASS_SYNTHETIC_ACTUAL_THREE_LEAF_PRODUCER',cases=len(results),positive=1,expected_refusals=len(results)-1,C_layout_assertions=len(contract['facts']),C_type_assertions=len(contract['function_and_member_type_expressions']),actual_producer_sha256=hashlib.sha256(extension.encode()).hexdigest(),compiler_invocations=0,kernel_artifacts_produced=False,production_acceptance=False)
(E/'summary.json').write_text(json.dumps(summary,indent=2)+chr(10));print(json.dumps(summary))
