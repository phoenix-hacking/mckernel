#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only size/alignment witnesses for private default-off perf entry.
"""
import difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent.parent;ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
assert ref(P/'PERF-ENTRY.ON-FIRST20.PRIVATE-NOT-APPLIED.patch')['sha256']=='617305190d63b325a737e5cdaa9fcd371741cb8f7f942f5a8a85b1d3a2559d2b'
paths=['kernel/syscall.c','kernel/rust/f03_perf_entry_candidate.rs'];before={x:(P/'postimage'/x).read_text() for x in paths};after=dict(before)
c=before['kernel/syscall.c'];anchor='#if defined(ENABLE_PERF) && defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)\nstruct f03_perf_entry_binding_v1_type {';assert c.count(anchor)==1
assertions='''#if defined(ENABLE_PERF) && defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)
_Static_assert(sizeof(struct perf_event_attr) == 104 && _Alignof(struct perf_event_attr) == 8, "perf attribute ABI");
_Static_assert(__builtin_offsetof(struct perf_event_attr, type) == 0 && __builtin_offsetof(struct perf_event_attr, read_format) == 32 && __builtin_offsetof(struct perf_event_attr, sample_period) == 16, "perf field ABI");
_Static_assert(sizeof(struct syscall_request) == 72 && _Alignof(struct syscall_request) == 8, "request ABI");
_Static_assert(sizeof(unsigned long) == 8 && sizeof(void (*)(void)) == 8, "binding scalar and callback ABI");
struct f03_perf_entry_binding_v1_type {'''
c=c.replace(anchor,assertions);anchor='};\nconst struct f03_perf_entry_binding_v1_type f03_perf_entry_binding_v1 = {';assert c.count(anchor)==1
c=c.replace(anchor,'};\n_Static_assert(sizeof(struct f03_perf_entry_binding_v1_type) == 352 && _Alignof(struct f03_perf_entry_binding_v1_type) == 8, "binding layout ABI");\nconst struct f03_perf_entry_binding_v1_type f03_perf_entry_binding_v1 = {')
after['kernel/syscall.c']=c
leaf=before[paths[1]].replace('mem::{size_of, MaybeUninit}','mem::{align_of, offset_of, size_of, MaybeUninit}')
old='const _: () = { assert!(size_of::<CULong>() == 8 && size_of::<usize>() == 8); };'
new='''const _: () = {
    assert!(size_of::<CULong>() == 8 && size_of::<usize>() == 8);
    assert!(size_of::<PerfEventAttr>() == 104 && align_of::<PerfEventAttr>() == 8);
    assert!(offset_of!(PerfEventAttr, type_) == 0 && offset_of!(PerfEventAttr, read_format) == 32);
    assert!(offset_of!(PerfEventAttr, sampling) == 16);
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(size_of::<PerfEntryBinding>() == 352 && align_of::<PerfEntryBinding>() == 8);
};'''
assert leaf.count(old)==1;leaf=leaf.replace(old,new);after[paths[1]]=leaf
# Changes add compile-time witnesses only; provider call and metadata field rows
# and original C source remain exact. Actual compilation is still required.
assert c.replace(assertions,'#if defined(ENABLE_PERF) && defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)\nstruct f03_perf_entry_binding_v1_type {').replace('_Static_assert(sizeof(struct f03_perf_entry_binding_v1_type) == 352 && _Alignof(struct f03_perf_entry_binding_v1_type) == 8, "binding layout ABI");\n','')==before['kernel/syscall.c']
assert leaf.replace('mem::{align_of, offset_of, size_of, MaybeUninit}','mem::{size_of, MaybeUninit}').replace(new,old)==before[paths[1]]
files=['kernel/syscall.c','kernel/CMakeLists.txt','kernel/rust/syscall_policy.rs','kernel/rust/f03_perf_entry_candidate.rs'];delta='';whole=''
for path in files:
 original=P/'preimage'/path;orig=original.read_text() if original.exists() else ''
 parent=(P/'postimage'/path).read_text();post=after.get(path,parent)
 if path in after:
  a=D/'preimage'/path;a.parent.mkdir(parents=True,exist_ok=True);a.write_text(parent)
  b=D/'postimage'/path;b.parent.mkdir(parents=True,exist_ok=True);b.write_text(post)
  delta+=''.join(difflib.unified_diff(parent.splitlines(True),post.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
 whole+=''.join(difflib.unified_diff(orig.splitlines(True),post.splitlines(True),fromfile='a/'+path if original.exists() else '/dev/null',tofile='b/'+path))
(D/'PERF-ABI-CORRECTION.patch').write_text(delta);(D/'PERF-ENTRY-ABI.ON-FIRST20.patch').write_text(whole)
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_PERF_ATTRIBUTE_AND_BINDING_ABI_WITNESSES_SOURCE_ONLY','parent_patch':ref(P/'PERF-ENTRY.ON-FIRST20.PRIVATE-NOT-APPLIED.patch'),'delta_patch':ref(D/'PERF-ABI-CORRECTION.patch'),'complete_patch':ref(D/'PERF-ENTRY-ABI.ON-FIRST20.patch'),'perf_header':ref(ROOT/'lib/include/mc_perf_event.h'),'rust_attribute':ref(ROOT/'kernel/rust/f03_perf_event_attr_abi.rs'),'checks':['matching C and Rust compile-time size104/alignment8 and used field offsets','matching C and Rust request72/align8 and provider-table352/align8 witnesses','no provider, argument, runtime fallback, C metadata or original source line changed'],'actual_compiler_link_native':False,'default_selection_authorized':False,'runtime_authority':None}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
