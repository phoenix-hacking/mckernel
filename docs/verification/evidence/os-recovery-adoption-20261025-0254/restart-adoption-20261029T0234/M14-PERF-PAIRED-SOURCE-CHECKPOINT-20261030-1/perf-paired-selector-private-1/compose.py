#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source and witness preparation only; no tree materialization or execution.
"""
from pathlib import Path
import hashlib,json,re,difflib
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234')
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/MANUAL-RESUME-M14-20261030-2')
O=Path(__file__).resolve().parent
C=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/syscall.c'
CM=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/CMakeLists.txt'
profile=E/'M14-CONVERSION-FIRST-PRODUCER-BINDING-1/current-frontier-successor-1/PROFILE.SOURCE-ONLY.json'
combined=D/'nonheld-signal-perf-group-compositor-1/NONHELD-SIGNAL-PERF-GROUP.PRIVATE.patch'
entry=D/'perf-group-failure-source-1/f03_perf_entry_candidate.rs'
full=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1/attempt-0001/m14-full28-procfs-successor-1/postimage/kernel/syscall.c')
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
expected={C:'3388adb79adff66eb85ae65a443af2c18e7b2057dd76d0ec99b531d62a36cab3',CM:'30e3a04bf48777d4891f7390804e574ca221e4234e9a8d7879bb068910a13fbd',profile:'8ab49c299dfc9218ddcf8df3cf71474d51e87167abe4cd166841ea47c3a32e2d',combined:'595d137bcaba9b4ce85361623edd5a12c174dc3baa53670bda5352ce80dd1d1a',entry:'d542c9f0a1793c8140f38c3d4439a9176742c420f94f792f76eafeb3981f82a5',full:'819eb6a81a6565057213f0c90a2b42868e2b9beed09811596d7cab6394c1ecca'}
for p,d in expected.items():assert h(p)==d,(p,h(p))
s=C.read_text(); a=s.splitlines(keepends=True)
start='#line 21470\n\n\nlong sys_perf_event_open(int n, ihk_mc_user_context_t *ctx)\n';assert s.count(start)==1
end='}\n#endif /* ENABLE_PERF */\n\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nconst char f03_rt_sigtimedwait_source_file[]';assert s.count(end)==1
# Calculate the logical line of the original #endif, then restore it after the new conditional.
pos=s.index(end)+2; line=1
for x in s[:pos].splitlines():
 m=re.match(r'^\s*#\s*line\s+(\d+)',x)
 line=int(m.group(1)) if m else line+1
orig_endif_line=line
prefix='#if defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)\nextern long sys_perf_event_open(int n, ihk_mc_user_context_t *ctx);\n#else\n'
t=s.replace(start,prefix+start,1).replace(end,'}\n#endif /* MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL */\n#line '+str(orig_endif_line)+'\n#endif /* ENABLE_PERF */\n\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nconst char f03_rt_sigtimedwait_source_file[]',1)
# Extract only original perf ABI declaration from retained full28 source, never its broad tree.
f=full.read_text(); anchor='/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n#if defined(ENABLE_PERF) && defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)\n_Static_assert(sizeof(struct perf_event_attr)'
i=f.index(anchor);j=f.index('\n#endif',i)+len('\n#endif'); witness=f[i:j]+'\n'
# Additional numeric witness: exact C header expressions for all 31 Rust binding scalars.
values=['sizeof(struct perf_event_attr)','__builtin_offsetof(struct perf_event_attr, type)','__builtin_offsetof(struct perf_event_attr, read_format)','__builtin_offsetof(struct perf_event_attr, sample_period)','PERF_TYPE_RAW','PERF_TYPE_HARDWARE','PERF_TYPE_HW_CACHE','PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING | PERF_FORMAT_ID','1UL << 63','__NR_perf_event_open','sizeof(struct mckfd)','IHK_MC_AP_NOWAIT','__builtin_offsetof(struct mc_perf_event, pid)','__builtin_offsetof(struct mc_perf_event, counter_id)','__builtin_offsetof(struct process, mckfd)','__builtin_offsetof(struct mckfd, next)','__builtin_offsetof(struct mckfd, fd)','__builtin_offsetof(struct mckfd, data)','__builtin_offsetof(struct mc_perf_event, group_leader)','__builtin_offsetof(struct mc_perf_event, sibling_list)','__builtin_offsetof(struct mc_perf_event, group_entry)','__builtin_offsetof(struct mc_perf_event, nr_siblings)','__builtin_offsetof(struct mc_perf_event, pmc_status)','__builtin_offsetof(struct thread, pmc_alloc_map)','__builtin_offsetof(struct process, mckfd_lock)','__builtin_offsetof(struct mckfd, sig_no)','__builtin_offsetof(struct mckfd, read_cb)','__builtin_offsetof(struct mckfd, ioctl_cb)','__builtin_offsetof(struct mckfd, mmap_cb)','__builtin_offsetof(struct mckfd, close_cb)','__builtin_offsetof(struct mckfd, fcntl_cb)']
assert len(values)==31
witness+='\n#if defined(ENABLE_PERF) && defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL) && defined(MCKERNEL_F03_PERF_ENTRY_ABI_WITNESS)\n_Static_assert(__builtin_types_compatible_p(__typeof__(&sys_perf_event_open), long (*)(int, ihk_mc_user_context_t *)), "perf entry function type");\n__attribute__((used)) static const unsigned long f03_perf_entry_c_header_witness_v1[31] = {\n'+''.join('    '+v+',\n' for v in values)+'};\n#endif\n'
guard='''\n/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n#if defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL) && (!defined(ENABLE_PERF) || !defined(__x86_64__) || !defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) || !defined(MCKERNEL_RUST_F03_SYNC_CHILD_EVENT) || !defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) || !defined(MCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES))\n#error "perf entry requires matched x86 perf and selected providers"\n#endif\n'''
t+='\n'+guard+witness
# C logical line maps for each unchanged original line; added conditional must preserve all.
def logical(lines):
 n=1;out=[]
 for l in lines:
  out.append(n);m=re.match(r'^\s*#\s*line\s+(\d+)',l);n=int(m.group(1)) if m else n+1
 return out
b=t.splitlines(keepends=True); x=logical(a);y=logical(b)
for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
 if tag=='equal':
  for ii,kk in zip(range(i,j),range(k,l)):
   if not re.match(r"^\s*#\s*line\s+\d+",a[ii]): assert x[ii]==y[kk],(ii+1,kk+1,a[ii],x[ii],y[kk])
# Profile is a bounded delta, not an executable admission. Existing actual command identities retained by reference.
p=json.loads(profile.read_text());rust=p['exact_commands'][0]['argv'];cc=p['exact_commands'][1]['argv']
for z in ['enable_perf','f03_sync_child_event_candidate','f03_leaf_callbacks_candidate','f03_perf_alloc_bridges_selected_candidate']:assert z in rust,z
for z in ['-DMCKERNEL_RUST_F03_SYNC_CHILD_EVENT','-DMCKERNEL_RUST_F03_LEAF_CALLBACKS','-DMCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES','-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS']:assert z in cc,z
assert 'f03_perf_entry_candidate' not in rust and '-DMCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL' not in cc
# CMake context has matching current providers; it is not modified, and no option defaults change.
cm=CM.read_text();assert all(z in cm for z in ['f03_sync_child_event_candidate','f03_perf_alloc_bridges_selected_candidate','MCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES','MCKERNEL_RUST_F03_SYNC_CHILD_EVENT'])
patch=''.join(difflib.unified_diff(a,b,fromfile='a/kernel/syscall.c',tofile='b/kernel/syscall.c'))
out=O/'PERF-PAIRED-SELECTOR.PRIVATE.patch';out.write_text(patch)
(O/'REAL-HEADER-ABI-WITNESS.c.inc').write_text(witness)
record={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'SOURCE_ONLY_DELTA_NOT_A_BUILD_RELEASE','baseline':{'profile_path':str(profile),'profile_sha256':h(profile),'combined_rust_patch_path':str(combined),'combined_rust_patch_sha256':h(combined),'C_path':str(C),'C_sha256':h(C),'CMake_path':str(CM),'CMake_sha256':h(CM)},'delta':{'experimental_rust_argv_addition':['--cfg','f03_perf_entry_candidate'],'experimental_C_argv_addition':['-DMCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL'],'real_header_witness_C_argv_addition':['-DMCKERNEL_F03_PERF_ENTRY_ABI_WITNESS'],'C_patch_sha256':h(out),'witness_sha256':h(O/'REAL-HEADER-ABI-WITNESS.c.inc')},'default':'Default baseline has neither selector; C body remains selected. CMake unchanged. Only a future specifically reviewed exact raw producer may select both flags; never enable one in isolation.', 'checks':['baseline C and selected prior Rust hashes pinned','C fallback body byte-exact and all unchanged C logical line coordinates preserved','31 actual C-header scalar expressions in read-only witness for comparison with Rust binding','prior Rust argv includes enable_perf and paired provider cfgs; C argv includes selected provider flags and no entry selector; C ENABLE_PERF must be established from actual headers','C guard rejects missing checked C provider flags; Rust guard independently requires corresponding Rust cfgs'], 'required_before_execution':['independent review of exact source patch, witness, flags and unmatched C/Rust configuration failure cases','review explicit control, physical ownership/resource and exact operation release; no current authority','bind closed source map including witness, new source/profile/guard, exact actual SDK21/header/toolchain and object dependencies; verify C ENABLE_PERF from bound headers','review 31 header values against Rust binding, all 13 callbacks and sys_perf_event_open ABI/type/relocations, provider uniqueness including Rust counter wrapper','check selection ON/OFF, original 389 metadata and complete current-consumer/link oracle on matching image','qualify actual allocation/counter/group ownership, synchronization, functional and native behavior'], 'exclusions':'Held direct-TID/terminate_host and execve transfer/ACK not selected or modified. No C retirement or acceptance asserted.','native_or_compile':False,'authority':None}
(O/'PROFILE.SOURCE-ONLY.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({'patch':h(out),'profile':h(O/'PROFILE.SOURCE-ONLY.json'),'witness':h(O/'REAL-HEADER-ABI-WITNESS.c.inc'),'logical_original_endif':orig_endif_line,'C_unchanged_lines_checked':len(a)},indent=2))
