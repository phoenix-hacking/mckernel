"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure/read-only Source31 interface checks; never constructs an operation owner.
"""
from pathlib import Path
import ast,hashlib,json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import final_contract as mc

def main():
 checks=[]
 for p in sorted(HERE.glob('*.py')):ast.parse(p.read_bytes(),str(p))
 checks.append('all private Python syntax')
 assert mc.CUTOFFS==[1793165769.0,947874.5689514667,963213.6960030915]
 checks.append('fixed actual12h cutoffs in wall/mono/boot order')
 command=mc.fixture_command('0'*32)
 assert command[-2:]==[mc.PREP['fixture_base']+'/fixture/run_final_suffix.py','--execute']
 assert not any(x in command for x in ['--cc','--rustc'])
 checks.append('exact final suffix command without compiler arguments')
 results=mc.validate_retained_current()
 assert len(results)==26
 checks.append('all26 retained receipts and joined proofs')
 expected={'ring-C','ring-Rust','oversize-Rust'}
 tree=ast.parse((HERE/'final_contract.py').read_text())
 functions={n.name:ast.get_source_segment((HERE/'final_contract.py').read_text(),n) for n in tree.body if isinstance(n,ast.FunctionDef)}
 assert "expected={'ring-C','ring-Rust','oversize-Rust'}" in functions['validate_fixture_tree']
 assert "['ihkmond-Rust','ring-C-helper']" in functions['output_tree_bytes']
 assert "'RETAINED-INPUTS.SOURCE-ONLY.json'" in functions['verify_request_inputs']
 checks.append('three-only join inventory, distinct symlink helper, exact preparation inventory')
 invalid=dict(status='PASS_RETAINED26_AND_FINAL_THREE_MOCK_ONLY',retained_daemon_cases=26,new_daemon_cases=0,compilers_executed=1,remaining_invocations_executed=3,normal_C_ring_parity=True,Rust_oversized_read_proposal=True,native_acceptance=False,provider_Rust_link_closure=False,M15_file_closure=False)
 try:mc.validate_summary(invalid)
 except ValueError:pass
 else:raise AssertionError('compiler execution summary accepted')
 invalid['compilers_executed']=0;mc.validate_summary(invalid)
 invalid['native_acceptance']=True
 try:mc.validate_summary(invalid)
 except ValueError:pass
 else:raise AssertionError('native claim accepted')
 checks.append('compiler replay and native scope claims refused')
 assert mc.PREP['command_template'].count('--stack=8388608:8388608')==1 and '--stack=2097152:2097152' not in mc.PREP['command_template']
 checks.append('fixture controller command binds hard/soft8MiB')
 raw=(HERE/'owned_process_stack8.py').read_text();tree=ast.parse(raw)
 rows=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CHILD_STACK_BYTES' for t in n.targets));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='apply_child_stack')
 import types
 calls=[];fake=types.SimpleNamespace(RLIMIT_STACK='STACK');fake.setrlimit=lambda kind,pair:calls.append((kind,pair));fake.getrlimit=lambda kind:calls[-1][1];namespace={'resource':fake}
 exec(compile(ast.Module(body=[rows,fn],type_ignores=[]),'pure-child-stack-control','exec'),namespace)
 for label,bound in [('ring-C',8388608),('ring-Rust',2097152),('oversize-Rust',2097152)]:
  calls.clear();namespace['apply_child_stack'](label);assert calls==[('STACK',(bound,bound))]
 checks.append('C8MiB and both Rust2MiB child limits with fake resource only')
 row=next(r for r in mc.PREP['source_files'] if r['relative'].endswith('/fixture/owned_process.py'));assert row['source']['sha256']==hashlib.sha256((HERE/'owned_process_stack8.py').read_bytes()).hexdigest()
 checks.append('staged owner adapter bound to stack successor bytes')
 print(json.dumps(dict(status='PASS_SOURCE_ONLY',checks=checks,checks_count=len(checks),workload_invocations=0,compiler_invocations=0)))
if __name__=='__main__':main()
