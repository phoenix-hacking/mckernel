#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source generation and exact-byte checks only; never invokes a compiler.
"""
import difflib
import hashlib
import json
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
EVIDENCE = HERE.parent
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
POLICIES = {
    'CONVERGENCE.md': 'fe3e27a2255f410645deeb92fa4a912b0fe52d8705665e05a5953c42a1a2f145',
    'GOAL.md': '183b4fe6c7470d43e0e10bf840cfc5f1efd3aa2ae4a30dd69818f85af7f7c328',
    'HANDOFF.md': 'e92aa1cd2db4f23094fa536b445e17d1171507cac201b941eb3a8274ec8964a3',
    'START.md': '5e82e288f7059ad73e01f49956a16039040c3c448b098e4f45dc917cf4620341',
}

def ref(p):
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

def function(s, marker):
    assert s.count(marker) == 1, marker
    a = s.index(marker)
    e = s.index('{', a) + 1
    depth = 1
    while depth:
        depth += (s[e] == '{') - (s[e] == '}')
        e += 1
    return a, e, s[a:e] + '\n'

def symbols(path):
    b = path.read_bytes()
    assert b[:6] == b'\x7fELF\x02\x01'
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', b)
    sections = [struct.unpack_from('<IIQQQQIIQQ', b, h[6]+i*h[11]) for i in range(h[12])]
    result = []
    for section in sections:
        if section[1] != 2:
            continue
        names = sections[section[6]]
        names = b[names[4]:names[4]+names[5]]
        for offset in range(section[4], section[4]+section[5], section[9]):
            name, info, other, index, value, size = struct.unpack_from('<IBBHQQ', b, offset)
            if info & 15 == 2 and 0 < index < len(sections) and sections[index][2] & 2:
                result.append(dict(name=names[name:names.index(0, name)].decode(), bytes=size))
    return result

def main():
    cpath = ROOT/'kernel/syscall.c'
    rpath = ROOT/'kernel/rust/syscall_policy.rs'
    c, rust = cpath.read_text(), rpath.read_text()
    a, e, original = function(c, 'int do_munmap(void *addr, size_t len, int holding_memory_range_lock)')
    assert 'mod f03_do_munmap_entry_v1' not in rust
    startline, closeline = c[:a].count('\n')+1, c[:e].count('\n')+1
    anchor = ('#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n'
              '#line 4490\n#else\n#line 4499\n#endif')
    anchor_index = c[:a].rfind(anchor)
    assert anchor_index >= 0
    anchor_end = anchor_index+len(anchor)
    assert '#line' not in c[anchor_end:a]
    selected_offset = 4490-(c[:c.index('#line 4490', anchor_index)].count('\n')+1)-1
    fallback_offset = 4499-(c[:c.index('#line 4499', anchor_index)].count('\n')+1)-1
    binding = (HERE/'do-munmap-binding.C.inc').read_text()
    paired = ('#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n'+binding+
              '#else\n#line '+str(startline+fallback_offset)+'\n'+original+'#endif\n'+
              '#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n'+
              '#line '+str(closeline+selected_offset-3)+'\n#else\n#line '+str(closeline+fallback_offset-1)+'\n#endif\n')
    fragment = (HERE/'do-munmap-entry.Rust.inc').read_text()
    # Independently calculate the successor source line for each dispatch state.
    # No preprocessor or compiler runs: only the active final #line arithmetic.
    next_marker = '#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nextern int f03_search_free_space_v1'
    original_next = c[:c.index(next_marker, e)].count('\n')+1
    candidate_c = c[:a]+paired+c[e:]
    candidate_next = candidate_c[:candidate_c.index(next_marker, a)].count('\n')+1
    line_checks = []
    for selected, offset, reset in [(True, selected_offset, closeline+selected_offset-3),
                                     (False, fallback_offset, closeline+fallback_offset-1)]:
        reset_text = '#line '+str(reset)+'\n'
        reset_at = candidate_c.index(reset_text, a)
        reset_physical = candidate_c[:reset_at].count('\n')+1
        observed_next = reset+candidate_next-reset_physical-1
        expected_next = original_next+offset
        assert observed_next == expected_next
        line_checks.append(dict(dispatch_selected=selected,expected_next=expected_next,observed_next=observed_next))
    (HERE/'do-munmap-original.C.inc').write_text(original)
    (HERE/'do-munmap-paired.C.inc').write_text(paired)
    for path, before, after in [('kernel/syscall.c', c, c[:a]+paired+c[e:]),
                                ('kernel/rust/syscall_policy.rs', rust, rust+'\n'+fragment)]:
        (HERE/(Path(path).name+'.patch')).write_text(''.join(difflib.unified_diff(
            before.splitlines(True), after.splitlines(True), fromfile='a/'+path, tofile='b/'+path)))

    _, _, body = function(rust, '#[no_mangle]\npub unsafe extern "C" fn do_munmap_body_result(')
    (HERE/'do-munmap-body.current.Rust.inc').write_text(body)
    _, _, cbody = function(c, 'do_munmap_body_result(void *vm, void *proc, unsigned long addr, size_t len,\n\t\tint holding_memory_range_lock,')
    (HERE/'do-munmap-body.original.C.inc').write_text(cbody)
    _, _, offset_body = function(c, 'static inline void *syscall_offset_ptr(void *base, size_t offset)')
    (HERE/'syscall-offset-ptr.original.C.inc').write_text(offset_body)
    types_start = c.index('typedef void (*do_munmap_void_fn_t)(void);')
    types_end = c.index('typedef int (*do_mmap_smaller_page_fn_t)', types_start)
    host_start = c.index('typedef int (*mprotect_set_host_vma_fn_t)')
    host_end = c.index('typedef int (*remap_file_pages_callable_fn_t)', host_start)
    (HERE/'do-munmap-types.C.inc').write_text(c[types_start:types_end]+c[host_start:host_end])
    rust_types = '\n'.join(line for line in rust.splitlines()
                           if line.startswith(('type DoMunmap', 'type MprotectSetHostVmaFn')))+'\n'
    constants = '\n'.join(line for line in rust.splitlines()
                          if line.startswith(('const EINVAL:', 'const PROT_READ:', 'const PROT_WRITE:', 'const PROT_EXEC:')))+'\n'
    (HERE/'do-munmap-types.current.Rust.inc').write_text(rust_types+constants)
    (HERE/'abi.current.rs').write_bytes((ROOT/'kernel/rust/abi.rs').read_bytes())
    witness = '''
    #[no_mangle]
    pub static F03_DO_MUNMAP_ABI:[CULong;27]=[
        core::mem::size_of::<crate::abi::Thread>() as _,core::mem::align_of::<crate::abi::Thread>() as _,
        core::mem::size_of::<crate::abi::ProcessVm>() as _,core::mem::align_of::<crate::abi::ProcessVm>() as _,
        core::mem::size_of::<Process>() as _,core::mem::align_of::<Process>() as _,
        core::mem::size_of::<crate::abi::CpuLocalVar>() as _,core::mem::align_of::<crate::abi::CpuLocalVar>() as _,
        offset_of!(crate::abi::CpuLocalVar,current) as _,offset_of!(crate::abi::Thread,vm) as _,
        offset_of!(crate::abi::Thread,proc) as _,offset_of!(Process,straight_va) as _,offset_of!(Process,straight_len) as _,
        core::mem::size_of::<DoMunmapBinding>() as _,core::mem::align_of::<DoMunmapBinding>() as _,
        offset_of!(DoMunmapBinding,begin) as _,offset_of!(DoMunmapBinding,remove_range) as _,
        offset_of!(DoMunmapBinding,clear_host) as _,offset_of!(DoMunmapBinding,set_host) as _,
        offset_of!(DoMunmapBinding,finish) as _,offset_of!(DoMunmapBinding,log) as _,
        core::mem::size_of::<CInt>() as _,core::mem::size_of::<crate::abi::CLong>() as _,
        core::mem::size_of::<SizeT>() as _,core::mem::size_of::<DoMunmapClearHostFn>() as _,
        core::mem::size_of::<DoMunmapRemoveRangeFn>() as _,(super::PROT_READ|super::PROT_WRITE|super::PROT_EXEC) as _,
    ];
'''
    (HERE/'do-munmap-entry.fixture.Rust.inc').write_text(fragment.rstrip()[:-1]+witness+'}\n')
    (HERE/'lib.fixture.rs').write_text('''#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod cls {
    unsafe extern "C" { pub fn get_this_cpu_local_var()->*mut crate::abi::CpuLocalVar; }
}
mod policy {
    use crate::abi::{CInt,CLong,CULong,SizeT};
    use core::ffi::c_void;
    include!("do-munmap-types.current.Rust.inc");
    unsafe fn field_ptr<T>(base:*mut u8,offset:SizeT)->*mut T { unsafe { base.add(offset).cast() } }
    include!("do-munmap-body.current.Rust.inc");
    include!("do-munmap-entry.fixture.Rust.inc");
}
''')
    oldbase = EVIDENCE/'m14-f03-next-runtime-body2-source-20261028-1'
    old = json.loads((oldbase/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').read_text())
    commands = old['commands']
    for row in commands:
        row['argv'] = [x.replace(str(oldbase), str(HERE)) for x in row['argv']]
        row['purpose'] = SCOPE+' HOST mock unmap/range/host callbacks only; no actual MM, syscall, Docker, root, guest, hardware or control action.'
    commands[0]['label'] = '00-existing-unmap-body-new-entry-Rust-object'
    commands[0]['argv'][commands[0]['argv'].index('f03_clear_host_pte_entry')] = 'f03_do_munmap_entry'
    commands[1]['argv'] = [x.replace('clear-host-pte-driver.c', 'driver.c') for x in commands[1]['argv']]
    commands[1]['label'] = '01-genuine-header-verbatim-C-oracle-link'
    commands[2]['label'] = '02-do-munmap-functional-equivalence'
    plan = dict(scope=SCOPE, status='SOURCE_ONLY_NOT_GRANTED', commands=commands,
                expected_stdout='PASS do-munmap actual-header ABI27; 4860 C/Rust pairs; 9720 independent order/error/straight-map/full-state oracles',
                requires='Fresh exact Root ordinary source/header/tool binding and grant, disjoint new output root; no old grant/window/nonce revived.',
                limits=dict(CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90),executed=False)
    (HERE/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').write_text(json.dumps(plan, indent=2)+'\n')

    acceptance = EVIDENCE/'CURRENT116-ACCEPTED-ARTIFACT-AND-CURRENTFREE.json'
    accepted = json.loads(acceptance.read_text())['actual_new_default_artifact']['generic_C']
    object_path = Path(accepted['path'])
    assert ref(object_path) == accepted
    selected = symbols(object_path)
    assert len(selected) == 54
    assert [row for row in selected if row['name'] == 'do_munmap'] == [dict(name='do_munmap', bytes=168)]
    inputs = [cpath,rpath,ROOT/'kernel/rust/abi.rs',ROOT/'kernel/include/process.h',
              ROOT/'kernel/include/cls.h',ROOT/'kernel/include/syscall.h',ROOT/'kernel/include/mman.h',
              ROOT/'kernel/rust/tests/do_munmap_host_clear_actual_harness.py',
              oldbase/'SETRESUID-HOLD.json']
    report = dict(scope=SCOPE,status='PRIVATE_DO_MUNMAP_SOURCE_READY_NOT_COMPILED',
                  owner='/root/f03_next',target='do_munmap',selected_current116_C_bytes=168,
                  accepted_current116=ref(acceptance),selected_current116_generic_C=accepted,
                  selected_generic_C_functions=54,selected_target=dict(name='do_munmap',bytes=168),
                  preimages=[ref(p) for p in inputs],existing_Rust_body_reused='do_munmap_body_result',
                  c_oracle='Verbatim current C wrapper AND complete retained C body; independent callback/state oracle per invocation.',
                  scope_exclusions=['banked117 perf_mmap','banked118 clear_host_pte','SETRESUID-HOLD and all credentials',
                                    'service-held/excluded request/endpoint/signal work'],
                  policy_hashes_adopted=POLICIES,
                  line_state=dict(start_physical=startline,close_physical=closeline,
                                  selected_offset=selected_offset,fallback_offset=fallback_offset,
                                  successor_line_checks=line_checks),
                  preserved_callbacks=['do_munmap_begin_bridge','do_munmap_remove_range_bridge','do_munmap_clear_host_bridge',
                                       'do_munmap_set_host_bridge','do_munmap_finish_bridge','do_munmap_log_bridge'],
                  explicit_C_debt=['do_munmap_clear_host_bridge','do_munmap_set_host_bridge','do_munmap_log_bridge',
                                   'their unchanged downstream host forwarding/request providers and holds'],
                  predicted_C_function_removal=1,actual_builds=0,actual_fixture_runs=0,actual_native=0,
                  canonical_writes=0,whole_file_retirement=False,
                  earliest_deadline=dict(UTC_epoch=1793253600,MONO=1035704.5689393478,BOOT=1051043.6959931096,
                                         boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'),
                  credit_run='7f4af94a83b14cc08f97401f5891d965',ceiling=57774.852125,spent_floor=22812.3311)
    assert cpath.read_text() == c and rpath.read_text() == rust, 'Source changed during preparation; regenerate from coherent new preimages.'
    report['files'] = [ref(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ('SOURCE-READY.json','SOURCE-CHECKS.json')]
    (HERE/'SOURCE-READY.json').write_text(json.dumps(report,indent=2)+'\n')
    checks = dict(scope=SCOPE,status='PASS_SOURCE_GENERATION_EXACT_C_AND_RUST_BYTES_ONLY',
                  selected_target_verified=True,complete_existing_Rust_body_byte_exact=True,
                  complete_C_oracle_byte_exact=True,original_wrapper_byte_exact=True,
                  source_ready=ref(HERE/'SOURCE-READY.json'),
                  note='No compiler, fixture, MM, syscall, Docker, root, hardware or native process was invoked.')
    (HERE/'SOURCE-CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(checks))

if __name__ == '__main__':
    main()
