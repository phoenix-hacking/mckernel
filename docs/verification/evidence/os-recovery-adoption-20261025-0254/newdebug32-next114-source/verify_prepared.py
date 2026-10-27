"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Separate prepared-source/profile readback only; never compile, guard or execute.
"""
from pathlib import Path
import json,hashlib,importlib.util,ast
P=Path(__file__).resolve().parent;E=P.parent;B=E/'current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/final-scope-source-1'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
a=json.loads((P/'PROFILE.SOURCE-ONLY.json').read_text());b=json.loads((B/'PROFILE.SOURCE-ONLY.json').read_text());d=json.loads((P/'COMPOSITION-DERIVATION.json').read_text());assert ref(B/'SOURCE-READY.json')['sha256']=='7340d457ebb4735240452c6c009fd9b0a0da98539f69b30629437430fca2526b'
assert a['exact_commands'][2:]==b['exact_commands'][2:]
r=list(a['exact_commands'][0]['argv']);r.remove('MCKERNEL_PROCESS_C_FILE=/src/kernel/process.c');r.remove('MCKERNEL_PROCESS_DDEBUG_FLAGS=0');idx=r.index('process_verbose_data');assert r[idx-1]=='--cfg';del r[idx-1:idx+1];assert r==b['exact_commands'][0]['argv']
c=list(a['exact_commands'][1]['argv']);[c.remove(x) for x in ['-DMCKERNEL_RUST_PROCESS_VERBOSE_DATA','-DMCKERNEL_PROCESS_DDEBUG_FLAGS=0','-DMCKERNEL_PROCESS_DDEBUG_FILE="/src/kernel/process.c"']];assert c==b['exact_commands'][1]['argv']
cm=Path(next(x['postimage']['path'] for x in a['inputs']['postimages'] if x['relative']=='kernel/CMakeLists.txt')).read_text()
for x in reversed(d['CMake_insertions']):assert cm.count(x['anchor']+x['addition'])==1;cm=cm.replace(x['anchor']+x['addition'],x['anchor'],1)
assert cm==Path(d['CMake_base']['path']).read_text()
smap=json.loads((P/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json').read_text());assert len(smap['files'])==119
for row in smap['files']:
 assert ref(row['snapshot']['path'])==row['snapshot']
 if row['relative'] not in ['lib.rs','process_verbose_data.rs']:assert row['snapshot']['sha256']==row['predecessor_snapshot']['sha256']
assert ref(P/'rust-subtree/process_verbose_data.rs')['sha256']=='8eaa8f0bff3d10a433fa88b899e56b9bd4aefd719c49f15c1487ffe335d65b27'
assert 'C-local debug storage requires coordinated companion config migration' in (P/'rust-subtree/process_verbose_data.rs').read_text()
assert 'process_verbose_local_companions' not in json.dumps(a['exact_commands'])
for name in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 assert (P/name).read_bytes()==(B/name).read_bytes();ast.parse((P/name).read_text())
for key in ['runtime_authority','request_sha256','actual_nonce','actual_root_adoption','actual_execution_review','actual_resource_authority','actual_output_root','actual_holder','native_custody_clearance']:assert a[key] is None
result=dict(scope=a['scope'],decision='PASS_PREPARED_SOURCE_PROFILE_READBACK_ONLY',profile=ref(P/'PROFILE.SOURCE-ONLY.json'),planned_base=ref(B/'SOURCE-READY.json'),Rust_files=119,unchanged_old_Rust_files=117,command_changes='Only Rust2env+1cfg and processC3defines',new_body_implementations=0,LOCAL14_selected=False,tools_byte_identical=True,source_controls=len(d['source_controls']),actual_compiler_runtime_canonical_Git_operations=0)
(P/'PREPARED-SOURCE-READBACK.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
