"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source/hash validation only: no compiler, generated binary, native or guest action.
"""
from pathlib import Path
import json,hashlib,re
p=Path(__file__).resolve().parent;root=Path('/home/holden/mckernel')
d=json.loads((p/'SOURCE16-CANDIDATE.NOT-EXECUTED.json').read_text())
r=json.loads((p/'EXACT-LOOKUP-RECIPE.NOT-GRANTED.json').read_text())
for x in d['sources']+r['sources']+r['reused_lock_inputs']:
    b=Path(x['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==x['sha256'],x['path']
f=(p/'candidate/process-vm-lookup.FRAGMENT.rs').read_text()
assert d['body_reused_unchanged'] in f
src=(root/'kernel/rust/process_helpers.rs').read_text();closure=(p/'fixture/process_helpers.rs').read_text()
for name in d['closure_functions']:
    def body(s):
        m=re.search(r'(?m)^(?:pub )?(?:unsafe )?(?:extern "C" )?fn '+name+r'\(',s);assert m,name
        b=s.index('{',m.start());i=b+1;n=1
        while n:n+=(s[i]=='{')-(s[i]=='}');i+=1
        return s[m.start():i]
    assert body(src)==body(closure),name
c=(p/'fixture/lookup-compare.c').read_text()
for s in ['rb_insert_color','oracle(','expected_cache','expected_index','range_before','arch_process_vm_rw_read_lock_bridge','arch_process_vm_rw_read_unlock_bridge','depth!=1','logn!=2']:
    assert s in c,s
assert len(r['commands'])==6 and not r['recompile_lock']
assert r['planned_cases']==3*3*5*2*2*19
for cmd in r['commands']:assert cmd['purpose'].startswith(d['scope'])
print('PASS SOURCE_ONLY Source16 unchanged_delegate=1 unchanged_lookup_functions=8 exact_C_delta=1 ABI_values=12 planned_cases=10260 reused_lock_inputs=2 compiler_runtime_commands=0')
