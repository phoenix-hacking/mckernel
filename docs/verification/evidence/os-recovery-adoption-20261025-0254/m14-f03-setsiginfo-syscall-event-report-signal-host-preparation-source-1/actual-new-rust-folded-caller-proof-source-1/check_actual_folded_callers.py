"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite read-only byte/relocation check of exact already-passed HOST objects only.
"""
from pathlib import Path
import hashlib,importlib.util,json
D=Path(__file__).resolve().parent
proof=json.loads((D/'ACTUAL-FOLDED-CALLER-PROOF.json').read_text())
helper=D.parent.parent/'f02-source38-next-current-integration-source-1/check_thirteen_storage.py'
spec=importlib.util.spec_from_file_location('existing_elf_exact_caller_check',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for reference in list(proof['artifacts'].values())+[proof['exact_source'],proof['selected_compile_command'],proof['accepted_HOST_ABI_review'],proof['accepted_ELF_facts']]:
 raw=Path(reference['path']).read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256']
r=module.Elf(proof['artifacts']['rust-selected.o']['path']);j=module.Elf(proof['artifacts']['selected-joint.o']['path']);c=module.Elf(proof['artifacts']['selected.o']['path'])
def code(e,name):
 defs=e.definitions(name);assert len(defs)==1;d=defs[0];s=e.sections[d['ndx']];a=s['off']+d['value']-s['addr'];return e.data[a:a+d['size']]
for name,row in proof['selected_functions'].items():
 actual=code(r,name);assert actual.hex()==row['body_hex'] and actual==code(j,name)
event=code(r,'ptrace_syscall_event');signal=code(r,'f03_exec_report_signal_v1');syscall=code(r,'syscall');ex=code(r,'f03_execveat_ptrace_report_v1')
assert len(event)==47 and signal.hex()=='554889e548b800000000000000005dffe0'
assert not r.allocated_references('ptrace_syscall_event') and not r.allocated_references('f03_exec_report_signal_v1')
for row in proof['folded_public_event_sites']:
 load=row['ptrace_load_flag_test_offset'];select=row['signal_selection_and_provider_load_offset'];call=row['call_offset'];null=row['thread_null_check_offset']
 assert syscall[load:load+12]==event[9:0x15]
 assert syscall[select:select+19]==event[0x19:0x2c]
 assert syscall[call:call+2]==bytes.fromhex('ffd0')
 assert syscall[null:null+5]==bytes.fromhex('4885ff7427')
 assert row['provider_relocation'] in r.allocated_references('ptrace_report_signal')
assert syscall[0x3fd:0x408].hex()=='49c78288000000daffffff'
assert syscall[0x434:0x43b].hex()=='498b8288000000'
assert syscall[0x959:0x960].hex()=='4d89a988000000'
assert syscall[0x98c:0x993].hex()=='4d8ba988000000'
assert ex[0x28:0x2b].hex()=='4889fb' and ex[0x100:0x10a].hex()=='4889dfbe05040000ffd0'
assert ex[0x286:0x299]==event[0x19:0x2c] and ex[0x299:0x29e].hex()=='4889dfffd0'
for row in proof['existing_exec_signal_caller']['provider_relocations']:assert row in r.allocated_references('ptrace_report_signal')
edge=proof['existing_exec_signal_caller']['actual_selected_C_caller'];assert edge['relocation'] in c.allocated_references('f03_execveat_ptrace_report_v1')
fn=edge['function'];assert fn in c.definitions('do_execveat')
body=code(c,'do_execveat');assert body[0x2bd5-fn['value']:0x2bee-fn['value']].hex()=='488bb560feffff4c89f748b800000000000000004c01f8ffd0'
argv=json.loads(Path(proof['selected_compile_command']['path']).read_text())['argv']
for cfg in ['f03_ptrace_entry_candidate','f03_syscall_entry_candidate']:assert any(argv[i:i+2]==['--cfg',cfg] for i in range(len(argv)-1))
print(json.dumps(dict(status='PASS_EXACT_NEW_SELECTED_OBJECT_CALLER_FOLDING',syscall_fold_sites=2,real_exec_caller=True,selected_joint_bytes_equal=True,compiler_runtime_query_calls=0,production_final_image_native='OPEN')))
