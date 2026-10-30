#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private default-off credential refresh pair reusing existing Rust providers.
"""
import difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent.parent;B=A/'M14-CONVERSION-FIRST-COMPOSITION-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
assert ref(B/'SOURCE-READY.json')['sha256']=='caef14198a096315e21380de49982772d8070a6489ec91d4d2f0c4d2dde3473e'
paths=['kernel/syscall.c','kernel/CMakeLists.txt','kernel/rust/syscall_policy.rs'];before={p:(B/'postimage'/p).read_text() for p in paths};after=dict(before)
c=before['kernel/syscall.c'];start=c.index('void\ndo_setresuid()\n{');end=c.index('\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nlong sys_setresuid',start);old=c[start:end]
assert old.count('syscall_refresh_cred_fields_body_result')==2 and old.count('getcred(_buf)')==2
lines=old.splitlines(True);removed=0;fallback=[]
for line in lines:
 if not line.strip() and removed<4:removed+=1
 else:fallback.append(line)
assert removed==4
fallback=''.join(fallback)
new='#if defined(MCKERNEL_RUST_F03_CREDENTIAL_REFRESH_EXPERIMENTAL)\nextern void do_setresuid(void); extern void do_setresgid(void);\n#else\n'+fallback.rstrip('\n')+'\n#endif'
# Account for the original trailing newline separately.
new+='\n'*(old.count('\n')-new.count('\n'));assert old.count('\n')==new.count('\n')
tok=lambda s:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]',s)
assert tok(old)==tok(fallback)
after['kernel/syscall.c']=c[:start]+new+c[end:]
cm=after['kernel/CMakeLists.txt'];anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_credential_refresh_candidate.rs"\n')
anchor='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\t\tif (MCKERNEL_F03_CREDENTIAL_REFRESH_EXPERIMENTAL)\n\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_credential_refresh_candidate")\n\t\t\t\tendif()\n')
anchor='\n\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\tif (MCKERNEL_F03_CREDENTIAL_REFRESH_EXPERIMENTAL)\n\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_CREDENTIAL_REFRESH_EXPERIMENTAL)\n\t\t\tendif()\n')
after['kernel/CMakeLists.txt']=cm
after['kernel/rust/syscall_policy.rs']+='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_credential_refresh_candidate, target_arch = "x86_64"))]\n#[path = "f03_credential_refresh_candidate.rs"]\nmod f03_credential_refresh_candidate;\n'
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Default-off credential field entry wrappers, reusing the existing refresh body.
use core::{ffi::c_void, mem::{offset_of, MaybeUninit}};
use crate::abi::{CInt, Process, Thread};

/// # Safety
/// The current CPU, thread, process, borrowed scratch and existing getcred
/// synchronous endpoint remain live. The response producer must initialize all
/// four selected fields before the existing refresh helper reads them. Caller
/// retains original field exclusion/validation; no failed response is repaired.
#[no_mangle]
pub unsafe extern "C" fn do_setresuid() {
    let mut scratch = MaybeUninit::<[CInt; 16]>::uninit();
    let thread = unsafe { (*super::get_this_cpu_local_var()).current };
    // SAFETY: Same current thread, stack allocation, indices and getcred provider;
    // no reference to the uninitialized scratch or added null/error policy.
    let _ = unsafe { super::syscall_refresh_cred_fields_body_result(
        thread.cast::<c_void>(), scratch.as_mut_ptr().cast::<CInt>(),
        offset_of!(Thread, proc), offset_of!(Process, ruid), offset_of!(Process, euid),
        offset_of!(Process, suid), offset_of!(Process, fsuid), 0, 1, 2, 3, Some(super::getcred),
    ) };
}

/// # Safety
/// Same current/endpoint and scratch ownership as the uid entry, but the producer
/// must initialize credential slots four through seven before their consumption.
#[no_mangle]
pub unsafe extern "C" fn do_setresgid() {
    let mut scratch = MaybeUninit::<[CInt; 16]>::uninit();
    let thread = unsafe { (*super::get_this_cpu_local_var()).current };
    // SAFETY: Exact existing helper, original field order and gid value indices.
    let _ = unsafe { super::syscall_refresh_cred_fields_body_result(
        thread.cast::<c_void>(), scratch.as_mut_ptr().cast::<CInt>(),
        offset_of!(Thread, proc), offset_of!(Process, rgid), offset_of!(Process, egid),
        offset_of!(Process, sgid), offset_of!(Process, fsgid), 4, 5, 6, 7, Some(super::getcred),
    ) };
}
const _: unsafe extern "C" fn() = do_setresuid;
const _: unsafe extern "C" fn() = do_setresgid;
'''
after['kernel/rust/f03_credential_refresh_candidate.rs']=leaf
assert 'fn getcred(raw_buf: *mut CInt) -> *mut CInt' in before['kernel/rust/syscall_policy.rs']
assert leaf.count('MaybeUninit::<[CInt; 16]>::uninit()')==2 and leaf.count('Some(super::getcred)')==2
assert len(after['kernel/syscall.c'].splitlines())==len(c.splitlines())
directives=lambda s:[(i,l) for i,l in enumerate(s.splitlines(),1) if re.match(r'^\s*#\s*(?:line\b|\d)',l)]
assert directives(after['kernel/syscall.c'])==directives(c)
sites=lambda s,m:[(i,x.start()+1,l)for i,l in enumerate(s.splitlines(),1)for x in re.finditer(r'\b'+m+r'!\s*\(',l)]
for m in ('line','file','column'):assert sites(before['kernel/rust/syscall_policy.rs'],m)==sites(after['kernel/rust/syscall_policy.rs'],m)
assert len(sites(before['kernel/rust/syscall_policy.rs'],'line'))==53
patch='';rows=[]
for name,text in after.items():
 post=D/'postimage'/name;post.parent.mkdir(parents=True,exist_ok=True);post.write_text(text)
 if name in before:
  pre=D/'preimage'/name;pre.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before[name])
 patch+=''.join(difflib.unified_diff(before.get(name,'').splitlines(True),text.splitlines(True),fromfile='a/'+name if name in before else '/dev/null',tofile='b/'+name))
 rows.append({'path':name,'preimage':ref(D/'preimage'/name) if name in before else None,'postimage':ref(post)})
f=D/'CREDENTIAL-PAIR.ON-FIRST20.PRIVATE-NOT-APPLIED.patch';f.write_text(patch)
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_CREDENTIAL_REFRESH_SOURCE_ONLY_DEFAULT_OFF','composition':ref(B/'SOURCE-READY.json'),'patch':ref(f),'files':rows,'checks':['original C fallback tokens and #line origins retained','Rust wrappers reuse exact existing credential body and getcred, original 16-int scratch and indices','no scratch zero-fill, no endpoint result/error or validation changes','same CPU/current lookup and field ordering','Rust metadata sites and default-OFF paired selectors retained'],'open_contract':'Response producer must initialize all consumed indices and preserve endpoint/VM/scratch/process lifetime/exclusion even on failure; no response-initialization authority inferred.','actual_abi_compile_link_native':False,'default_selection_authorized':False,'runtime_authority':None}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
