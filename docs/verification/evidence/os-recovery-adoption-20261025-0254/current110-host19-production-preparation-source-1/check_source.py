"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only source/profile checks and isolated pure clock cases. No execution gates.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

D = Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text())
def ref(p):
    raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

profile=read(D/'PROFILE.SOURCE-ONLY.json')
ready=read(D/'SOURCE-READY.json')
assert profile['request_sha256'] is None and profile['runtime_authority'] is None
for tool in ready['tools']:
    assert ref(Path(tool['successor']['path'])) == tool['successor']
    assert ref(Path(tool['diff']['path'])) == tool['diff']
    ast.parse(Path(tool['successor']['path']).read_text())
assert ref(D/'ROOT-NEXT-STEPS.NOT-AUTHORITY.json') == ready['next_steps']
source_map=read(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')
assert len(source_map['files']) == 112
assert {str(p.relative_to(D/'rust-subtree')) for p in (D/'rust-subtree').rglob('*') if p.is_file()} == {r['relative'] for r in source_map['files']}
for row in source_map['files']:
    assert ref(Path(row['snapshot']['path'])) == row['snapshot']
    st=Path(row['snapshot']['path']).lstat()
    assert st.st_nlink == 1 and not Path(row['snapshot']['path']).is_symlink()

# Import only defines functions; never call execute, holder, publisher or guard.
spec=importlib.util.spec_from_file_location('current110_readonly_source_api',D/'run_build_only.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
try: runner.commands_for_plan(profile)
except RuntimeError as exc: assert 'Root must bind new exact request SHA256' in str(exc)
else: raise AssertionError('unbound request template must fail literal source API')
bound=copy.deepcopy(profile)
bound['request_sha256']='0'*64  # memory-only structural witness, no Root authority
commands=runner.commands_for_plan(bound)
assert len(commands)==5 and commands==profile['exact_commands']
assert runner.BUDGET==23259332608 and runner.DEADLINE==1793165769
old=read(D.parent/'ROOT-CURRENT109-NEXT-DEFAULT-BUILD-ADMISSION-1/PROFILE.SOURCE-ONLY.json')
assert commands[1]==old['exact_commands'][1] and commands[4]==old['exact_commands'][4]
for index in [0,2,3]:
    before=old['exact_commands'][index]['argv'];after=commands[index]['argv']
    remaining=after.copy()
    additions=4 if index==0 else (1 if index==2 else 3)
    if index==0:
        flags=['f03_perf_alloc_bridges_selected_candidate','f06_rt_sigreturn_syscall_candidate','f06_rt_sigreturn_set_signal_candidate','f06_rt_sigreturn_check_signal_candidate']
        for flag in flags:
            n=remaining.index(flag);assert remaining[n-1]=='--cfg';del remaining[n-1:n+1]
    else:
        flags=['-DMCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES'] if index==2 else ['-DMCKERNEL_RUST_F06_RT_SIGRETURN_'+s for s in ['SYSCALL','SET_SIGNAL','CHECK_SIGNAL']]
        for flag in flags: remaining.remove(flag)
    assert remaining==before

# Execute only two pure definitions against fake time and fake boot data.
tree=ast.parse((D/'build_only_worker.py').read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'require','window_remaining'}]
class FakeTime:
    CLOCK_BOOTTIME=7
    def __init__(self,values): self.values=values
    def time(self): return self.values[0]
    def monotonic(self): return self.values[1]
    def clock_gettime(self,kind): assert kind==7;return self.values[2]
class BootPath:
    value='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
    def __init__(self,path): assert path=='/proc/sys/kernel/random/boot_id'
    def read_text(self): return self.value
cutoffs=profile['fixed_three_clock_cutoffs']
namespace=dict(CUTOFFS=cutoffs,BOOT=BootPath.value,Path=BootPath)
exec(compile(ast.Module(body=nodes,type_ignores=[]),'worker-exact-pure-functions','exec'),namespace)
cases=0
for values,should_pass in [([c-10 for c in cutoffs],True)]+[([c if n==i else c-10 for n,c in enumerate(cutoffs)],False) for i in range(3)]:
    namespace['time']=FakeTime(values)
    try:
        result=namespace['window_remaining']()
        assert should_pass and result==10
    except RuntimeError: assert not should_pass
    cases+=1
namespace['time']=FakeTime([c-10 for c in cutoffs]);BootPath.value='different-boot'
try:namespace['window_remaining']()
except RuntimeError:cases+=1
else:raise AssertionError('boot drift must reject')
print(json.dumps(dict(status='PASS_SOURCE_ONLY_LITERAL_API_AND_PURE_CLOCK_CHECKS',closed_Rust_files=112,
    exact_commands=5,unchanged_process_and_link_argv=True,pure_clock_cases=cases,
    null_request_rejected=True,memory_only_structural_request_not_authority=True,
    artifact_gates_executed=False,live_guard_executed=False,compiler_commands=0)))
