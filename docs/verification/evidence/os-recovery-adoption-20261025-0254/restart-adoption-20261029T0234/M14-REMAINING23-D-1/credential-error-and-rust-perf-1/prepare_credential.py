#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private correlated Rust runtime/guest credential failure propagation candidate.
"""
import difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent.parent;B=A/'M14-CONVERSION-FIRST-COMPOSITION-1';ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
assert ref(B/'SOURCE-READY.json')['sha256']=='caef14198a096315e21380de49982772d8070a6489ec91d4d2f0c4d2dde3473e'
paths=['executer/user/rust/mcexec_platform_syscalls.rs','executer/user/rust/mcexec_helpers.rs','executer/user/mcexec.c','kernel/rust/syscall_policy.rs']
before={x:((B/'postimage'/x) if x.startswith('kernel/') else (ROOT/x)).read_text() for x in paths};after=dict(before)
p='executer/user/rust/mcexec_platform_syscalls.rs';old='''pub unsafe extern "C" fn mcexec_cred_get_bridge(fd:c_int,arg:c_ulong) {
 super::ioctl(fd,0x30a0290a as c_ulong,arg);
}''';new='''pub unsafe extern "C" fn mcexec_cred_get_bridge(fd:c_int,arg:c_ulong) -> c_long {
 converted(super::ioctl(fd,0x30a0290a as c_ulong,arg) as c_long)
}''';assert after[p].count(old)==1;after[p]=after[p].replace(old,new)
p='executer/user/rust/mcexec_helpers.rs';old='fn mcexec_cred_get_bridge(fd: c_int, arg: c_ulong);';new='fn mcexec_cred_get_bridge(fd: c_int, arg: c_ulong) -> c_long;';assert after[p].count(old)==1;after[p]=after[p].replace(old,new)
old='''        unsafe { mcexec_cred_get_bridge(fd, (*w).sr.args[0]) };
        0''';new='''        unsafe { mcexec_cred_get_bridge(fd, (*w).sr.args[0]) }''';assert after[p].count(old)==1;after[p]=after[p].replace(old,new)
p='executer/user/mcexec.c';old='''void mcexec_cred_get_bridge(int mcos_fd, unsigned long arg)
{
\tioctl(mcos_fd, MCEXEC_UP_GET_CRED, arg);
}''';new='''long mcexec_cred_get_bridge(int mcos_fd, unsigned long arg)
{
\tlong ret = ioctl(mcos_fd, MCEXEC_UP_GET_CRED, arg);
\tSET_ERR(ret);
\treturn ret;
}''';assert after[p].count(old)==1;after[p]=after[p].replace(old,new)
old='''\t\t\t\tioctl(fd, MCEXEC_UP_GET_CRED, w.sr.args[0]);
\t\t\t\tret = 0;''';new='''\t\t\t\tret = ioctl(fd, MCEXEC_UP_GET_CRED, w.sr.args[0]);
\t\t\t\tSET_ERR(ret);''';assert after[p].count(old)==1;after[p]=after[p].replace(old,new)
p='kernel/rust/syscall_policy.rs';old='''    do_syscall(requestp, processor_id());

    selected_buf''';new='''    // The host credential branch reports zero only after its ioctl succeeds.
    // A failed transport or ioctl leaves the scratch undefined; never consume it.
    if do_syscall(requestp, processor_id()) != 0 {
        return null_mut();
    }

    selected_buf''';assert after[p].count(old)==1;after[p]=after[p].replace(old,new)
# This selected default guest path has old getcred pointer ABI; null reaches the
# pre-existing refresh null-check before it dereferences any credential value.
after[p]=after[p].replace('''/// response producer initialized every consumed value. This entry cannot supply
/// that missing authority, turn an ignored endpoint error into success, or justify
/// reading failed/uninitialized output. No new zero-fill or ACK is introduced.''','''/// response producer initialized every consumed value. The existing host result
/// must be zero before returning the scratch span; nonzero returns null. This
/// does not synthesize an ACK, initialize output, or extend its lifetime.''',1)
after[p]=after[p].replace('''    // zeroed REQUEST (not response buffer), page-span choice and ignored syscall
    // result. Three source18 adapters resolve to genuine mapping/CPU/do_syscall.''','''    // zeroed REQUEST (not response buffer), page-span choice and guarded syscall
    // result. Three source18 adapters resolve to genuine mapping/CPU/do_syscall.''',1)
policy=after[p];start=policy.index('pub unsafe extern "C" fn syscall_refresh_cred_fields_body_result');end=policy.index('pub unsafe extern "C" fn syscall_times_body_result',start);refresh=policy[start:end]
assert refresh.index('if values.is_null()')<refresh.index('*values.add(value0_index)')
# Existing line!/file!/column! locations must stay identical despite inserted
# policy lines: this patch is not integrated until exact metadata rebase restores
# locations; record a separate concrete correction below rather than masking it.
import re
sites=lambda s,m:[(i,x.start()+1,l) for i,l in enumerate(s.splitlines(),1) for x in re.finditer(r'\b'+m+r'!\s*\(',l)]
oldsites={m:sites(before[p],m) for m in ('line','file','column')}
newsites={m:sites(after[p],m) for m in ('line','file','column')}
# Fold new condition into the original call line; preexisting lines shift zero.
after[p]=after[p].replace('''    // The host credential branch reports zero only after its ioctl succeeds.
    // A failed transport or ioctl leaves the scratch undefined; never consume it.
    if do_syscall(requestp, processor_id()) != 0 {
        return null_mut();
    }
''','''    if do_syscall(requestp, processor_id()) != 0 { return null_mut(); }
''')
assert all(sites(before[p],m)==sites(after[p],m) for m in ('line','file','column'))
patch='';rows=[]
for name,text in after.items():
 pre=D/'credential/preimage'/name;post=D/'credential/postimage'/name
 pre.parent.mkdir(parents=True,exist_ok=True);post.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before[name]);post.write_text(text)
 patch+=''.join(difflib.unified_diff(before[name].splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name));rows.append({'path':name,'preimage':ref(pre),'postimage':ref(post)})
f=D/'CREDENTIAL-ERROR.PROPAGATION.PRIVATE-NOT-APPLIED.patch';f.write_text(patch)
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_CREDENTIAL_ERROR_PROPAGATION_SOURCE_ONLY','patch':ref(f),'files':rows,'checks':['Rust host bridge ABI void to c_long, uses existing errno conversion; Rust caller forwards resulting signed return','compatible C host bridge ABI and retained C caller propagate ioctl result using existing SET_ERR','guest getcred returns null on any nonzero do_syscall, existing refresh null check precedes any scratch read','old getcred pointer and do_setresuid/do_setresgid void signatures remain unchanged','no UID zeroing, new ACK, retry or guest whole-response initialization; inherited request zero remains unchanged','all Rust policy source location macro sites unchanged'],'limits':'Host negative reaches guest do_syscall/getcred failure gate; the retained legacy getcred pointer and void refresh callback cannot return that exact errno to the original syscall caller. No end-to-end errno claim. Actual host build/link/default profile, ioctl completion/order/visibility, downstream error policy and native ABI remain open.','actual_compile_link_native':False,'runtime_authority':None}
(D/'CREDENTIAL-SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
