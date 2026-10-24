"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pre-execution source binding correction; same selected lock symbol, no compile.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
Q=Path(__file__).resolve().parent;P=Q.parent;H=Q/'sourcehandoff'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
 with p.open('x') as f:f.write(s)
def write(p,j):put(p,json.dumps(j,indent=2)+'\n')
def main():
 H.mkdir()
 oldready=P/'sourcehandoff/EXECUTABLE-READY.PAGE-FAULT-PREPARE96.NOT-GRANTED.json'
 olddriver=P/'sourcehandoff/run_owned_page_fault_prepare96_once.py'
 assert pin(oldready)['sha256']=='fce078ca8da0cea8def5e2cc0ef80579042733af363419b46eb4cb5111ba72d3'
 assert not (P/'sourcehandoff/ROOT-GRANT.json').exists() and not (P/'output-first-candidate-1').exists()
 shutil.copytree(P/'candidate',Q/'candidate');shutil.copytree(P/'fixture',Q/'fixture')
 a='crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq('
 b='__ihk_mc_spinlock_lock_noirq('
 corrections=[]
 for rel in ['candidate/kernel/rust/process_helpers.rs','fixture/page_fault_prepare.ACTUAL-RUST.inc']:
  path=Q/rel;before=path.read_text();assert before.count(a)==1;after=before.replace(a,b,1)
  if rel.startswith('candidate'):
   assert after.count('    fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock);')==1
  path.write_text(after)
  corrections.append(dict(path=str(path),before=pin(P/rel),after=pin(path)))
  put(H/(Path(rel).name+'.ONLY-EXISTING-C-ABI-LOCK-BINDING.diff'),''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='unrun-module-qualified-source/'+rel,tofile='existing-C-ABI-symbol/'+rel)))
 fixture=Q/'fixture/actual_provider.rs';s=fixture.read_text()
 needle='mod spinlock_helpers { use crate::abi::IhkSpinlock;extern "C" { pub fn __ihk_mc_spinlock_lock_noirq(lock:*mut IhkSpinlock); } }\n'
 assert s.count(needle)==1
 fixture.write_text(s.replace(needle,needle+'use spinlock_helpers::__ihk_mc_spinlock_lock_noirq;\n',1))
 correction=dict(scope=SCOPE,status='PREEXEC_SOURCE_TYPE_BINDING_CORRECTION_NO_COMPILER_OR_JOB',
  original_unrun_ready=pin(oldready),original_unrun_driver=pin(olddriver),
  finding='spinlock_helpers::IhkSpinlock and abi::IhkSpinlock are distinct Rust types. The original C macro selects __ihk_mc_spinlock_lock_noirq, and process_helpers already declares that same C ABI symbol with *mut abi::IhkSpinlock.',
  disposition='Use existing unconditional extern declaration and same selected Rust-exported symbol. No new pointer cast, getter, C helper, lock implementation, lock/ref/ownership/ABI/ordering policy.',
  exact_source_changes=corrections,fixture_binding=pin(fixture),
  lock_argument='The original &vm->page_table_lock address and lifetime are unchanged. All preparation outcomes retain it for the original C out: unlock.',
  candidate_C=pin(Q/'candidate/kernel/process.c'),candidate_Rust=pin(Q/'candidate/kernel/rust/process_helpers.rs'),
  F01_getter_dependency=pin(P/'sourcehandoff/F01-TYPED-PROVIDER-DEPENDENCY.json'),
  original96_cases_oracles_commands_unchanged=True,old_unrun_ready_not_an_executable_queue=True,
  compiler_jobs=0,CPU_reservations=0,next_unexpected='STOP_EXPERT_ESCALATION_NO_AUTOMATIC_RETRY')
 write(H/'PREEXEC-LOCK-TYPE-BINDING-CORRECTION.json',correction)
 r=json.loads((P/'sourcehandoff/EXACT-PAGE-FAULT-PREPARE96.NOT-GRANTED.json').read_text())
 for row in r['commands']:
  row['argv']=[arg.replace(str(P/'fixture'),str(Q/'fixture')).replace(str(P/'output-first-candidate-1'),str(Q/'output-first-candidate-1')) for arg in row['argv']]
  row['cwd']=str(Q/'output-first-candidate-1')
 bindings={}
 for name,value in r['input_bindings'].items():
  if name.startswith(str(P/'fixture')+'/') or name.startswith(str(P/'candidate')+'/'):
   path=Path(name.replace(str(P),str(Q),1));bindings[str(path)]=pin(path)
  else:bindings[name]=value
 bindings[str(H/'PREEXEC-LOCK-TYPE-BINDING-CORRECTION.json')]=pin(H/'PREEXEC-LOCK-TYPE-BINDING-CORRECTION.json')
 r.update(input_bindings=bindings,preexec_lock_binding_correction=pin(H/'PREEXEC-LOCK-TYPE-BINDING-CORRECTION.json'))
 rf=H/'EXACT-PAGE-FAULT-PREPARE96.NOT-GRANTED.json';write(rf,r)
 driver=H/olddriver.name;shutil.copy2(olddriver,driver)
 ready=json.loads(oldready.read_text())
 ready.update(recipe=pin(rf),driver=pin(driver),preparer=pin(Path(__file__)),preexec_lock_binding_correction=pin(H/'PREEXEC-LOCK-TYPE-BINDING-CORRECTION.json'),
              private_C=pin(Q/'candidate/kernel/process.c'),private_Rust=pin(Q/'candidate/kernel/rust/process_helpers.rs'))
 ready['preflight_history_bindings'] += [pin(oldready),pin(olddriver),pin(H/'PREEXEC-LOCK-TYPE-BINDING-CORRECTION.json')]
 readyfile=H/oldready.name;write(readyfile,ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(readyfile),recipe=pin(rf),driver=pin(driver),correction=pin(H/'PREEXEC-LOCK-TYPE-BINDING-CORRECTION.json'),C=ready['private_C'],Rust=ready['private_Rust'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
