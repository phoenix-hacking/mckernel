"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read produced artifacts only after separately granted compilation/runtime commands.
"""
from pathlib import Path
import subprocess,json,hashlib
p=Path(__file__).resolve().parent
d=json.loads((p/'EXACT-LOOKUP-RECIPE.NOT-GRANTED.json').read_text());out=Path(d['output_root'])
for r in d['reused_lock_inputs']:
    assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
def nm(file):return subprocess.check_output(['/usr/bin/nm','-g',str(file)],text=True)
r=nm(out/'lookup-Rust.o');c=nm(out/'original-C.o');h=nm(out/'compare-C.o')
assert ' T arch_process_vm_rw_lookup_range_bridge\n' in r
assert ' T arch_process_vm_rw_lookup_range_bridge\n' not in c
assert ' U lookup_process_memory_range\n' in c
assert ' U arch_process_vm_rw_lookup_range_bridge\n' in h
for s in ['arch_process_vm_rw_read_lock_bridge','arch_process_vm_rw_read_unlock_bridge']:
    assert ' T '+s+'\n' not in r
    assert ' U '+s+'\n' in h
assert ' U process_range_public_log_bridge\n' in r
print('PASS lookup_ELF Rust_provider=1 original_C_static=1 typed_C_import=1 reused_lock_providers=2 unchanged_objects=1 log_event_ABI=1')
