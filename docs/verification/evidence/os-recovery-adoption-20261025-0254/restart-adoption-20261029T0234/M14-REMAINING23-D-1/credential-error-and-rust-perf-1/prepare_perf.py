#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private Rust-owned typed perf-entry binding successor, no runtime C data.
"""
import ast,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;PREV=P/'defined-callers-correction-1/perf-abi-correction-1';ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
assert ref(PREV/'PERF-ENTRY-ABI.ON-FIRST20.patch')['sha256']=='dde53ee3e6725943baf699ba02ceab16effccee20835580c865f7ed6abb1629e'
source=ast.parse((P/'prepare_perf_entry.py').read_text());tables={}
for n in source.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('values','funcs'):tables[n.targets[0].id]=ast.literal_eval(n.value)
values=tables['values'];funcs=tables['funcs'];assert len(values)==31 and len(funcs)==13
paths=['kernel/syscall.c','kernel/rust/f03_perf_entry_candidate.rs'];before={x:(PREV/'postimage'/x).read_text() for x in paths};after=dict(before)
c=before[paths[0]];marker='const struct f03_perf_entry_binding_v1_type f03_perf_entry_binding_v1 = {\n';start=c.index(marker);end=c.index('\n};',start)+3
c_old=c[start:end];assert c_old.count('\n')==45
new='extern const struct f03_perf_entry_binding_v1_type f03_perf_entry_binding_v1;\n_Static_assert(__builtin_offsetof(struct mckfd, sig_no) == 12, "mckfd sig_no slot ABI");'
after[paths[0]]=c[:start]+new+c[end:]
leaf=before[paths[1]]
leaf=leaf.replace('use crate::abi::{CInt, CLong, CULong, SyscallRequest, X86UserContext};','use crate::abi::{CInt, CLong, CULong, Mckfd, Process, Thread, SyscallRequest, X86UserContext};\nuse super::f03_sync_child_layout_v2::FullMcPerfEvent;')
old='unsafe extern "C" { static f03_perf_entry_binding_v1: PerfEntryBinding; }';assert leaf.count(old)==1
names={'copy_from':'syscall_copy_from_user_bridge','attr_freq':'f03_perf_attr_frequency_v1','event_alloc':'f03_perf_event_allocate_v1','counter_alloc':'f03_perf_counter_allocate_v1','syscall':'perf_event_open_do_syscall_bridge','allocate':'perf_event_alloc_kmalloc_bridge','read':'f03_perf_read_v1','ioctl':'f03_perf_ioctl_v1','mmap':'f03_perf_mmap_v1','close':'f03_perf_close_v1','fcntl':'f03_perf_fcntl_v1','lock':'syscall_mckfd_lock_bridge','unlock':'syscall_mckfd_unlock_bridge'}
prototypes={
'SyscallCopyFromUserFn':'fn {n}(dst: *mut u8, src: CULong, size: usize) -> CLong;',
'PerfAttrFreqFn':'fn {n}(attr: *const c_void) -> CInt;',
'PerfOpenAllocEventFn':'fn {n}(out: *mut *mut c_void, attr: *mut c_void) -> CInt;',
'PerfCounterAllocFn':'fn {n}(thread: *mut c_void, event: *mut c_void) -> CInt;',
'PerfOpenSyscallFn':'fn {n}(request: *mut SyscallRequest, cpu: CInt) -> CLong;',
'SyscallPolicyAllocFn':'fn {n}(size: usize, flags: CULong) -> *mut c_void;',
'SyscallMckfdLongFn':'fn {n}(fd: *mut c_void, ctx: *mut c_void) -> CLong;',
'SyscallMckfdIntFn':'fn {n}(fd: *mut c_void, ctx: *mut c_void) -> CInt;',
'SyscallMckfdLockFn':'fn {n}(lock: *mut c_void) -> CLong;',
'SyscallMckfdUnlockFn':'fn {n}(lock: *mut c_void, irq: CLong);'}
expr={'attr_size':'size_of::<PerfEventAttr>()','attr_type':'offset_of!(PerfEventAttr, type_)','attr_read_format':'offset_of!(PerfEventAttr, read_format)','attr_sample_period':'offset_of!(PerfEventAttr, sampling)','raw_type':'4','hardware_type':'0','cache_type':'3','unsupported_format':'7','sign_bit':'1u64 << 63','syscall_number':'298','mckfd_size':'size_of::<Mckfd>()','allocation_flags':'super::IHK_MC_AP_NOWAIT','event_pid':'offset_of!(FullMcPerfEvent, pid)','event_counter_id':'offset_of!(FullMcPerfEvent, counter_id)','proc_mckfd':'offset_of!(Process, mckfd)','mckfd_next':'offset_of!(Mckfd, next)','mckfd_fd':'offset_of!(Mckfd, fd)','mckfd_data':'offset_of!(Mckfd, data)','event_group_leader':'offset_of!(FullMcPerfEvent, group_leader)','event_sibling_list':'offset_of!(FullMcPerfEvent, sibling_list)','event_group_entry':'offset_of!(FullMcPerfEvent, group_entry)','event_nr_siblings':'offset_of!(FullMcPerfEvent, nr_siblings)','event_pmc_status':'offset_of!(FullMcPerfEvent, pmc_status)','thread_pmc_alloc_map':'offset_of!(Thread, pmc_alloc_map)','proc_mckfd_lock':'offset_of!(Process, mckfd_lock)','mckfd_sig_no':'offset_of!(Mckfd, padding)','mckfd_read_cb':'offset_of!(Mckfd, read_cb)','mckfd_ioctl_cb':'offset_of!(Mckfd, ioctl_cb)','mckfd_mmap_cb':'offset_of!(Mckfd, mmap_cb)','mckfd_close_cb':'offset_of!(Mckfd, close_cb)','mckfd_fcntl_cb':'offset_of!(Mckfd, fcntl_cb)'}
assert set(expr)=={k for k,v in values}
block='unsafe extern "C" {\n'+''.join('    '+prototypes[ty].format(n=names[name])+'\n' for name,symbol,ty in funcs)+'}\n'
block+='// Exact current selected Rust providers; paired C declaration carries no runtime data.\n#[no_mangle]\npub(super) static f03_perf_entry_binding_v1: PerfEntryBinding = PerfEntryBinding {\n'
block+=''.join('    '+name+': ('+expr[name]+') as CULong,\n' for name,_ in values)
block+=''.join('    '+name+': Some('+names[name]+'),\n' for name,_,_ in funcs)+'};'
leaf=leaf.replace(old,block)
sig_witness='    assert!(offset_of!(Mckfd, padding) == 12);\n'
assert leaf.count('    assert!(size_of::<PerfEntryBinding>() == 352 && align_of::<PerfEntryBinding>() == 8);\n')==1
leaf=leaf.replace('    assert!(size_of::<PerfEntryBinding>() == 352 && align_of::<PerfEntryBinding>() == 8);\n','    assert!(size_of::<PerfEntryBinding>() == 352 && align_of::<PerfEntryBinding>() == 8);\n'+sig_witness)
# No callback, stack storage, argument/return ordering is modified.
assert leaf.replace('use crate::abi::{CInt, CLong, CULong, Mckfd, Process, Thread, SyscallRequest, X86UserContext};\nuse super::f03_sync_child_layout_v2::FullMcPerfEvent;','use crate::abi::{CInt, CLong, CULong, SyscallRequest, X86UserContext};').replace(block,old).replace(sig_witness,'')==before[paths[1]]
after[paths[1]]=leaf
# C source declarations/static assertions remain; no C runtime array/object.
assert c[:start]+c_old+c[end:]==before[paths[0]], 'C predecessor reconstruction'
assert marker not in after[paths[0]], 'C runtime object still defined'
assert 'extern const struct f03_perf_entry_binding_v1_type f03_perf_entry_binding_v1;' in after[paths[0]]
assert '#[no_mangle]\npub(super) static f03_perf_entry_binding_v1' in leaf
# Actual source definitions and constants; unsupported source/profile remains open.
header=(ROOT/'lib/include/mc_perf_event.h').read_text();assert all(x in header for x in ('PERF_TYPE_HARDWARE                      = 0','PERF_TYPE_HW_CACHE                      = 3','PERF_TYPE_RAW                           = 4','PERF_FORMAT_TOTAL_TIME_ENABLED          = 1U << 0','PERF_FORMAT_TOTAL_TIME_RUNNING          = 1U << 1','PERF_FORMAT_ID                          = 1U << 2'))
assert '__NR_perf_event_open = 298,' in (ROOT/'kernel/include/syscall.h').read_text()
assert 'int sig_no;' in (ROOT/'kernel/include/process.h').read_text() and 'pub padding: CInt,' in (ROOT/'kernel/rust/abi.rs').read_text()
patch='';full='';files=['kernel/syscall.c','kernel/CMakeLists.txt','kernel/rust/syscall_policy.rs','kernel/rust/f03_perf_entry_candidate.rs']
for name in files:
 parent=(PREV/'postimage'/name).read_text() if name in before else (P/'postimage'/name).read_text()
 post=after.get(name,parent);origpath=P/'preimage'/name;orig=origpath.read_text() if origpath.exists() else ''
 if name in before:
  pre=D/'perf/preimage'/name;out=D/'perf/postimage'/name;pre.parent.mkdir(parents=True,exist_ok=True);out.parent.mkdir(parents=True,exist_ok=True);pre.write_text(parent);out.write_text(post)
  patch+=''.join(difflib.unified_diff(parent.splitlines(True),post.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
 full+=''.join(difflib.unified_diff(orig.splitlines(True),post.splitlines(True),fromfile='a/'+name if origpath.exists() else '/dev/null',tofile='b/'+name))
(D/'PERF-RUST-OWNED-BINDING.DELTA.patch').write_text(patch);(D/'PERF-RUST-OWNED-BINDING.ON-FIRST20.patch').write_text(full)
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_RUST_OWNED_PERF_BINDING_SOURCE_ONLY_DEFAULT_OFF','delta':ref(D/'PERF-RUST-OWNED-BINDING.DELTA.patch'),'whole':ref(D/'PERF-RUST-OWNED-BINDING.ON-FIRST20.patch'),'leaf':ref(D/'perf/postimage/kernel/rust/f03_perf_entry_candidate.rs'),'host_source':ref(ROOT/'kernel/include/process.h'),'perf_header':ref(ROOT/'lib/include/mc_perf_event.h'),'checks':['C runtime binding object replaced by extern declaration; Rust repr-C typed static owns original 31 scalars and 13 provider addresses','original callback body, stack storage and order unchanged','constant values sourced from selected headers, Rust offset_of current qualified layouts','C sig_no maps to Rust Mckfd.padding slot; exact cross-language offset/type witness and actual compilation mandatory','original C/Rust size104/8, request72/8 and binding352/8 assertions retained'],'limits':'Actual selected Rust provider symbols, all 31 native C/Rust offsets and 13 function pointer ABIs require independent emitted/compiled proof; current default selection OFF.','actual_compile_link_native':False,'runtime_authority':None}
(D/'PERF-SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
