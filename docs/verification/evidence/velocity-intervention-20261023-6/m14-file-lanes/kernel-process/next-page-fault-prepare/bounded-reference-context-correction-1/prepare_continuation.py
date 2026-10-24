"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One concrete fixture lexical-context correction; no compiler, test or CPU lease.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
Q=Path(__file__).resolve().parent;BASE=Q.parent;P=BASE/'preexec-lock-binding-correction-1'
H=Q/'sourcehandoff';F=Q/'fixture';O=Q/'output-first-candidate-1';PH=P/'sourcehandoff'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
def write(p,j):put(p,json.dumps(j,indent=2)+'\n')
def main():
 H.mkdir();F.mkdir()
 failure=PH/'PAGE-FAULT-PREPARE96-FIRST-FAILURE-1.json'
 assert pin(failure)['sha256']=='de43da649e8970f488606c86b9593031cbee95718e8303e7b01a5858349b210f'
 j=json.loads(failure.read_text())
 assert j['CPU6_released'] and [row['join']['returncode'] for row in j['records']]==[0,0,0,0,1]
 oldready=PH/'EXECUTABLE-READY.PAGE-FAULT-PREPARE96.NOT-GRANTED.json'
 olddriver=PH/'run_owned_page_fault_prepare96_once.py'
 r=json.loads((PH/'EXACT-PAGE-FAULT-PREPARE96.NOT-GRANTED.json').read_text())
 retained=j['durable_objects']['Rust_fixture'];rp=Path(retained['path']);st=rp.stat()
 assert retained['sha256']=='218f089a7b585e712663b9fd1f7d1f29a7f69a9d509e62d3538ac4fa959821fc' and retained['size']==3696
 assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(retained[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 before=(P/'fixture/actual_parity.c').read_text()
 include='#include "original_page_fault_prepare.ACTUAL-C-BLOCK.inc"'
 assert before.count(include)==1 and before.count('static int original(')==1
 assert before.index('struct result c=run(0),r=run(1)')>before.index('static int original(')
 original=(P/'fixture/original_page_fault_prepare.ACTUAL-C-BLOCK.inc').read_text()
 assert original.count('__FUNCTION__')==1 and '__func__' not in original
 actual_full=(P/'fixture/original_page_fault.ACTUAL-C-FULL-REFERENCE.inc').read_text()
 assert actual_full.startswith('int page_fault_process_memory_range(') and original.strip() in actual_full
 replacement='''/* Restore the extracted block's original enclosing function identity.
 * The strict logger oracle below remains unchanged. */
#define __FUNCTION__ "page_fault_process_memory_range"
'''+include+'\n#undef __FUNCTION__'
 after=before.replace(include,replacement,1)
 put(F/'actual_parity.c',after)
 shutil.copy2(P/'fixture/original_page_fault_prepare.ACTUAL-C-BLOCK.inc',F/'original_page_fault_prepare.ACTUAL-C-BLOCK.inc')
 diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='preserved-runtime-failure/actual_parity.c',tofile='original-function-context-restored/actual_parity.c'))
 put(Q/'ONLY-ORIGINAL-FUNCTION-LEXICAL-CONTEXT.diff',diff)
 caps=PH/'actual-first-candidate-capture-1'
 evidence=[pin(caps/name/'whole-join.json') for name in ['00-actual-Rust-page-fault-prepare','01-actual-real-header-ABI']]
 stdout=caps/'04-actual-page-fault-prepare96-execute/stdout'
 assert stdout.read_text()=='FAIL functional page-fault prepare line=63 comparisons=1 scenario=0 reason=0 debug=255\n'
 correction=dict(scope=SCOPE,status='SOLE_BOUNDED_FIXTURE_REFERENCE_FUNCTION_CONTEXT_CORRECTION_NO_EXECUTION',
  original_failure=pin(failure),actual_stdout=pin(stdout),original_ready=pin(oldready),original_driver=pin(olddriver),
  root_cause='The original block uses __FUNCTION__ for its bounds logger. Its real enclosing function is page_fault_process_memory_range; the fixture wrapper is static int original. At scenario0/debug255 the C reference executes first and passes original to the unchanged strict %s oracle, failing before Rust invocation. The earlier debug0 comparison completed1.',
  exact_correction='Restore only the original __FUNCTION__ lexical value in the extracted reference block, with scoped define/undef around its unchanged include. Do not alter the strict logger assertion, format/arguments, debug255, event/state/error oracle, scenario matrix or Rust implementation.',
  original_block=pin(P/'fixture/original_page_fault_prepare.ACTUAL-C-BLOCK.inc'),
  original_full_function=pin(P/'fixture/original_page_fault.ACTUAL-C-FULL-REFERENCE.inc'),
  corrected_C_fixture=pin(F/'actual_parity.c'),diff=pin(Q/'ONLY-ORIGINAL-FUNCTION-LEXICAL-CONTEXT.diff'),
  unchanged_product_Rust=pin(P/'candidate/kernel/rust/process_helpers.rs'),unchanged_product_C=pin(P/'candidate/kernel/process.c'),
  unchanged_Rust_object_reused=retained,successful_Rust_and_ABI_results_reused=evidence,
  original_indices_reexecuted=[2,3,4,5],successful_vectors_not_counted_as_acceptance=1,
  expected_comparisons=96,strict_oracles_unchanged=True,compiler_jobs=0,CPU_reservations=0,
  history_not_reset=True,next_unexpected='STOP_DIFFERENT_EXPERT_NO_FURTHER_AUTHOR_CORRECTION_OR_RETRY')
 write(H/'BOUNDED-REFERENCE-CONTEXT-CORRECTION.json',correction)
 cmds=[]
 for row in r['commands'][2:]:
  row=dict(row);row['argv']=[arg.replace(str(P/'output-first-candidate-1'),str(O)).replace(str(P/'fixture/actual_parity.c'),str(F/'actual_parity.c')) for arg in row['argv']]
  row['argv']=[str(rp) if arg==str(O/'actual_provider.o') else arg for arg in row['argv']]
  row['cwd']=str(O);cmds.append(row)
 r['commands']=cmds
 r['tools']={key:value for key,value in r['tools'].items() if key in ['/usr/bin/gcc-9','/usr/bin/nm']}
 for path in [F/'actual_parity.c',F/'original_page_fault_prepare.ACTUAL-C-BLOCK.inc',failure,H/'BOUNDED-REFERENCE-CONTEXT-CORRECTION.json']:
  r['input_bindings'][str(path)]=pin(path)
 r.update(status='SOLE_PAGE_FAULT96_REFERENCE_CONTEXT_FOUR_COMMAND_CONTINUATION_READY_NO_GRANT',
  reused_successful_Rust_fixture=retained,reused_successful_commands=evidence,
  original_command_indices=[2,3,4,5],correction=pin(H/'BOUNDED-REFERENCE-CONTEXT-CORRECTION.json'))
 r['failure_history'].update(first_actual_page_fault96_reference_context_failure=pin(failure),
  sole_bounded_reference_context_correction=pin(H/'BOUNDED-REFERENCE-CONTEXT-CORRECTION.json'),history_not_reset=True,
  next_unexpected_result='STOP_DIFFERENT_EXPERT_NO_FURTHER_AUTHOR_CORRECTION_OR_RETRY')
 rf=H/'EXACT-PAGE-FAULT-PREPARE96-CONTINUATION.NOT-GRANTED.json';write(rf,r)
 driver=olddriver.read_text()
 driver=driver.replace('EXACT-PAGE-FAULT-PREPARE96.NOT-GRANTED.json','EXACT-PAGE-FAULT-PREPARE96-CONTINUATION.NOT-GRANTED.json')
 driver=driver.replace('EXECUTABLE-READY.PAGE-FAULT-PREPARE96.NOT-GRANTED.json','EXECUTABLE-READY.PAGE-FAULT-PREPARE96-CONTINUATION.NOT-GRANTED.json')
 driver=driver.replace('PAGE-FAULT-PREPARE96-FIRST-FAILURE-1.json','PAGE-FAULT-PREPARE96-BOUNDED-CONTINUATION-FAILURE-1.json')
 driver=driver.replace("len(r['commands'])==6","len(r['commands'])==4")
 driver=driver.replace('six-command','four-command-continuation')
 driver=driver.replace(' actual_comparisons=0;symbols_witness={}',""" reused=r['reused_successful_Rust_fixture']
 st=Path(reused['path']).stat()
 assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(reused[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
 durable['Rust_fixture_reused']=reused
 actual_comparisons=0;symbols_witness={}""")
 driver=driver.replace('actual_commands=6,','actual_commands=4,previous_successful_commands_reused=2,complete_chain_commands=6,')
 driverfile=H/'run_owned_page_fault_prepare96_continuation_once.py';put(driverfile,driver)
 ready=json.loads(oldready.read_text())
 ready.update(status='SOLE_PAGE_FAULT96_BOUNDED_FOUR_COMMAND_CONTINUATION_READY_NO_GRANT',
  recipe=pin(rf),driver=pin(driverfile),preparer=pin(Path(__file__)),prepared_commands=4,
  previous_successful_commands_reused=2,original_command_indices=[2,3,4,5],
  correction=pin(H/'BOUNDED-REFERENCE-CONTEXT-CORRECTION.json'))
 ready['preflight_history_bindings'] += [pin(oldready),pin(olddriver),pin(failure),pin(stdout),*evidence,pin(H/'BOUNDED-REFERENCE-CONTEXT-CORRECTION.json')]
 readyfile=H/'EXECUTABLE-READY.PAGE-FAULT-PREPARE96-CONTINUATION.NOT-GRANTED.json';write(readyfile,ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(readyfile),recipe=pin(rf),driver=pin(driverfile),correction=pin(H/'BOUNDED-REFERENCE-CONTEXT-CORRECTION.json'),compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
