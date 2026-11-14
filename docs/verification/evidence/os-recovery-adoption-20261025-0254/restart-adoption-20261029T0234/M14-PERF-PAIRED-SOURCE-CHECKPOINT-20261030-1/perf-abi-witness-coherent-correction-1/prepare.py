#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Generate private witness inputs. This program does not compile or execute tests.
"""
from pathlib import Path
import hashlib,json,re,difflib
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/MANUAL-RESUME-M14-20261030-2')
O=Path(__file__).resolve().parent
assert not any((O/name).exists() for name in ['f03_perf_entry_abi_witness.rs','RUST-WITNESS-ONLY.PRIVATE.patch','TARGET-CONTRACT.json']), 'preserve prior outputs'
entry=D/'perf-group-failure-source-1/f03_perf_entry_candidate.rs'
cw=D/'perf-paired-selector-private-1/REAL-HEADER-ABI-WITNESS.c.inc'
review=D/'perf-selector-independent-review-1/REVIEW.md'
prior=D/'nonheld-signal-perf-group-compositor-1/NONHELD-SIGNAL-PERF-GROUP.PRIVATE.patch'
cp=D/'perf-paired-selector-private-1/PERF-PAIRED-SELECTOR.PRIVATE.patch'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p,v in {entry:'d542c9f0a1793c8140f38c3d4439a9176742c420f94f792f76eafeb3981f82a5',cw:'212fbf03425ea1e883f01cd4132b3821cca224a015890cabeaf3fda95e80d8c0',review:'daaa6ff29143c886683d0519ead33ec84724cb54cc4208707f8a3f5b486cfee3',prior:'595d137bcaba9b4ce85361623edd5a12c174dc3baa53670bda5352ce80dd1d1a',cp:'7aaa310aaa15d12b0ce3a4c49a48f40e3a0e23a2d14c134b264935fbed93f345'}.items():assert h(p)==v
s=entry.read_text();m=re.search(r'pub\(super\) static f03_perf_entry_binding_v1: PerfEntryBinding = PerfEntryBinding \{\n(.*?)\n\};',s,re.S);assert m
fields=re.findall(r'^\s*(\w+):\s*(.*),\s*$',m.group(1),re.M);assert len(fields)==44
scalars=fields[:31];callbacks=fields[31:];assert len(callbacks)==13
assert all(v.endswith('as CULong') for _,v in scalars)
assert [k for k,v in callbacks]==['copy_from','attr_freq','event_alloc','counter_alloc','syscall','allocate','read','ioctl','mmap','close','fcntl','lock','unlock']
# Existing private parent module supplies every actual type, offset, expression and provider.
callbacktypes=['SyscallCopyFromUserFn','PerfAttrFreqFn','PerfOpenAllocEventFn','PerfCounterAllocFn','PerfOpenSyscallFn','SyscallPolicyAllocFn','SyscallMckfdLongFn','SyscallMckfdIntFn','SyscallMckfdLongFn','SyscallMckfdIntFn','SyscallMckfdIntFn','SyscallMckfdLockFn','SyscallMckfdUnlockFn']
lines=['//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','//! Witness-only module; compile only in a separate object excluded from every image link.','use super::*;','#[used]','#[no_mangle]','pub static f03_perf_entry_rust_scalar_witness_v1: [CULong; 31] = [']
assert scalars[11] == ('allocation_flags', '(super::IHK_MC_AP_NOWAIT) as CULong')
lines += ['    '+(v.replace('super::IHK_MC_AP_NOWAIT', 'super::super::IHK_MC_AP_NOWAIT') if k == 'allocation_flags' else v)+', // '+k for k,v in scalars]
lines += ['];','const _: () = { assert!(size_of::<[CULong; 31]>() == 248); };']
for (k,v),typ in zip(callbacks,callbacktypes):
 match=re.fullmatch(r'Some\((\w+)\)',v);assert match
 lines.append('const _: '+typ+' = '+match.group(1)+'; // '+k)
lines.append('const _: unsafe extern "C" fn(CInt, *mut X86UserContext) -> CLong = sys_perf_event_open;')
w=O/'f03_perf_entry_abi_witness.rs';w.write_text('\n'.join(lines)+'\n')
append='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n// Witness-only: use only in separate, excluded Rust witness object.\n#[cfg(f03_perf_entry_abi_witness)]\n#[path = "f03_perf_entry_abi_witness.rs"]\nmod f03_perf_entry_abi_witness;\n'
p=O/'RUST-WITNESS-ONLY.PRIVATE.patch';p.write_text(''.join(difflib.unified_diff(s.splitlines(keepends=True),(s+append).splitlines(keepends=True),fromfile='a/kernel/rust/f03_perf_entry_candidate.rs',tofile='b/kernel/rust/f03_perf_entry_candidate.rs')))
contracts=[]
for (name,value),typ in zip(callbacks,callbacktypes):contracts.append({'slot':name,'rust_type_alias':typ,'rust_binding_expression':value,'c_expression':{'copy_from':'syscall_copy_from_user_bridge','attr_freq':'perf_event_open_attr_freq_bridge','event_alloc':'perf_event_open_alloc_event_bridge','counter_alloc':'perf_event_open_counter_alloc_bridge','syscall':'perf_event_open_do_syscall_bridge','allocate':'perf_event_alloc_kmalloc_bridge','read':'perf_read','ioctl':'perf_ioctl','mmap':'perf_mmap','close':'perf_close','fcntl':'perf_fcntl','lock':'syscall_mckfd_lock_bridge','unlock':'syscall_mckfd_unlock_bridge'}[name]})
record={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_SOURCE_ONLY_NOT_EXECUTED_OR_RELEASED','inputs':{str(x):h(x) for x in [entry,cw,review,prior,cp]},'outputs':{'rust_witness':{'path':str(w),'sha256':h(w)},'witness_only_entry_patch':{'path':str(p),'sha256':h(p)}},'fields':[{'index':i,'name':k,'rust_expression':v} for i,(k,v) in enumerate(scalars)],'callbacks':contracts,'structure':{'binding_symbol':'f03_perf_entry_binding_v1','scalar_bytes':248,'total_bytes':352,'pointer_bytes':8,'scalar_count':31,'callback_count':13,'endianness':'read from actual ELF; require little-endian x86_64'},'required_independent_checks':['Review exact witness addition and comparator and actual toolchain behavior; source preparation does not authorize execution','C and Rust witnesses compile as separate objects from identical bound config/source/profile; no witness object in any final link','actual compiled C witness 31 values equal actual Rust witness 31 AND the first 31 values of actual production Rust binding, all word-by-word','evaluate actual callback ABI types and actual preprocessed C declarations including erased pointer semantics and calling conventions; Rust type checks alone do not compare C','require all 13 actual production binding relocations and inspect exact targets/aliases, section-symbol addends and final resolved link; counter slot points to local wrapper and wrapper calls counter/free as reviewed','compare exact generated config.h include resolution and ENABLE_PERF, paired actual flags, scalar endianness/size and complete original metadata/link oracle','selected real provider ownership/functional/native checks remain separate'], 'selection':'Default remains OFF. Appending witness patch and cfg is permitted only for a separate unlinked Rust witness object; original selected production object never includes witness cfg or witness patch.', 'compiler_or_native_run':False,'authority':None}
(O/'TARGET-CONTRACT.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({'rust_witness':h(w),'witness_only_patch':h(p),'target_contract':h(O/'TARGET-CONTRACT.json')},indent=2))
