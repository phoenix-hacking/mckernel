from pathlib import Path
import subprocess,resource,time,json,re,os,hashlib,signal
O=Path(__file__).parent
E=O/'checks-1'
records=[]
CAP_BYTES=32*1024**2

def limits(cap_bytes):
 os.sched_setaffinity(0,{7})
 for kind,n in [(resource.RLIMIT_CPU,30),(resource.RLIMIT_AS,1024**3),(resource.RLIMIT_FSIZE,cap_bytes),(resource.RLIMIT_CORE,0)]:
  resource.setrlimit(kind,(n,n))

def run(n,args,*,cap_bytes=CAP_BYTES,wall_seconds=35,kill_grace=2):
 assert re.fullmatch(r'[a-zA-Z0-9_-]+',n) and 0<cap_bytes<=CAP_BYTES
 assert 0<wall_seconds<=35 and 0<kill_grace<=2
 E.mkdir(exist_ok=True)
 t=time.monotonic();p=None;timed_out=False;cleanup=[]
 # Child-owned writes into regular files are subject to the child's FSIZE limit.
 # Exclusive creation preserves every prior attempt and never truncates evidence.
 with (E/(n+'.stdout')).open('xb') as out, (E/(n+'.stderr')).open('xb') as err:
  try:
   p=subprocess.Popen(args,stdout=out,stderr=err,preexec_fn=lambda:limits(cap_bytes),start_new_session=True)
   try:p.wait(timeout=wall_seconds)
   except subprocess.TimeoutExpired:
    timed_out=True
  finally:
   if p is not None and p.poll() is None:
    try:os.killpg(p.pid,signal.SIGTERM);cleanup.append('SIGTERM_process_group')
    except ProcessLookupError:cleanup.append('SIGTERM_group_already_gone')
    try:p.wait(timeout=kill_grace)
    except subprocess.TimeoutExpired:
     try:os.killpg(p.pid,signal.SIGKILL);cleanup.append('SIGKILL_process_group')
     except ProcessLookupError:cleanup.append('SIGKILL_group_already_gone')
     finally:p.wait()
   if p is not None:p.wait()
 # No parent PIPE buffering or parent rewrite of captured child output.
 captures={}
 for ext in ['stdout','stderr']:
  f=E/(n+'.'+ext);size=f.stat().st_size
  h=hashlib.sha256()
  with f.open('rb') as stream:
   for block in iter(lambda:stream.read(32768),b''):h.update(block)
  captures[ext]=dict(bytes=size,sha256=h.hexdigest(),within_cap=size<=cap_bytes,cap_reached=size>=cap_bytes)
 row=dict(label=n,argv=args,pid=p.pid,returncode=p.returncode,direct_child_joined=True,seconds=time.monotonic()-t,timed_out=timed_out,cleanup=cleanup,capture_method='direct regular-file child writes',cap_bytes_per_stream=cap_bytes,captures=captures)
 (E/(n+'.status.json')).write_text(json.dumps(row,indent=2)+'\n');records.append(row);(E/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
 assert not timed_out and p.returncode==0 and all(x['within_cap'] and not x['cap_reached'] for x in captures.values()),(n,'STOP unexpected failure, retained file-backed streams')
 # Success reads at most the configured cap; no unsuccessful output is collected.
 return (E/(n+'.stdout')).read_bytes().decode()


def function(text,name):
 m=re.search(r'(?m)^(?:#\[no_mangle\]\n)?(?:pub )?(?:unsafe )?(?:extern "C" )?fn '+name+r'\(',text);assert m,name;a=text.index('{',m.start());d=1;i=a+1
 while d:d+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[m.start():i]+chr(10)
def cfunction(text,name):
 a=text.index('void '+name+'(');s=text.index('{',a);d=1;i=s+1
 while d:d+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[a:i]+chr(10)
def extern_decl(text,name):
 m=re.search(r'(?m)^    fn '+name+r'\(',text)
 if m:return text[m.start():text.index(';',m.start())+1]
 body=function(text,name);head=body[:body.index('{')].strip();return re.sub(r'^(?:#\[no_mangle\]\n)?pub unsafe extern "C" fn ','fn ',head)+';'
def main():
 E.mkdir(exist_ok=False);root=Path('/home/holden/mckernel');rs=(root/'kernel/rust/process_helpers.rs').read_text();c=(root/'kernel/process.c').read_text()
 expected=json.loads((O/'integration-status.json').read_text())['after_sha256']
 assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in expected.items())
 names=['__release_tid','process_destroy_thread_time_account_bridge','process_destroy_thread_hash_detach_bridge'];bodyfiles=[Path('/home/holden/mckernel-work/host-preparation/rust-next-process-leaf-20261018-1/release-tid-body.rs'),Path('/home/holden/mckernel-work/host-preparation/rust-next-compatible-leaf-20261019-1/time-account-body.rs'),Path('/home/holden/mckernel-work/host-preparation/rust-next-normal-leaf-20261019-1/hash-detach-body.rs')]
 bodies=''.join(p.read_text() for p in bodyfiles);assert rs.endswith(bodies)
 before=(O/'before/kernel/rust/process_helpers.rs').read_text()
 for n in names[1:]:before=before.replace('    fn '+n+'(thread: *mut c_void);'+chr(10),'',1)
 assert rs[:-len(bodies)]==before
 consumer=function(rs,'destroy_thread');beforeconsumer=function((O/'before/kernel/rust/process_helpers.rs').read_text(),'destroy_thread');assert consumer==beforeconsumer
 for n in names[1:]+['process_destroy_thread_release_tid_bridge']:assert consumer.count('Some('+n+')')==1
 helpernames=['process_tid_index_for_thread_result','process_tid_index_found_result','checked_entry_addr','process_tid_release_slot_result','process_release_tid_body_result','process_tid_log_result','thread_hash','process_list_is_linked_result','list_detach','process_list_detach_result'];helpers=''.join(function(rs,n) for n in helpernames)
 dbg=(root/'kernel/rust/debug.rs').read_text();a=dbg.index('#[repr(C)]\npub struct Ddebug');b=dbg.index('\nconst _: ()',a);dbg=dbg[a:b]
 lk=(root/'kernel/rust/lock_helpers.rs').read_text();a=lk.index('#[repr(C, align(64))]\npub struct McsRwlockNodeIrqsave');b=lk.index('\n}',a)+2;node=lk[a:b]
 destroybody=function(rs,'process_destroy_thread_body_result');sig=destroybody[:destroybody.index('{')].strip();sig=re.sub(r'^(?:#\[no_mangle\]\n)?pub unsafe extern "C" fn ','fn ',sig)+';'
 aliases=[]
 for alias in sorted(set(re.findall(r'\bProcess\w+Fn\b',sig))|{'ProcessTidLogFn'}):
  a=rs.index('type '+alias+' ');b=rs.index(';',a)+1;aliases.append(rs[a:b])
 callbacks=['process_mcs_writer_lock_bridge','process_mcs_writer_unlock_bridge','get_this_cpu_local_var','process_destroy_thread_release_tid_bridge','process_destroy_thread_replace_tid_bridge','process_spin_lock_bridge','process_spin_unlock_bridge','process_optional_free_bridge','release_fp_regs','process_release_sigcommon_bridge','process_free_thread_pages_bridge']
 declarations=chr(10).join(extern_decl(rs,n) for n in callbacks)
 prefix='#[path='+json.dumps(str(root/'kernel/rust/abi.rs'))+'] mod abi;'+chr(10)+'''use core::ffi::c_void;
use core::mem::{offset_of,size_of,MaybeUninit};
use abi::{AbiListHead,AddressSpace,CInt,CULong,Thread,ThreadHash,ResourceSet,CpuLocalVar,Process,ProcessVm,SigPending,PROCESS_HASH_SIZE};
mod debug { DDEBUG }
mod lock_helpers {use crate::abi::CULong; NODE}
use lock_helpers::McsRwlockNodeIrqsave;
const HASH_SIZE:CInt=PROCESS_HASH_SIZE as CInt;
const LIST_POISON1:usize=0x0010_0129;const LIST_POISON2:usize=0x0020_0229;
'''.replace('DDEBUG',dbg).replace('NODE',node)+chr(10).join(aliases)+chr(10)+'extern "C" {'+declarations+chr(10)+sig+chr(10)+'#[link_name="num_processors"] static mut PROCESS_NUM_PROCESSORS:CInt;'+chr(10)+'}'+chr(10)
 fixture='#![no_std]'+chr(10)+prefix+helpers+bodies+consumer;(E/'actual-integrated-consumer.rs').write_text(fixture)
 rc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc';flags=['panic=abort','opt-level=2','debuginfo=2','code-model=large','relocation-model=static','no-redzone=yes','force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no','no-vectorize-loops','no-vectorize-slp','target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
 assert run('rust-version',[rc,'--version']).startswith('rustc 1.92.0 ');run('gcc-version',['/usr/bin/gcc','--version'])
 run('actual-rust-consumer',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+[v for f in flags for v in ['-C',f]]+['--emit=obj',str(E/'actual-integrated-consumer.rs'),'-o',str(E/'rust.o')]);nm=run('actual-rust-nm',['/usr/bin/nm',str(E/'rust.o')])
 for n in names+['destroy_thread']:assert len(re.findall(r'\bT '+n+'$',nm,re.M))==1
 dis=run('actual-destroy-consumer',['/usr/bin/objdump','-dr','--disassemble=destroy_thread',str(E/'rust.o')]);code=dis[dis.index('<destroy_thread>:'):]
 for n in names[1:]+['process_destroy_thread_release_tid_bridge']:assert n in code,n
 # Real selection/declaration regions are copied from actual integrated C. The
 # minimal type environment supplies no declaration for any changed leaf.
 debug=(root/'lib/include/ihk/debug.h').read_text().replace('#include "lwk/compiler.h"','#define __aligned(n) __attribute__((aligned(n)))')
 cp=debug+'''
#include <stddef.h>
struct list_head {struct list_head *next,*prev;};
struct timespec {long tv_sec,tv_nsec;};
struct mcs_rwlock_lock {unsigned long flags[8];} __attribute__((aligned(64)));
struct mcs_rwlock_node_irqsave {unsigned long irqsave;} __attribute__((aligned(64)));
struct mcexec_tid {int tid,padding;struct thread *thread;};
struct thread_hash {struct list_head list[73];struct mcs_rwlock_lock lock[73];};
struct resource_set {unsigned char prefix[32];struct thread_hash *thread_hash;unsigned char tail[344];} __attribute__((aligned(64)));
struct cpu_local_var {unsigned char prefix[7912];struct resource_set *resource_set;unsigned char tail[208];} __attribute__((aligned(64)));
struct process {unsigned char prefix[64];struct mcs_rwlock_lock update_lock;unsigned char middle[128];struct mcexec_tid *tids;int nr_tids;unsigned char middle2[1028];struct timespec stime,utime;unsigned char tail[400];};
struct thread {struct list_head hash_list;int cpu_id,tid;unsigned char middle[4280];struct process *proc;unsigned char middle2[728];unsigned long system_tsc,user_tsc;unsigned char tail[512];} __attribute__((aligned(64)));
extern struct cpu_local_var *get_this_cpu_local_var(void);
extern int thread_hash(int);
extern int process_list_is_linked_result(const struct list_head*);
extern void process_list_detach_result(struct list_head*);
extern void mcs_rwlock_writer_lock(struct mcs_rwlock_lock*,struct mcs_rwlock_node_irqsave*);
extern void mcs_rwlock_writer_unlock(struct mcs_rwlock_lock*,struct mcs_rwlock_node_irqsave*);
extern void tsc_to_ts(unsigned long,struct timespec*);
extern void ts_add(struct timespec*,const struct timespec*);
typedef void (*process_tid_log_fn_t)(int,void*,int);
'''
 header=(root/'kernel/include/process_helpers.h').read_text();a=header.index('int process_release_tid_body_result(');b=header.index(';',a)+1;cp+=header[a:b]+chr(10)
 assert all(('void '+n+'(') not in cp for n in names)
 a=c.index('#ifndef MCKERNEL_RUST_PROCESS_HELPERS\nstatic void process_release_tid_log_bridge(');b=c.index('#endif',a)+len('#endif');chunks=[c[a:b]]
 for n in names:
  a=c.index('#ifdef MCKERNEL_RUST_PROCESS_HELPERS\nvoid '+n+'(');b=c.index('#endif',a)+len('#endif');chunks.append(c[a:b])
 actualconsumer=cfunction(c,'process_destroy_thread_release_tid_bridge');bridges=cfunction(c,'process_mcs_writer_lock_bridge')+cfunction(c,'process_mcs_writer_unlock_bridge')
 text=cp+chr(10).join(chunks)+chr(10)+actualconsumer+bridges;(E/'actual-integrated-consumer.c').write_text(text)
 cc=['/usr/bin/gcc','-O2','-Wall','-Wextra','-Werror','-Werror=implicit-function-declaration','-fno-pie','-c']
 for profile,defs in [('selected',['-DMCKERNEL_RUST_PROCESS_HELPERS']),('fallback',[])]:
  run(profile+'-consumer',cc+defs+[str(E/'actual-integrated-consumer.c'),'-o',str(E/(profile+'.o'))]);nm=run(profile+'-nm',['/usr/bin/nm',str(E/(profile+'.o'))])
  for n in names:assert len(re.findall(r'\bT '+n+'$',nm,re.M))==(0 if profile=='selected' else 1)
  if profile=='selected':assert re.search(r'\bU __release_tid$',nm,re.M)
 run('actual-selected-link',['/usr/bin/ld','-r',str(E/'selected.o'),str(E/'rust.o'),'-o',str(E/'joined.o')]);nm=run('actual-joined-nm',['/usr/bin/nm',str(E/'joined.o')])
 for n in names:assert len(re.findall(r'\bT '+n+'$',nm,re.M))==1 and not re.search(r'\bU '+n+'$',nm,re.M)
 for n in names:
  dis=run(n+'-body',['/usr/bin/objdump','-dr','--disassemble='+n,str(E/'rust.o')]);code=dis[dis.index('<'+n+'>:'):];assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',code)
 # Evidence that the fixture does not mask a missing production selected TID
 # declaration: removing only that actual line must fail real C consumer compile.
 declaration='void __release_tid(struct process *proc, struct thread *thread);';assert text.count(declaration)==1;(E/'missing-declaration-control.c').write_text(text.replace(declaration,'/* intentionally missing selected declaration */',1))
 try:run('missing-declaration-control',cc+['-DMCKERNEL_RUST_PROCESS_HELPERS',str(E/'missing-declaration-control.c'),'-o',str(E/'negative.o')])
 except AssertionError:
  row=records[-1];assert row['returncode']!=0 and row['direct_child_joined'] and not row['timed_out'];err=(E/'missing-declaration-control.stderr').read_text();assert '__release_tid' in err and 'implicit declaration' in err
 else:raise AssertionError('missing declaration control accepted')
 assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in expected.items())
 summary=dict(status='PASS_ACTUAL_INTEGRATED_CHANGED_CONSUMERS_ONLY',commands=len(records),symbols=names,actual_Rust_destroy_thread_body_compiled=True,actual_C_release_bridge_compiled=True,all_three_selected_fallbacks=True,unique_joined_exports=True,real_selected_declarations_not_injected=True,negative_missing_declaration_rejected=True,reviewed_bodies_byte_identical=True,unrelated_current_Rust_WIP_preserved=True,semantic_suites_replayed=False,full_actual_C_TU_or_real_crate=False,production_or_native_acceptance=False)
 (E/'summary.json').write_text(json.dumps(summary,indent=2)+chr(10));print(json.dumps(summary))
if __name__=='__main__':main()
