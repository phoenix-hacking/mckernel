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
 print(json.dumps(dict(status='PASS_SOURCE_ONLY',checks=checks,checks_count=len(checks),workload_invocations=0,compiler_invocations=0)))
if __name__=='__main__':main()
