"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source and stubbed resource controls; never imports/executes an actual helper.
"""
from pathlib import Path
import ast,json,types
HERE=Path(__file__).resolve().parent

def main():
 source=(HERE/'owned_process_stack8.py').read_text();tree=ast.parse(source);checks=[]
 rows=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CHILD_STACK_BYTES' for t in n.targets));function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='apply_child_stack')
 # Isolated fake resource object: no actual getrlimit/setrlimit invocation.
 calls=[];fake=types.SimpleNamespace(RLIMIT_STACK='STACK');fake.setrlimit=lambda kind,pair:calls.append((kind,pair));fake.getrlimit=lambda kind:calls[-1][1]
 namespace={'resource':fake};exec(compile(ast.Module(body=[rows,function],type_ignores=[]),'pure-stack-control','exec'),namespace)
 for label,bound in [('ring-C',8388608),('ring-Rust',2097152),('oversize-Rust',2097152)]:
  calls.clear();namespace['apply_child_stack'](label);assert calls==[('STACK',(bound,bound))]
 checks.append('three exact per-child hard/soft stack values with fake resource')
 calls.clear()
 try:namespace['apply_child_stack']('Rust-daemon-build')
 except KeyError:pass
 else:raise AssertionError('unexpected compiler label admitted')
 assert calls==[];checks.append('unexpected/compiler label cannot change limits')
 fake.getrlimit=lambda kind:(1,1)
 try:namespace['apply_child_stack']('ring-C')
 except ValueError:pass
 else:raise AssertionError('wrong applied stack admitted')
 checks.append('applied resource mismatch fails closed')
 proposal=json.loads((HERE/'FIXTURE-COMMAND.RESOURCE-PROPOSAL.json').read_text());old=proposal['old_command'];new=proposal['proposed_command'];assert len(old)==len(new) and [(a,b) for a,b in zip(old,new) if a!=b]==[('--stack=2097152:2097152','--stack=8388608:8388608')];checks.append('fixture argv changes only exact stack limit')
 frame=0x3ff148;buffer=(4<<20)-4096;assert frame>buffer>2097152 and frame<8388608
 dis=(HERE/'fwrite_kmsg.constprop.0.disassembly.txt').read_text();assert 'sub    $0x3ff148,%rsp' in dis and '402815:' in dis
 checks.append('retained machine frame exceeds original2MiB and fits proposed8MiB')
 assert '(resource.RLIMIT_STACK, 8 << 20)' in source and "lambda: apply_child_stack(label)" in source
 checks.append('controller retains8MiB and h990 child preexec selects label stack')
 original=HERE.parent/'new12h-operation-preparation-1/final_driver.py';successor=HERE/'final_driver_stack8.py'
 assert original.read_text().replace('(resource.RLIMIT_STACK,2<<20)','(resource.RLIMIT_STACK,8<<20)')==successor.read_text();checks.append('driver changes only captured fixture stack2to8MiB')
 for p in HERE.glob('*.py'):ast.parse(p.read_bytes(),str(p))
 report=dict(status='PASS_SOURCE_STUB_CONTROLS_ONLY',scope=__doc__.splitlines()[0],checks=checks,checks_count=len(checks),actual_helper_runs=0,actual_resource_mutations=0,compiler_calls=0)
 (HERE/'PURE-TEST-RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
