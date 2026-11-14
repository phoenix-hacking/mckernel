"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Replace selected candidate C data tables with Rust-owned typed data; private only.
"""
from pathlib import Path
import difflib
D=Path(__file__).resolve().parent;P=D/'postimage';C=P/'kernel/syscall.c';R=P/'kernel/rust/syscall_policy.rs';oldc=(D/'pre-metadata/kernel/syscall.c').read_text();oldr=(D/'pre-metadata/kernel/rust/syscall_policy.rs').read_text()
start=oldc.index('const unsigned long f03_do_syscall_constants_v1[5] = {');end=oldc.index('#undef F03_DO_LINE_OFFSET',start)
do_c='''/* Rust owns the selected binding values and verbose records. These are
 * compile-time checks only; the unselected C implementation is unchanged. */
extern const unsigned long f03_do_syscall_constants_v1[5];
extern struct ddebug f03_do_syscall_debug_v1[6];
_Static_assert(__NR_exit_group == 231 && __NR_sched_setaffinity == 203 && IHK_SCD_REQ_THREAD_SPINNING == 0 && IHK_OS_MONITOR_KERNEL_OFFLOAD == 5 && PROFILE_SYSCALL_MAX == 2000 && DDEBUG_DEFAULT == 0, "F03 selected do_syscall constants");
'''
newc=oldc[:start]+do_c+oldc[end:];start=newc.index('const struct f03_util_thread_layout f03_util_thread_layout_v1 = {');end=newc.index('extern int util_thread(struct uti_attr *);',start)
util_c='''/* Rust owns the selected layout, constants, origins, descriptor pointer and
 * verbose records. These compare the real selected C headers to that profile. */
_Static_assert(sizeof(struct uti_ctx)==4096 && __alignof__(struct uti_ctx)==4 && __builtin_offsetof(struct uti_ctx,ctx)==0 && __builtin_offsetof(struct uti_ctx,uti_refill_tid)==0, "F03 uti context ABI");
_Static_assert(sizeof(struct uti_info)==160 && __alignof__(struct uti_info)==8 && __builtin_offsetof(struct uti_info,thread_va)==0 && __builtin_offsetof(struct uti_info,uti_futex_resp_pa)==24 && __builtin_offsetof(struct uti_info,ikc2linux_pa)==32 && __builtin_offsetof(struct uti_info,tid)==40 && __builtin_offsetof(struct uti_info,cpu)==44, "F03 uti info ABI 1");
_Static_assert(__builtin_offsetof(struct uti_info,status_pa)==88 && __builtin_offsetof(struct uti_info,spin_sleep_lock_pa)==96 && __builtin_offsetof(struct uti_info,spin_sleep_pa)==104 && __builtin_offsetof(struct uti_info,vm_pa)==112 && __builtin_offsetof(struct uti_info,futex_q_pa)==120 && __builtin_offsetof(struct uti_info,mc_idle_halt)==128 && __builtin_offsetof(struct uti_info,futex_queue_pa)==152, "F03 uti info ABI 2");
_Static_assert(IHK_MC_AP_NOWAIT==2 && __NR_sched_setaffinity==203 && UTI_STATE_PROLOGUE==1 && UTI_STATE_RUNNING_IN_LINUX==2 && UTI_STATE_EPILOGUE==3 && DDEBUG_DEFAULT==0, "F03 selected util constants");
'''
# Retain the struct definitions as C type declarations for ABI probes; only
# remove actual objects. The original Origins type was interspersed with data.
util_c+='struct f03_util_thread_origins { const char *file; int context_alloc,info_alloc,context_free,info_free,context_out,info_out; };\nextern const struct f03_util_thread_layout f03_util_thread_layout_v1;\nextern const unsigned long f03_util_thread_constants_v1[5];\nextern const struct f03_util_thread_origins f03_util_thread_origins_v1;\nextern unsigned long *const f03_util_thread_descriptor_slot_v1;\nextern struct ddebug f03_util_thread_debug_v1[4];\n'
newc=newc[:start]+util_c+newc[end:]
assert oldr.count('        static f03_do_syscall_constants_v1: [CULong; 5];')==1;newr=oldr.replace('        static f03_do_syscall_constants_v1: [CULong; 5];\n        static mut f03_do_syscall_debug_v1: [Ddebug; 6];\n','',1)
do_r='''    // Rust-owned data, fixed to the original selected x86 profile. C static
    // assertions verify the same source constants before the real build.
    #[no_mangle]
    pub static f03_do_syscall_constants_v1: [CULong; 5] = [231, 203, 0, 5, 2000];
    #[cfg(f03_dispatch_context_candidate)]
    const F03_DO_LINE_OFFSET: u32 = 23;
    #[cfg(not(f03_dispatch_context_candidate))]
    const F03_DO_LINE_OFFSET: u32 = 16;
    macro_rules! f03_do_record {
        ($line:expr) => { Ddebug { file: c"/src/kernel/syscall.c".as_ptr(),
            func: c"do_syscall".as_ptr(), fmt: core::ptr::null(),
            line_flags: $line - F03_DO_LINE_OFFSET } };
    }
    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    pub static mut f03_do_syscall_debug_v1: [Ddebug; 6] = [
        f03_do_record!(4155), f03_do_record!(4189), f03_do_record!(4197),
        f03_do_record!(4369), f03_do_record!(4416), f03_do_record!(4428),
    ];

'''
marker='    static RETURN_LOG_STATE: AtomicU64 = AtomicU64::new((u32::MAX as u64) << 32);';assert newr.count(marker)==1;newr=newr.replace(marker,do_r+marker,1)
for line in ('        static f03_util_thread_layout_v1: Layout;\n','        static f03_util_thread_constants_v1: [CULong; 5];\n','        static f03_util_thread_origins_v1: Origins;\n','        static f03_util_thread_descriptor_slot_v1: *const CULong;\n','        static mut f03_util_thread_debug_v1: [crate::debug::Ddebug; 4];\n'):
 assert newr.count(line)==1;newr=newr.replace(line,'',1)
marker='''    unsafe extern "C" {
        static mut idle_halt: CInt;''';assert newr.count(marker)==1
util_r='''    // Exact selected source6153/executer uti.h layout; physical publication
    // remains partial and no reference to uninitialized UtiInfo is created.
    #[repr(C)]
    struct UtiInfoLayout {
        thread_va: CULong, uti_futex_resp: *mut c_void, ikc2linux: *mut c_void,
        uti_futex_resp_pa: CULong, ikc2linux_pa: CULong, tid: CInt, cpu: CInt,
        status: *mut c_void, spin_sleep_lock: *mut c_void, spin_sleep: *mut c_void,
        vm: *mut c_void, futex_q: *mut c_void, status_pa: CULong,
        spin_sleep_lock_pa: CULong, spin_sleep_pa: CULong, vm_pa: CULong,
        futex_q_pa: CULong, mc_idle_halt: CInt, futex_queue: *mut c_void,
        os: *mut c_void, futex_queue_pa: CULong,
    }
    const _: () = {
        assert!(size_of::<UtiInfoLayout>() == 160 && align_of::<UtiInfoLayout>() == 8);
        assert!(size_of::<UtiCtx>() == 4096 && align_of::<UtiCtx>() == 4);
    };
    #[no_mangle]
    pub static f03_util_thread_layout_v1: Layout = Layout {
        context_size: size_of::<UtiCtx>(), info_size: size_of::<UtiInfoLayout>(),
        context: offset_of!(UtiCtx, ctx), refill_tid: offset_of!(UtiCtx, refill),
        info_thread_va: offset_of!(UtiInfoLayout, thread_va),
        info_response_pa: offset_of!(UtiInfoLayout, uti_futex_resp_pa),
        info_channel_pa: offset_of!(UtiInfoLayout, ikc2linux_pa),
        info_tid: offset_of!(UtiInfoLayout, tid), info_cpu: offset_of!(UtiInfoLayout, cpu),
        info_status_pa: offset_of!(UtiInfoLayout, status_pa),
        info_sleep_lock_pa: offset_of!(UtiInfoLayout, spin_sleep_lock_pa),
        info_sleep_pa: offset_of!(UtiInfoLayout, spin_sleep_pa),
        info_vm_pa: offset_of!(UtiInfoLayout, vm_pa),
        info_futex_q_pa: offset_of!(UtiInfoLayout, futex_q_pa),
        info_idle_halt: offset_of!(UtiInfoLayout, mc_idle_halt),
        info_futex_queue_pa: offset_of!(UtiInfoLayout, futex_queue_pa),
    };
    #[no_mangle]
    pub static f03_util_thread_constants_v1: [CULong; 5] = [2, 203, 1, 2, 3];
    // Immutable pointer names a static NUL-terminated source path; never mutated.
    unsafe impl Sync for Origins {}
    #[no_mangle]
    pub static f03_util_thread_origins_v1: Origins = Origins {
        file: c"/src/kernel/syscall.c".as_ptr(), context_alloc: 28314,
        info_alloc: 28323, context_free: 28369, info_free: 28372,
        context_out: 28395, info_out: 28396,
    };
    #[repr(transparent)]
    #[derive(Clone, Copy)]
    struct DescriptorSlot(*const CULong);
    // This static is an immutable pointer to the existing C-owned slot; access
    // to the pointed-to mutable value remains the original volatile load.
    unsafe impl Sync for DescriptorSlot {}
    #[no_mangle]
    pub static f03_util_thread_descriptor_slot_v1: DescriptorSlot =
        DescriptorSlot(core::ptr::addr_of!(uti_desc));
    macro_rules! f03_util_record {
        ($line:expr) => { crate::debug::Ddebug {
            file: c"/src/kernel/syscall.c".as_ptr(),
            func: c"util_thread".as_ptr(), fmt: core::ptr::null(), line_flags: $line,
        } };
    }
    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    pub static mut f03_util_thread_debug_v1: [crate::debug::Ddebug; 4] = [
        f03_util_record!(28359), f03_util_record!(28367),
        f03_util_record!(28377), f03_util_record!(28382),
    ];

'''
newr=newr.replace(marker,util_r+'''    unsafe extern "C" {
        static mut uti_desc: CULong;
        static mut idle_halt: CInt;''',1)
oldslot='let slot = read_volatile(addr_of!(f03_util_thread_descriptor_slot_v1));';assert newr.count(oldslot)==1;newr=newr.replace(oldslot,'let slot = read_volatile(addr_of!(f03_util_thread_descriptor_slot_v1)).0;',1)
C.write_text(newc);R.write_text(newr);diff=[]
for rel,a,b in [('kernel/syscall.c',oldc,newc),('kernel/rust/syscall_policy.rs',oldr,newr)]:diff.extend(difflib.unified_diff(a.splitlines(keepends=True),b.splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel))
(D/'RUST-OWNED-METADATA.ON-CALLER-SUCCESSOR.patch').write_text(''.join(diff));print('Rust-owned selected tables prepared, real-header assertions retained; no compile')
