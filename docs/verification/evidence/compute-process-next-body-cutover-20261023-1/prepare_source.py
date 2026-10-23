# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import pathlib, hashlib, json, difflib, shutil
R=pathlib.Path('/home/holden/mckernel')
P=pathlib.Path('/home/holden/mckernel-work/host-preparation/compute-process-next-body-cutover-20261023-1')
E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1'
S=P/'source'; F=P/'fixture'
S.mkdir(exist_ok=True); F.mkdir(exist_ok=True)
def extract(s, marker):
 a=s.index(marker); b=s.index('{',a); level=1; end=b+1
 while level:
  if s[end]=='{': level+=1
  elif s[end]=='}': level-=1
  end+=1
 return s[a:end]
def ident(p):
 b=p.read_bytes(); return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,s):
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s)
c=(R/'kernel/process.c').read_text(); rs=(R/'kernel/rust/sched_helpers.rs').read_text(); h=(R/'kernel/rust/tests/run_equivalence.sh').read_text(); hdr=(R/'kernel/include/sched_helpers.h').read_text()
body=extract(c,'void set_timer(int runq_locked)'); write(P/'ORIGINAL-set_timer.c',body+'\n')
assert body.count('timer_set_timer_body_result')==1 and '#if' not in body
newc=c.replace('static const struct timer_runtime_offsets process_timer_runtime_offsets','PROCESS_SCHED_PUBLIC_BRIDGE const struct timer_runtime_offsets process_timer_runtime_offsets',1)
for prefix in ['unsigned long process_timer_spin_lock_bridge','void process_timer_spin_unlock_bridge','void process_timer_lapic_enable_bridge','void process_timer_lapic_disable_bridge']:
 old='static '+prefix; assert newc.count(old)==1; newc=newc.replace(old,'PROCESS_SCHED_PUBLIC_BRIDGE '+prefix,1)
newc=newc.replace(body,'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+body+'\n#endif',1)
extern='''    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    static mut time_sharing: CInt;
    static process_timer_runtime_offsets: TimerRuntimeOffsets;
    fn process_timer_spin_lock_bridge(lock_addr: usize) -> CULong;
    fn process_timer_spin_unlock_bridge(lock_addr: usize, irqstate: CULong);
    fn process_timer_lapic_enable_bridge(clocks: u32);
    fn process_timer_lapic_disable_bridge();
'''
newrs=rs.replace('unsafe extern "C" {\n','unsafe extern "C" {\n'+extern,1)
wrapper='''/// Preserve the process.c timer entry boundary using the existing timer body.
///
/// # Safety
/// The caller runs on the current CPU under the original scheduler/IRQ contract;
/// runq_locked describes ownership of its runqueue lock. C owns the immutable
/// descriptor and callback providers; no pointer or lock ownership is transferred.
#[no_mangle]
pub unsafe extern "C" fn set_timer(runq_locked: CInt) {
    let v = unsafe { get_this_cpu_local_var() };
    let sharing = unsafe { core::ptr::read(core::ptr::addr_of!(time_sharing)) };
    let _ = unsafe {
        timer_set_timer_body_result(
            v as usize,
            sharing,
            runq_locked,
            core::ptr::addr_of!(process_timer_runtime_offsets),
            Some(process_timer_spin_lock_bridge),
            Some(process_timer_spin_unlock_bridge),
            Some(process_timer_lapic_enable_bridge),
            Some(process_timer_lapic_disable_bridge),
        )
    };
}

'''
anchor='#[no_mangle]\npub unsafe extern "C" fn timer_set_timer_body_result('
assert newrs.count(anchor)==1; newrs=newrs.replace(anchor,wrapper+anchor,1)
cstruct=extract(hdr,'struct timer_runtime_offsets')+';\n'
rstruct='#[repr(C)]\n'+extract(rs,'pub struct TimerRuntimeOffsets')+'\n'
stub='__attribute__((weak)) void set_timer(int runq_locked) { (void)runq_locked; }'
assert h.count(stub)==1
stubs=cstruct+'''/* Only host equivalence bindings; production providers remain process.c. */
__attribute__((weak)) const struct timer_runtime_offsets process_timer_runtime_offsets;
__attribute__((weak)) unsigned long process_timer_spin_lock_bridge(unsigned long p)
{ (void)p; return 0; }
__attribute__((weak)) void process_timer_spin_unlock_bridge(unsigned long p, unsigned long s)
{ (void)p; (void)s; }
__attribute__((weak)) void process_timer_lapic_enable_bridge(unsigned int c) { (void)c; }
__attribute__((weak)) void process_timer_lapic_disable_bridge(void) {}
'''
newh=h.replace(stub,stubs,1)
ledger="grep -Eq 'U set_timer' \"${tmpdir}/out/rust.undefined\""
assert newh.count(ledger)==1
newh=newh.replace(ledger,"grep -Eq ' T set_timer$' \"${tmpdir}/out/rust.global\"\n! grep -Eq 'U set_timer$' \"${tmpdir}/out/rust.undefined\"\n"+'\n'.join("grep -Eq 'U "+n+"$' \"${tmpdir}/out/rust.undefined\"" for n in ['process_timer_runtime_offsets','process_timer_spin_lock_bridge','process_timer_spin_unlock_bridge','process_timer_lapic_enable_bridge','process_timer_lapic_disable_bridge']),1)
assert newh.count("-eq 593")==1; newh=newh.replace('-eq 593','-eq 597',1)
changes={'kernel/process.c':newc,'kernel/rust/sched_helpers.rs':newrs,'kernel/rust/tests/run_equivalence.sh':newh}
patch=''
for rel,new in changes.items():
 old=(R/rel).read_text(); write(S/rel,new)
 patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel,n=4))
write(P/'PRIVATE-PRODUCTION.patch',patch)
write(F/'original.c',body.replace('void set_timer(', 'void original_set_timer(')+'\n')
alias='''use core::ptr::{read_volatile, write_volatile};
type CInt=i32; type CULong=u64; type CpuLocalVar=u8;
'''
for key in ['type TimerSpinLockFn =','type TimerSpinUnlockFn =','type TimerLapicEnableFn =','type TimerLapicDisableFn =','const EINVAL:','const PS_RUNNING:']:
 a=rs.index(key); alias+=rs[a:rs.index(';',a)+1]+'\n'
leaf=alias+rstruct+'unsafe extern "C" {\n'+extern+'''    fn timer_set_timer_body_result(cpu: usize, sharing: CInt, locked: CInt,
        offsets: *const TimerRuntimeOffsets, lock: Option<TimerSpinLockFn>,
        unlock: Option<TimerSpinUnlockFn>, enable: Option<TimerLapicEnableFn>,
        disable: Option<TimerLapicDisableFn>) -> CInt;
}\n'''+wrapper
for name in ['list_next','list_empty_addr']:
 leaf+=extract(rs,'unsafe fn '+name)+'\n'
leaf+='#[no_mangle]\n'+extract(rs,'pub unsafe extern "C" fn timer_set_timer_body_result').replace('fn timer_set_timer_body_result(', 'fn leaf_timer_set_timer_body_result(',1)+'\n'
write(F/'actual.rs',leaf)
write(F/'timer-offsets.h',cstruct)
write(F/'abi.c','#include <sched_helpers.h>\n_Static_assert(sizeof(unsigned long)==8,"ulong64");\n_Static_assert(sizeof(int)==4,"int32");\n_Static_assert(sizeof(struct timer_runtime_offsets)==120,"existing15offsets");\nvoid abi(void) { void (*p)(int)=set_timer; (void)p; }\n'.replace('#include <sched_helpers.h>','#include <sched_helpers.h>\n#include <process.h>'))
write(P/'SOURCE-BINDINGS.json',json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'SOURCE_ONLY_NOT_COMPILED','source_inputs':{rel:ident(R/rel) for rel in changes},'outputs':{rel:ident(S/rel) for rel in changes},'original_body':ident(P/'ORIGINAL-set_timer.c'),'patch':ident(P/'PRIVATE-PRODUCTION.patch'),'existing_header':ident(R/'kernel/include/sched_helpers.h'),'existing_process_header':ident(R/'kernel/include/process.h'),'fixture_semantics':'Original C wrapper and actual Rust wrapper feed captured callback/descriptor arguments to the same extracted existing actual Rust timer body. Host fixture models layout only; ABI TU uses real current headers.','whole_C_TU_default_kernel_native':'OPEN'},indent=2)+'\n')
print(json.dumps({'patch':ident(P/'PRIVATE-PRODUCTION.patch'),'bindings':ident(P/'SOURCE-BINDINGS.json')}))
