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


def main():
 E.mkdir(exist_ok=False)
 rc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
 flags=['panic=abort','opt-level=2','debuginfo=2','code-model=large','relocation-model=static','no-redzone=yes','force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no','no-vectorize-loops','no-vectorize-slp','target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
 assert run('rust-version',[rc,'--version']).startswith('rustc 1.92.0 ')
 run('gcc-version',['/usr/bin/gcc','--version'])
 for f,h in json.loads((O/'source-bindings.json').read_text()).items():assert hashlib.sha256((O/'original'/f).read_bytes()).hexdigest()==h
 orig=(O/'original/kernel/rust/process_helpers.rs').read_text();body=(O/'replace-tid-body.rs').read_text();assert (O/'candidate/kernel/rust/process_helpers.rs').read_text()==orig+body
 dbg=(O/'original/kernel/rust/debug.rs').read_text();ds=dbg[dbg.index('#[repr(C)]\npub struct Ddebug'):dbg.index('\nconst _: ()',dbg.index('pub struct Ddebug'))]
 prefix='#[path='+json.dumps(str(O/'original/kernel/rust/abi.rs'))+'] mod abi;\nuse core::ffi::c_void;\nuse core::mem::{offset_of,size_of};\nuse abi::{CInt,CULong,Process,Thread};\nmod debug { '+ds+' }\ntype ProcessTidLogFn=unsafe extern "C" fn(CInt,*mut c_void,CInt);\nextern "C" {fn kprintf(format:*const i8,...)->CInt;}\n'
 extracted=prefix+(O/'unchanged-helper-bodies.rs').read_text()+body
 (E/'extracted.rs').write_text('#![no_std]\n'+extracted)
 run('actual-leaf-object',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+[v for f in flags for v in ['-C',f]]+['--emit=obj',str(E/'extracted.rs'),'-o',str(E/'leaf.o')])
 nm=run('actual-leaf-nm',['/usr/bin/nm',str(E/'leaf.o')]);assert len(re.findall(r'\bT __find_and_replace_tid$',nm,re.M))==1
 dis=run('actual-leaf-disassembly',['/usr/bin/objdump','-dr','--disassemble=__find_and_replace_tid',str(E/'leaf.o')]);code=dis[dis.index('<__find_and_replace_tid>:'):];assert not re.search(r'\b(?:[xyz]mm\d+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',code)
 header=(O/'original/lib/include/ihk/debug.h').read_text().replace('#include "lwk/compiler.h"','#define __aligned(n) __attribute__((aligned(n)))')
 cp=header+'''\n#include <stddef.h>
 struct thread {unsigned char pad[20];int tid;};
 struct mcexec_tid {int tid;int padding;struct thread *thread;};
 struct process {unsigned char pad[256];struct mcexec_tid *tids;int nr_tids;};
 typedef void (*process_tid_log_fn_t)(int,void*,int);
 extern int process_replace_tid_body_result(void *,int,unsigned long,unsigned long,unsigned long,void *,int,int,process_tid_log_fn_t);
 '''
 c=(O/'candidate/kernel/process.c').read_text();logger=(O/'frozen-log.c').read_text();leaf=(O/'frozen-leaf.c').read_text();consumer=(O/'frozen-consumer.c').read_text()
 ls='#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+logger+'#endif\n';fs='#ifdef MCKERNEL_RUST_PROCESS_HELPERS\nvoid __find_and_replace_tid(struct process *proc, struct thread *thread, int new_tid);\n#else\n'+leaf+'#endif\n'
 assert ls in c and fs in c and consumer in c
 (E/'consumer.c').write_text(cp+ls+fs+consumer)
 cc=['/usr/bin/gcc','-O2','-Wall','-Wextra','-Werror','-Werror=implicit-function-declaration','-fno-pie','-c']
 for n,defs in [('selected',['-DMCKERNEL_RUST_PROCESS_HELPERS']),('fallback',[])]:
  run(n,cc+defs+[str(E/'consumer.c'),'-o',str(E/(n+'.o'))]);nm=run(n+'-nm',['/usr/bin/nm',str(E/(n+'.o'))]);assert re.search(r'\b'+('U' if n=='selected' else 'T')+' __find_and_replace_tid$',nm,re.M)
 run('selected-link',['/usr/bin/ld','-r',str(E/'selected.o'),str(E/'leaf.o'),'-o',str(E/'joined.o')]);nm=run('joined-nm',['/usr/bin/nm',str(E/'joined.o')]);assert len(re.findall(r'\bT __find_and_replace_tid$',nm,re.M))==1 and not re.search(r'\bU __find_and_replace_tid$',nm,re.M)
 ref=cp+logger+'\n#define __find_and_replace_tid c_reference\n'+leaf+'''\n#undef __find_and_replace_tid
 #include <stdarg.h>
 extern void record_log(const char*,const char*,int,void*,int);
 int kprintf(const char *fmt,...) {va_list a;va_start(a,fmt);const char *func=va_arg(a,const char*);int tid=va_arg(a,int);void *thread=va_arg(a,void*);int new_tid=va_arg(a,int);va_end(a);record_log(fmt,func,tid,thread,new_tid);return 0;}
 '''
 (E/'reference.c').write_text(ref);run('reference',cc+[str(E/'reference.c'),'-o',str(E/'reference.o')])
 harness=r'''
use std::ffi::CStr;
use abi::McexecTid;
static mut EVENTS:Vec<(i32,usize,i32,Vec<(i32,usize)>)>=Vec::new();
static mut SLOTS:*mut McexecTid=std::ptr::null_mut();
static mut LEN:usize=0;
extern "C" {fn c_reference(p:*mut Process,t:*mut Thread,n:i32);static mut __start___verbose:debug::Ddebug;static mut __stop___verbose:debug::Ddebug;}
#[no_mangle] unsafe extern "C" fn record_log(fmt:*const i8,func:*const i8,tid:i32,t:*mut c_void,new_tid:i32) {
 assert_eq!(CStr::from_ptr(fmt).to_bytes(),b"%s: tid %d (thread %p) has been relaced with tid %d\n");assert_eq!(CStr::from_ptr(func).to_bytes(),b"__find_and_replace_tid");
 let slots=std::slice::from_raw_parts(SLOTS,LEN).iter().map(|s|(s.tid,s.thread as usize)).collect();EVENTS.push((tid,t as usize,new_tid,slots));
}
unsafe fn set_debug(on:bool) {let mut p=&raw mut __start___verbose;let e=&raw mut __stop___verbose;let mut count=0;while p<e {assert!((*p).fmt.is_null());assert_eq!(CStr::from_ptr((*p).func).to_bytes(),b"process_replace_tid_log_bridge");(*p).line_flags=((*p).line_flags&0x00ff_ffff)|((on as u32)<<24);count+=1;p=p.add(1);}assert_eq!(count,2);}
fn main(){unsafe{
 let mut count=0;
 for on in [false,true] {set_debug(on);for old_tid in [0,37,i32::MAX,i32::MIN] {for new_tid in [0,37,i32::MAX,i32::MIN] {for case in 0..8 {
  let mut traces=Vec::new();
  let mut thread=Box::<Thread>::new_uninit();let tp=thread.as_mut_ptr();std::ptr::addr_of_mut!((*tp).tid).write(old_tid);
  let mut proc=Box::<Process>::new_uninit();let pp=proc.as_mut_ptr();
  let pattern:Vec<bool>=match case {0=>vec![],1=>vec![true],2=>vec![false,true,false],3=>vec![false,false],4=>vec![true,false,true],5=>vec![true],6=>vec![true],_=>vec![false,true]};
  for rust in [false,true] {
   // All numeric TIDs match old_tid: lookup must still match ownership pointer.
   let mut slots:Vec<McexecTid>=pattern.iter().map(|b|McexecTid{tid:old_tid,padding:0x1234abcd,thread:if *b {tp}else{0xfedcba9876543200usize as *mut Thread}}).collect();
   SLOTS=slots.as_mut_ptr();LEN=slots.len();let null_tids=case==5;let nr=if case==6 {-1}else if case==7 {1}else{slots.len() as i32};std::ptr::addr_of_mut!((*pp).tids).write(if null_tids {std::ptr::null_mut()}else{SLOTS.cast()});std::ptr::addr_of_mut!((*pp).nr_tids).write(nr);
   let mut expected:Vec<(i32,usize)>=slots.iter().map(|s|(s.tid,s.thread as usize)).collect();let mut expectedlogs=Vec::new();EVENTS.clear();
   for _ in 0..3 {
    if !null_tids&&nr>0 {if let Some(i)=expected[..nr as usize].iter().position(|p|p.1==tp as usize) {expected[i]=(new_tid,0);if on {expectedlogs.push((old_tid,tp as usize,new_tid,expected.clone()));}}}
    if rust {__find_and_replace_tid(pp,tp,new_tid)}else{c_reference(pp,tp,new_tid)}
    assert_eq!(slots.iter().map(|s|(s.tid,s.thread as usize)).collect::<Vec<_>>(),expected);assert_eq!(EVENTS,expectedlogs);
    assert_eq!((*tp).tid,old_tid);assert_eq!((*pp).nr_tids,nr);assert_eq!((*pp).tids,if null_tids {std::ptr::null_mut()}else{SLOTS.cast()});
    for s in &slots {assert_eq!(s.padding,0x1234abcd);}
   }
   traces.push(format!("{:?}:{:?}",expected,EVENTS));
  }
  assert_eq!(traces[0],traces[1]);count+=1;
 }}}}
 println!("PASS {} actual C/Rust leaf cases, three replacements each, first-match ownership, callback-after-pointer-clear-and-TID-write, unchanged thread/padding, nulltable/nonpositive/boundedcount",count);
}}
'''
 (E/'parity.rs').write_text(extracted+harness)
 run('parity-compile',[rc,'--edition=2021','-Awarnings','-C','opt-level=2',str(E/'parity.rs'),'-C','link-arg='+str(E/'reference.o'),'-C','link-arg=-no-pie','-o',str(E/'parity')])
 out=run('parity-run',[str(E/'parity')]);assert 'PASS 256 actual C/Rust leaf cases' in out
 (E/'summary.json').write_text(json.dumps(dict(status='PASS_PRIVATE_EXTRACTED_LEAF_ONLY',cases=256,replacements_each=3,commands=len(records),shared_helpers='Both C and Rust leaves use exact unchanged selected Rust helpers',actual_C_reference=True,selected_fallback_fixture=True,unique_linked_leaf=True,full_production_crate=False,actual_C_layout_proof=False,production_or_native=False),indent=2)+'\n')
 print('PASS focused private __find_and_replace_tid candidate; 256 cases; no production/native claim')

if __name__=='__main__':main()
