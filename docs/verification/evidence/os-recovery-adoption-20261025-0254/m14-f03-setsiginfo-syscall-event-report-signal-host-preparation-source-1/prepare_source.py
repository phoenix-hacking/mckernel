"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact three-wrapper bank composition; source-only HOST preparation, no execution.
"""
from pathlib import Path
import hashlib,json,re,difflib,shutil,importlib.util,ast
D=Path(__file__).resolve().parent;E=D.parent;A=E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'
N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717');S=N/'f03-next-unbanked-body-source-1';W=N/'f03-next-unbanked-wrappers-source-2'
REL=E/'m14-f02-local14-final14-qualified-preparation-source-1/relative-module-context-correction-source-1'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def write(n,t):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t)
def js(n,x):write(n,json.dumps(x,indent=2)+'\n')
assert ref(S/'READY.SOURCE-ONLY.json')['sha256'].startswith('6777') and ref(W/'READY.SOURCE-ONLY.json')['sha256'].startswith('357b')
actual=read(A/'PROFILE.SOURCE-ONLY.json');cbase=next(x['postimage'] for x in actual['inputs']['postimages'] if x['relative']=='kernel/syscall.c');assert cbase['sha256']=='d6e9c595364f72018b96ccba50e97ebc71ff438b8e91315982e287d63ff8bafb'
actualmap=read(actual['inputs']['source_directory_exports'][0]['manifest']['path']);policy=next(x['snapshot'] for x in actualmap['files'] if x['relative']=='syscall_policy.rs');assert policy['sha256']=='2975c9c2d0c398a8acffb52b0936ae46ab2b73d65d45113be93730802fe276d7'
c=Path(cbase['path']).read_text();rust=Path(policy['path']).read_text()
assert c==(W/'base/kernel/syscall.c').read_text()
combined=(W/'postimage/kernel/syscall.c').read_text()
# Add only the two frozen setsiginfo selector insertions to the pair C postimage.
sbase=(S/'base/kernel/syscall.c').read_text().splitlines(True);spost=(S/'postimage/kernel/syscall.c').read_text().splitlines(True);insertions=[]
for tag,i,j,k,l in difflib.SequenceMatcher(a=sbase,b=spost,autojunk=False).get_opcodes():
 if tag=='equal':continue
 assert tag=='insert';anchor=''.join(sbase[max(0,i-8):i]);addition=''.join(spost[k:l]);assert combined.count(anchor)==1;combined=combined.replace(anchor,anchor+addition,1);insertions.append(dict(anchor=anchor,addition=addition))
assert len(insertions)==2
body=(S/'ptrace_setsiginfo.FRAGMENT.rs').read_text();event=(W/'ptrace_syscall_event.FRAGMENT.rs').read_text();attribute=(W/'expose_existing_signal_adapter.ATTRIBUTE.rs.inc').read_text().strip()
fn='unsafe extern "C" fn f03_exec_report_signal_v1(thread:*mut c_void,sig:CInt) {';assert rust.count(fn)==1 and '#[cfg_attr(f03_ptrace_entry_candidate, no_mangle)]\n'+fn not in rust
newrust=rust.replace(fn,attribute+'\n'+fn,1)+'\n'+body+'\n'+event
write('candidate/kernel/syscall.c',combined);write('candidate/kernel/rust/syscall_policy.rs',newrust);write('preimages/syscall.c',c);write('preimages/syscall_policy.rs',rust)
for name,old,new in [('syscall.c',c,combined),('syscall_policy.rs',rust,newrust)]:write('patches/'+name+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='actual114/'+name,tofile='three-wrapper-candidate/'+name)))
# Production-like complete119 source layout. NO F02 LOCAL14 candidate sources.
root=D/'context-root';rr=root/'kernel/rust';rows=[]
for row in actualmap['files']:
 dest=rr/row['relative'];dest.parent.mkdir(parents=True,exist_ok=True)
 if row['relative']=='syscall_policy.rs':dest.write_text(newrust)
 else:shutil.copyfile(row['snapshot']['path'],dest)
 rows.append(dict(relative=row['relative'],original=row['snapshot'],snapshot=ref(dest)))
assert len(rows)==119
relative=read(REL/'CLOSED-RUST-MODULE-CONTEXT.json');externals=[]
for row in relative['external_relative_modules']:
 src=Path(row['snapshot']['path']);assert ref(src)==row['snapshot'];dest=root/row['relative_to_context_root'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest);nr=dict(row,snapshot=ref(dest));externals.append(nr)
assert len(externals)==3 and all((rr/x['import_literal']).resolve()==Path(x['snapshot']['path']) for x in externals)
js('CLOSED-RUST-MODULE-CONTEXT.json',dict(scope=__doc__.splitlines()[0],runtime_authority=None,status='ACTUAL114_119_SOURCES_WITH_EXACT_THREE_WRAPPERS_AND_GENUINE_RELATIVE_CONTEXT',context_root=str(root),Rust_source_root=str(rr),crate_entry=ref(rr/'lib.rs'),Rust_files=rows,external_relative_modules=externals,relative_context_predecessor=ref(REL/'CLOSED-RUST-MODULE-CONTEXT.json'),source6153=actual['inputs']['source6153'],LOCAL14_or_WAKE3_LOCK4_selected=False,private_ABI_mirrors=0))
# Test-only layout words appended to HOST crate in actual defining modules/types.
witness='''
// HOST qualification witness only; not part of the production candidate patch.
#[cfg(f03_ptrace_entry_candidate)]
#[no_mangle]
pub static f03_ptrace_HOST_ABI: [usize; 9] = [
    core::mem::size_of::<crate::abi::SigInfo>(),
    core::mem::align_of::<crate::abi::SigInfo>(),
    core::mem::size_of::<crate::abi::SigPending>(),
    core::mem::align_of::<crate::abi::SigPending>(),
    core::mem::offset_of!(crate::abi::SigPending, info),
    core::mem::offset_of!(crate::abi::Thread, ptrace),
    core::mem::size_of::<crate::abi::CInt>(),
    core::mem::size_of::<crate::abi::CLong>(),
    IHK_MC_AP_NOWAIT as usize,
];
#[cfg(f03_ptrace_entry_candidate)]
const _: unsafe extern "C" fn(crate::abi::CInt, *mut crate::abi::SigInfo) -> crate::abi::CLong = ptrace_setsiginfo_entry::f03_ptrace_setsiginfo_v1;
#[cfg(f03_ptrace_entry_candidate)]
const _: unsafe extern "C" fn(*mut crate::abi::Thread) = ptrace_syscall_event_entry::ptrace_syscall_event;
#[cfg(f03_ptrace_entry_candidate)]
const _: PtraceReportSignalFn = f03_exec_report_signal_v1;
'''
with (rr/'syscall_policy.rs').open('a') as f:f.write(witness)
js('HOST-WITNESS-BINDING.json',dict(scope=__doc__.splitlines()[0],runtime_authority=None,production_policy=ref(D/'candidate/kernel/rust/syscall_policy.rs'),HOST_policy=ref(rr/'syscall_policy.rs'),witness_only=witness,uses_actual_defining_ABI_module=next(x['snapshot'] for x in rows if x['relative']=='abi.rs'),no_runtime_provider_stubs=True,no_ABI_mirrors=True))
# Update only HOST map leaf after explicit fixture-only witness addition.
ctx=read(D/'CLOSED-RUST-MODULE-CONTEXT.json');next(x for x in ctx['Rust_files'] if x['relative']=='syscall_policy.rs')['snapshot']=ref(rr/'syscall_policy.rs');js('CLOSED-RUST-MODULE-CONTEXT.json',ctx)
fixture='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "'''+str(D/'candidate/kernel/syscall.c')+'''"
_Static_assert(sizeof(siginfo_t)==128,"genuine SigInfo128");
_Static_assert(sizeof(struct sig_pending)==160,"genuine SigPending160");
_Static_assert(__builtin_offsetof(struct sig_pending,info)==24,"genuine pendinginfo24");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ptrace_setsiginfo),long (*)(int,siginfo_t *)),"setsiginfo exactlong/int/pointer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ptrace_syscall_event),void (*)(struct thread *)),"public event void/thread ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ptrace_report_signal_bridge),void (*)(void *,int)),"signal callback void/opaque/int ABI");
const unsigned long f03_ptrace_C_ABI[9]={sizeof(siginfo_t),__alignof__(siginfo_t),sizeof(struct sig_pending),__alignof__(struct sig_pending),__builtin_offsetof(struct sig_pending,info),__builtin_offsetof(struct thread,ptrace),sizeof(int),sizeof(long),IHK_MC_AP_NOWAIT};
'''
write('fixture/genuine_candidate_abi.c',fixture)
# Exact retained semantic bodies: no duplication, mocking or new algorithm.
helpers=[]
for name in ['ptrace_setsiginfo_body_result','ptrace_syscall_event_body_result','ptrace_report_signal']:
 start=rust.index('pub unsafe extern "C" fn '+name+'(');openbrace=rust.index('{',start);level=1;end=openbrace+1
 while level:
  if rust[end]=='{':level+=1
  elif rust[end]=='}':level-=1
  end+=1
 text=rust[start:end];assert text in newrust;helpers.append(dict(name=name,source_sha256=hashlib.sha256(text.encode()).hexdigest(),bytes=len(text),unchanged=True))
js('REUSED-SEMANTIC-PROVIDER-SOURCE-PROOF.json',dict(scope=__doc__.splitlines()[0],runtime_authority=None,actual114_profile=ref(A/'PROFILE.SOURCE-ONLY.json'),retained_actual_Rust=next(x['source'] for x in actual['inputs']['objects'] if x['link_token']=='rust/mckernel_rust.o'),body_source=policy,helpers=helpers,new_algorithms=0,dynamic_new_wrapper_semantic_cases_run=0,retained_wholehelper_test_source='kernel/rust/run_equivalence.sh:39487/39510 in frozen6777 references; not replayed or claimed newlypassing',native_or_whole_file_credit=0))
# Existing ordinary HOST flags/tools/profile; use actual114 Rust cfgs, not F02cfgs.
O=D/'HOST-output-proposed-1';assert not O.exists();basehost=read(REL/'PROFILE.NOT-GRANTED.json');oldplan=read(REL/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')['commands'];rustargv=list(actual['exact_commands'][0]['argv']);rustargv[rustargv.index('/nightly/bin/rustc')]=oldplan[0]['argv'][oldplan[0]['argv'].index('/home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu/bin/rustc')] if '/home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu/bin/rustc' in oldplan[0]['argv'] else '/home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu/bin/rustc'
rustargv=[('--emit=obj='+str(O/'rust-selected.o')) if x.startswith('--emit=obj=') else x for x in rustargv];rustargv[-1]=str(rr/'lib.rs')
assert 'f03_ptrace_entry_candidate' in rustargv and 'process_verbose_local_companions' not in rustargv
cc=list(oldplan[1]['argv']);cc=cc[:cc.index('-c')];cc=[x for x in cc if not any(y in x for y in ['MCKERNEL_RUST_PROCESS_VERBOSE_LOCAL','MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE','MCKERNEL_PROCESS_DDEBUG_FILE','MCKERNEL_PROCESS_DDEBUG_FLAGS','MCKERNEL_RUST_PROCESS_VERBOSE_DATA'])]
# Use actual114 syscall defines, mapped onto same genuine GCC9 HOST include roots.
actualcc=actual['exact_commands'][1]['argv'];defines=[x for x in actualcc if x.startswith('-D')];assert actualcc[-1]=='/src/kernel/syscall.c'
cc=[cc[0]]+defines+[x for x in cc[1:] if not x.startswith('-D')]
assert '-DMCKERNEL_RUST_F03_PTRACE_ENTRY' in cc and '-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS' in cc
lld=oldplan[3]['argv'][0];actualrust=A/'OUTPUT/work/output/build/kernel/rust/mckernel_rust.o'
commands=[dict(name='00-full119Rust-actualABI-wrappers-and-existing-signal-body',argv=rustargv),dict(name='01-selected-genuine-syscallTU-CABI',argv=cc+['-c',str(D/'fixture/genuine_candidate_abi.c'),'-o',str(O/'selected.o')]),dict(name='02-original-ptraceentry-off-fallback-TU-CABI',argv=cc+['-UMCKERNEL_RUST_F03_PTRACE_ENTRY','-c',str(D/'fixture/genuine_candidate_abi.c'),'-o',str(O/'fallback.o')]),dict(name='03-selected-fullRust-and-C-partial-link',argv=[lld,'-flavor','gnu','-r',str(O/'rust-selected.o'),str(O/'selected.o'),'-o',str(O/'selected-joint.o')]),dict(name='04-fallback-with-retained-actual114Rust-partial-link',argv=[lld,'-flavor','gnu','-r',str(actualrust),str(O/'fallback.o'),'-o',str(O/'fallback-joint.o')]),dict(name='05-genuineABI-selectedcallback-and-fullRust-origin-qualification',argv=['/usr/bin/python3','-B',str(D/'qualify_changed_objects.py'),str(O)])]
for c in commands:c['purpose']=__doc__.splitlines()[0]+' '+c['name']
js('EXACT-SIX-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json',dict(scope=__doc__.splitlines()[0],runtime_authority=None,commands=commands,expected_stdout='PTRACE3 PASS genuineABI/fullRust/selectedCcallback/publicsymbol/fallback; behavior-nativeOPEN\n'))
js('COMPOSITION-AND-SCOPE.json',dict(scope=__doc__.splitlines()[0],runtime_authority=None,body6777=ref(S/'READY.SOURCE-ONLY.json'),pair357b=ref(W/'READY.SOURCE-ONLY.json'),baseC=cbase,baseRust=policy,newC=ref(D/'candidate/kernel/syscall.c'),newRust=ref(D/'candidate/kernel/rust/syscall_policy.rs'),selected_C_wrappers=['ptrace_setsiginfo','ptrace_syscall_event','ptrace_report_signal_bridge'],new_Rust_definitions=2,existing_Rust_body_exported='f03_exec_report_signal_v1',existing_selector='f03_ptrace_entry_candidate / MCKERNEL_RUST_F03_PTRACE_ENTRY with policyhelpers',new_cfg_axes=0,semantic_helpers=helpers,setsig_C_insertions=insertions,WAKE3_LOCK4_F02_changes=0,all_actual_cpp_compiler_HOST_link_native_run=False,root_sole_integration_admission=True))
print('PASS private3wrapper composition,119source production-like root+3genuine relativemodules, sixunrun HOST commands prepared')
