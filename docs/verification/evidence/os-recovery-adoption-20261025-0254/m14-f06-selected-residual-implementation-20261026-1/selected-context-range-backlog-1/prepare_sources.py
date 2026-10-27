"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite four selected existing-port bridge compositions; no compiler or canonical writes.
"""
import difflib
import hashlib
import json
from pathlib import Path
import struct

D=Path(__file__).resolve().parent
P=D.parent
ROOT=Path('/home/holden/mckernel')
LANE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall')
PTR=LANE/'next-ptrace-runtime-callbacks-source-1/candidate/syscall_policy.ptrace_runtime_callbacks.FRAGMENT.rs'
VDSO=LANE/'next-vdso-state-range-transaction-source-1/candidate/syscall_policy.vdso_state_range.FRAGMENT.rs'
FRONTIER=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/chat-thirty-minute-oversight-1/M14-SELECTED-OBJECT-FRONTIER.json')
SPECS=[
 dict(name='ptrace-context',symbol='arch_ptrace_lookup_user_context_bridge',begin='\nvoid *\narch_ptrace_lookup_user_context_bridge(',end='\nvoid *\narch_ptrace_alloc_bridge(',C='MCKERNEL_RUST_F06_PTRACE_CONTEXT',Rust='f06_ptrace_context_candidate',leaf='f06_ptrace_context.rs',old=PTR,provider='kernel/rust/x86_cpu_helpers.rs'),
 dict(name='ptrace-alloc',symbol='arch_ptrace_alloc_bridge',begin='\nvoid *\narch_ptrace_alloc_bridge(',end='\nunsigned long\narch_ptrace_find_thread_bridge(',C='MCKERNEL_RUST_F06_PTRACE_ALLOC',Rust='f06_ptrace_alloc_candidate',leaf='f06_ptrace_alloc.rs',old=PTR,provider='kernel/rust/mem_helpers.rs'),
 dict(name='vdso-add-range',symbol='arch_vdso_add_range_bridge',begin='\nint\narch_vdso_add_range_bridge(',end='\nint\narch_vdso_set_range_bridge(',C='MCKERNEL_RUST_F06_VDSO_ADD_RANGE',Rust='f06_vdso_add_range_candidate',leaf='f06_vdso_add_range.rs',old=VDSO,provider='kernel/rust/process_helpers.rs'),
 dict(name='vdso-set-range',symbol='arch_vdso_set_range_bridge',begin='\nint\narch_vdso_set_range_bridge(',end='\nvoid\narch_vdso_map_log_bridge(',C='MCKERNEL_RUST_F06_VDSO_SET_RANGE',Rust='f06_vdso_set_range_candidate',leaf='f06_vdso_set_range.rs',old=VDSO,provider='kernel/rust/x86_memory_helpers.rs'),
]


def ref(path):
    raw=path.read_bytes()
    return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def exact_symbols(path):
    raw=path.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01'
    start=struct.unpack_from('<Q',raw,40)[0];width,count=struct.unpack_from('<HH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,start+i*width) for i in range(count)]
    wanted={x['symbol'] for x in SPECS};found={}
    for table in sections:
        if table[1]!=2:continue
        strings=sections[table[6]];names=raw[strings[4]:strings[4]+strings[5]]
        for offset in range(table[4],table[4]+table[5],table[9]):
            name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,offset)
            symbol=names[name:names.find(b'\0',name)].decode()
            if symbol in wanted:
                assert symbol not in found
                found[symbol]=dict(symbol=symbol,binding=info>>4,type=info&15,size=size,section_index=index,section_flags=sections[index][2])
    assert set(found)==wanted
    assert all(x['binding']==1 and x['type']==2 and x['size']>0 and x['section_flags']&2 for x in found.values())
    return found


def compose(spec,c,rust,old):
    assert c.count(spec['begin'])==1
    left=c.index(spec['begin']);right=c.index(spec['end'],left)
    original=c[left:right];wrapped='\n#ifndef '+spec['C']+original+'\n#endif\n'
    fn=old.index('pub unsafe extern "C" fn '+spec['symbol']+'(')
    left=old.rfind('/// # Safety',0,fn)
    try:right=old.index('\n/// # Safety',fn)
    except ValueError:right=len(old)
    reused=old[left:right]
    declaration=''
    if spec['name']=='ptrace-context':
        imports='use core::ffi::c_void;\n\nuse crate::abi::{Thread, X86UserContext};\n\n'
        left=old.index('    #[link_name = "lookup_user_context"]');right=old.index('\n}',left)
        declaration='unsafe extern "C" {\n'+old[left:right]+'\n}\n\n'
    elif spec['name']=='ptrace-alloc':imports='use core::ffi::c_void;\n\nuse crate::abi::{CInt, CULong, SizeT};\n\n'
    elif spec['name']=='vdso-add-range':imports='use core::ptr::null_mut;\n\nuse crate::abi::{CInt, CULong, ProcessVm, VmRange};\n\nuse super::PAGE_SHIFT;\n\n'
    else:
        imports='use core::ffi::c_void;\n\nuse crate::abi::{CInt, CULong, ProcessVm, VmRange};\n\n'
        left=old.index('    #[link_name = "ihk_mc_pt_set_range"]');right=old.index('\n}',left)
        declaration='unsafe extern "C" {\n'+old[left:right]+'\n}\n\n'
    module='// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n// Exact existing adapter; current-stack/allocation/VM ownership remains with provider.\n'+imports+declaration+reused
    selection='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg('+spec['Rust']+')]\n#[path = "'+spec['leaf']+'"]\nmod '+spec['leaf'].removesuffix('.rs')+';\n'
    assert 'mod '+spec['leaf'].removesuffix('.rs')+';' not in rust
    return c[:c.index(spec['begin'])]+wrapped+c[c.index(spec['end'],c.index(spec['begin'])):],rust+selection,module,original,wrapped,selection,reused


def main():
    cpath=ROOT/'arch/x86_64/kernel/syscall.c';rpath=ROOT/'kernel/rust/syscall_policy.rs'
    c,rust=cpath.read_text(),rpath.read_text()
    frontier=json.loads(FRONTIER.read_text());obj=Path(next(x for x in frontier['rows'] if x['id']=='M14-F06')['object']);symbols=exact_symbols(obj)
    for spec in SPECS:
        out=D/spec['name'];out.mkdir()
        selected_c,selected_r,module,original,wrapped,selection,reused=compose(spec,c,rust,spec['old'].read_text())
        for name,text in [('syscall.c',selected_c),('syscall_policy.rs',selected_r),(spec['leaf'],module),('original_bridge.inc',original),('genuine_prologue.inc',c.split('\nvoid terminate_mcexec(int, int);',1)[0]+'\n')]:
            (out/name).write_text(text)
        for label,before,after,target in [('syscall.c.diff',c,selected_c,'arch/x86_64/kernel/syscall.c'),('syscall_policy.rs.diff',rust,selected_r,'kernel/rust/syscall_policy.rs')]:
            (out/label).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=target,tofile=target)))
        (out/'SELECTED-SYMBOL.json').write_text(json.dumps(dict(scope='Functional OS only; no security testing. Exact four-target lookup, not inventory.',object=ref(obj),frontier=ref(FRONTIER),selected_symbol=symbols[spec['symbol']]),indent=2)+'\n')
        serial_spec={key:(str(value) if isinstance(value,Path) else value) for key,value in spec.items()}
        headers=['kernel/include/process.h','kernel/include/kmalloc.h','lib/include/ihk/mm.h','arch/x86_64/kernel/include/ihk/types.h']
        (out/'SOURCE-BINDINGS.json').write_text(json.dumps(dict(scope=__doc__,spec=serial_spec,before=[ref(cpath),ref(rpath)],old_fragment=ref(spec['old']),existing_provider=ref(ROOT/spec['provider']),selected_proof=ref(out/'SELECTED-SYMBOL.json'),genuine_headers=[ref(ROOT/name) for name in headers],after=[ref(out/name) for name in ['syscall.c','syscall_policy.rs',spec['leaf'],'original_bridge.inc','genuine_prologue.inc']],compiler=None,native=None),indent=2)+'\n')


if __name__=='__main__':main()
