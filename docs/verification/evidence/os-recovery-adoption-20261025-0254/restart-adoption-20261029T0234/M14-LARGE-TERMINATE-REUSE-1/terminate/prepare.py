from pathlib import Path
import difflib
here=Path(__file__).resolve().parent
old=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-terminate-whole-orchestration-source-1/terminate_whole.RUST-FRAGMENT.rs.inc').read_text()
new=old
oldblock='''    #[repr(C)]
    struct Origins {
        file: *const i8,
        id_alloc_line: CInt,
        id_free_line: CInt,
        saved_command_free_line: CInt,
    }

    unsafe extern "C" {
        static f03_terminate_origins_v1: Origins;
        static f03_terminate_nowait_v1: CULong;
        static mut f03_terminate_debug_v1: [Ddebug; 3];
'''
newblock='''    // The Rust-owned metadata below is limited to the reviewed /src source
    // profile. The compiler's selected __FILE__/__LINE__ must be verified before
    // the candidate can be enabled; these source facts are not runtime proof.
    const SOURCE_FILE: &[u8] = b"/src/kernel/syscall.c\\0";
    const FUNCTION_NAME: &[u8] = b"terminate\\0";
    const NOWAIT: CULong = 0x000002;
    #[cfg(f03_terminate_origin_dispatch)]
    const ORIGIN_LINES: [CInt; 6] = [5271, 5292, 5511, 5346, 5363, 5403];
    #[cfg(not(f03_terminate_origin_dispatch))]
    const ORIGIN_LINES: [CInt; 6] = [5278, 5299, 5518, 5353, 5370, 5410];

    // Match the three original ddebug records and writable flag semantics.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    static mut f03_terminate_debug_v1: [Ddebug; 3] = [
        Ddebug { file: SOURCE_FILE.as_ptr().cast(), func: FUNCTION_NAME.as_ptr().cast(),
            fmt: core::ptr::null(), line_flags: ORIGIN_LINES[0] as u32 },
        Ddebug { file: SOURCE_FILE.as_ptr().cast(), func: FUNCTION_NAME.as_ptr().cast(),
            fmt: core::ptr::null(), line_flags: ORIGIN_LINES[1] as u32 },
        Ddebug { file: SOURCE_FILE.as_ptr().cast(), func: FUNCTION_NAME.as_ptr().cast(),
            fmt: core::ptr::null(), line_flags: ORIGIN_LINES[2] as u32 },
    ];

    unsafe extern "C" {
'''
assert new.count(oldblock)==1
new=new.replace(oldblock,newblock)
new=new.replace('            let origins = addr_of!(f03_terminate_origins_v1);\n','')
new=new.replace('count.wrapping_mul(size_of::<CInt>() as CInt), f03_terminate_nowait_v1,\n                    (*origins).file.cast_mut(), (*origins).id_alloc_line,','count.wrapping_mul(size_of::<CInt>() as CInt), NOWAIT,\n                    SOURCE_FILE.as_ptr().cast_mut().cast(), ORIGIN_LINES[3],')
new=new.replace('ids.cast(), (*origins).file.cast_mut(), (*origins).id_free_line,','ids.cast(), SOURCE_FILE.as_ptr().cast_mut().cast(), ORIGIN_LINES[4],')
new=new.replace('saved.cast(), (*origins).file.cast_mut(), (*origins).saved_command_free_line,','saved.cast(), SOURCE_FILE.as_ptr().cast_mut().cast(), ORIGIN_LINES[5],')
assert 'f03_terminate_origins_v1' not in new and 'f03_terminate_nowait_v1' not in new
new=new.replace('/// fallible reservation binder cannot be substituted without propagation.','''/// fallible reservation binder cannot be substituted without propagation.
    /// The original selected allocation domain also requires a nonnegative peer
    /// count for which `count * sizeof(int)` fits the allocator's C int size and
    /// matches the number of peer nodes under the held reader lock. No claim is
    /// made about C signed-overflow or implementation-defined narrowing cases.''')
(here/'terminate.CURRENT119-RUST-METADATA.PRIVATE.rs.inc').write_text(new)
(here/'RUST-METADATA-CORRECTION.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='retained/terminate_whole.RUST-FRAGMENT.rs.inc',tofile='private/terminate.CURRENT119-RUST-METADATA.PRIVATE.rs.inc')))
