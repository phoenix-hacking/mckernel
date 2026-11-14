# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Bounded observer-only correction: consumes already-compiled object/captured NM.
# No subprocess/compiler/provider/source changes.
from pathlib import Path
import hashlib,json,os
D=Path(__file__).resolve().parent
PREVIOUS=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/next-memory-bridge-rust-20261023-1')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
def exclusive(p,obj):
 fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
recipe_path=D/'NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json';assert sha(recipe_path)=='295d258e7c22789993770d6b155c21dfc16863179d992d92405aa6792b4790d3'
recipe=json.loads(recipe_path.read_text());compiled=json.loads((D/'COMPILE-OBJECT-RECEIPT.json').read_text());obj=Path(compiled['object']['path']);assert sha(obj)==compiled['object']['sha256']
j=json.loads((D/'actual-fullcrate-compiler-capture-1/whole-join.json').read_text());n=json.loads((D/'actual-fullcrate-nm-capture-1/whole-join.json').read_text())
for result in [j,n]:
 assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and not result['timed_out']
for name in ['stdout','stderr']:
 assert sha(D/'actual-fullcrate-nm-capture-1'/name)==n['captures'][name]['sha256']
oldreceipt=PREVIOUS/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json';assert sha(oldreceipt)=='0997088697285bce8a5cf30512a9f6eed91a472b7153271198159f6a4e32e261'
oldmeta=json.loads(oldreceipt.read_text());old=Path(oldmeta['nm_stdout']['path']);assert sha(old)==oldmeta['nm_stdout']['sha256']
def rows(path):return [line.split() for line in path.read_text().splitlines() if line.strip()]
a=rows(old);b=rows(D/'actual-fullcrate-nm-capture-1/stdout')
def unresolved(rows):return {r[-1] for r in rows if len(r)>=2 and r[-2]=='U'}
before=unresolved(a);after=unresolved(b)
added={'process_timer_runtime_offsets','process_timer_spin_lock_bridge','process_timer_spin_unlock_bridge','process_timer_lapic_enable_bridge','process_timer_lapic_disable_bridge'}
assert len(before)==556 and len(after)==560
assert before-after=={'set_timer'} and after-before==added
symbols={}
for name,kind in [('set_timer','T'),('timer_set_timer_body_result','T'),('process_sched_set_timer_bridge','T'),('get_this_cpu_local_var','T'),('time_sharing','U'),*[(name,'U') for name in sorted(added)],('x86_init_text_end_bridge','T'),('_end','U'),('x86_init_text_map_kernel_start_bridge','T'),('x86_init_normal_set_large_bridge','T'),('x86_map_kernel_start_geometry','U')]:
 found=[r for r in b if r[-1]==name];assert len(found)==1 and found[0][-2]==kind,(name,found);symbols[name]=found
assert len(recipe['source_inputs'])==78
assert all(sha(Path(r['private']['path']))==r['private']['sha256'] for r in recipe['source_inputs'].values())
exclusive(D/'OBSERVER-FAILURE-1.json',dict(scope=recipe['scope'],status='PRESERVED_OBSERVER_ASSERTION_FAILURE_COMPILER_PASSED',original_runner=pin(D/'run_actual_fullcrate.py'),error='AssertionError:560 at undefined_count==597',cause='Broad equivalence harness ledger593->597 was incorrectly applied to distinct four-cfg production Rust recipe. Same production profile baseline is556->560.',compiler_invocations=1,compiler_failures=0,compiler_object=compiled['object'],nm_capture_join=pin(D/'actual-fullcrate-nm-capture-1/whole-join.json'),correction='Read-only captured actual symbols against pinned accepted same-profile symbol table; no compile/NM/source replay.'))
exclusive(D/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json',dict(scope=recipe['scope'],status='PASS_ACTUAL_78INPUT_PRODUCTION_RUST_OBJECT_AFTER_OBSERVER_ONLY_CORRECTION',exact_granted_recipe=pin(recipe_path),source_bindings=pin(D/'SOURCE-BINDINGS.json'),source_count=78,source_inputs_unchanged=True,compiler_invocations=1,compiler_failures=0,observer_failures=1,observer_corrections=1,compiler_seconds=j['seconds'],compiler_command=pin(D/'actual-fullcrate-compiler-capture-1/command.json'),compiler_whole_join=pin(D/'actual-fullcrate-compiler-capture-1/whole-join.json'),nm_command=pin(D/'actual-fullcrate-nm-capture-1/command.json'),nm_whole_join=pin(D/'actual-fullcrate-nm-capture-1/whole-join.json'),durable_object_receipt_before_nm=pin(D/'COMPILE-OBJECT-RECEIPT.json'),object=compiled['object'],actual_profile=pin(D/'ACTUAL-FULLCRATE-PROFILE.json'),actual_symbol_rows=symbols,production_U_delta=dict(baseline_receipt=pin(oldreceipt),before=556,after=560,removed=['set_timer'],added=sorted(added),all_other_U_exactly_unchanged=True),broad_harness_U_ledger='593->597 remains separate expected source preparation; broad harness not executed',observer_failure=pin(D/'OBSERVER-FAILURE-1.json'),observer_correction_source=pin(Path(__file__)),retirement='compiler/NM return0/directjoined/groupabsent/closedstreams/errornull/retirementerrornull',CPU6_released=True,canonical_changes=0,whole_C_TU_default_link_native='OPEN',independent_source_ABI_review='REQUIRED_BEFORE_CANONICAL'))
print(json.dumps(dict(status='PASS_CORRECTED_OBSERVER_NO_COMPILER_REPLAY',receipt=pin(D/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json'),object=compiled['object'],CPU6_released=True)))
