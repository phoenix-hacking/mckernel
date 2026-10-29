#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Check this body's exact originals, providers, ABI/source and fixed command plan.
"""
import ast,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def bind(p):
 data=p.read_bytes();return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def verify(row):assert bind(Path(row['path']))==row,row['path']
for p in HERE.glob('*.py'):ast.parse(p.read_text())
pre=json.loads((HERE/'PREIMAGES.json').read_text())
for entry in pre['snapshots'].values():
 for key in ['canonical','snapshot']:verify(entry[key])
for row in pre['all_nine_root118_canonical_postimages'].values():verify(row)
for row in pre['real_header_inputs']:verify(row)
for key in ['source_adoption118','accepted_artifact_source_adoption116','original_body','retained_object_frontier','descriptor_identity']:verify(pre[key])
reused=json.loads((HERE/'EXACT-REUSED-PROVIDERS.json').read_text())
for key in ['banked_state','banked_storage','banked_nominal_ArchVdso']:
 entry=reused[key];verify(entry['original']);verify(entry['private_copy']);assert entry['original']['sha256']==entry['private_copy']['sha256']
c=(HERE/'BASE.syscall.c').read_text();candidate=(HERE/'candidate.syscall.c').read_text();original=(HERE/'original-vdso-map-log.c.inc').read_text()
assert c.count(original)==1and candidate.count(original)==1and (HERE/'oracle.c').read_text().count(original)==1
assert '#else\n#line 3077\n'+original+'#endif\n#line 3104\n'in candidate
assert candidate.count('MCKERNEL_RUST_F06_VDSO_MAP_LOG')==1
for name in ['syscall.c','lib.rs','CMakeLists.txt']:
 relative={'syscall.c':'arch/x86_64/kernel/syscall.c','lib.rs':'kernel/rust/lib.rs','CMakeLists.txt':'kernel/CMakeLists.txt'}[name]
 assert bind(HERE/('candidate.'+name))['sha256']==pre['snapshots'][relative]['proposed_postimage_sha256']
assert (HERE/'candidate.lib.rs').read_text().count('mod f06_vdso_map_log;')==1
assert (HERE/'candidate.CMakeLists.txt').read_text().count('COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_VDSO_MAP_LOG"')==1
rust=(HERE/'f06_vdso_map_log.rs').read_text();assert rust.count('pub static mut')==1and 'line_flags:3084'in rust
assert rust.count('arch_vdso_state_bridge(null_mut(),null_mut(),addr_of_mut!(offset_address))')==1
assert 'read(offset_address) as CULong'in rust and 'read(addr_of!((*process).pid))'in rust
assert 'if vm.is_null(){-1}'in rust and 'if process.is_null(){-1}'in rust
assert rust.count('#[no_mangle]')==1and 'fn arch_vdso_map_log_bridge('in rust
assert 'fn arch_vdso_map_log_bridge('in(HERE/'original-Rust-log-declaration.rs.inc').read_text()
assert 'ARCH_VDSO_MAP_LOG_MAPPED'in(HERE/'original-Rust-map-caller.rs.inc').read_text()
header=(ROOT/'lib/include/ihk/debug.h').read_text();assert '#define DDEBUG_DEFAULT DDEBUG_NONE'in header and '#define DDEBUG_NONE  0x0'in header
identity=json.loads((HERE/'ORIGINAL-DESCRIPTOR-IDENTITY.json').read_text());assert identity['accepted_registry_count']==389and identity['selected_record']['line']==3084
assert identity['canonical118_site_drift_preexisting']==2
plan=json.loads((HERE/'FUTURE-HOST-COMMANDS.json').read_text());assert len(plan['commands'])==4
assert '-save-temps'in plan['commands'][1]['argv']and '-save-temps=obj'not in plan['commands'][1]['argv']
assert all(x['purpose'].startswith(SCOPE)for x in plan['commands'])
assert plan['environment']['MCKERNEL_F06_RT_SIGRETURN_ORIGIN']=='/src/arch/x86_64/kernel/syscall.c'
assert not Path(plan['fresh_output']).exists()
result={'scope':SCOPE,'status':'PASS','exact_canonical118_preimages':True,'unchanged_original_C_text_and_Rust_caller':True,'unchanged_banked_Rust_state_storage_providers':True,'original_PID_offset_and_variadic_domain_preserved':True,'inherited3084_descriptor_identity_preserved':True,'preexisting_canonical118_metadata_drift_explicit':True,'new_C_implementation':False,'fixed_new_commands':4,'no_shared_writes':True,'compiler_runs':0,'fixture_runs':0,'default_native_data_file_credit':0}
(HERE/'SOURCE-CHECK.RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
