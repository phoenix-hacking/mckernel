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
 flags=['panic=abort','opt-level=2','debuginfo=2','code-model=large','relocation-model=static','no-redzone=yes','force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no','no-vectorize-loops','no-vectorize-slp','target-feature=-sse,-sse2,-sse3,-ssse3,-ssse4.1,-ssse4.2,-avx,-avx2,-fma']
 assert run('rust-version',[rc,'--version']).startswith('rustc 1.92.0 ')
 run('gcc-version',['/usr/bin/gcc','--version'])
 orig=(O/'original/kernel/rust/process_helpers.rs').read_text();candidate=(O/'candidate/kernel/rust/process_helpers.rs').read_text();body=(O/'new-bodies.rs').read_text()
 assert candidate.endswith(body)
 for name in ['process_release_hash_detach_bridge','process_release_sibling_detach_bridge']:
  assert '    fn '+name+'(' in orig and '    fn '+name+'(' not in candidate
 abi=O/'original/kernel/rust/abi.rs'
 prefix='#[path='+json.dumps(str(abi))+'] mod abi;\nuse core::ffi::c_void;\nuse core::mem::{offset_of,size_of,MaybeUninit};\nuse abi::{AbiListHead,CInt,CULong,Process,ProcessHash,ResourceSet,McsRwlockLock,PROCESS_HASH_SIZE,Mckfd};\n#[repr(C,align(64))] struct McsRwlockNodeIrqsave {irqsave:CULong}\nconst HASH_SIZE:CInt=PROCESS_HASH_SIZE as CInt;\nconst LIST_POISON1:usize=0x100129;const LIST_POISON2:usize=0x200229;\n'
 callbackdecl='unsafe extern "C" {fn process_mcs_writer_lock_bridge(lock:CULong,node:*mut c_void);fn process_mcs_writer_unlock_bridge(lock:CULong,node:*mut c_void); }\n'
 helpers=(O/'unchanged-helpers.rs').read_text()
 # Exact unchanged exported helpers accompany the actual candidate bodies.
 exported=helpers.replace('pub extern "C" fn process_hash','#[no_mangle]\npub extern "C" fn process_hash').replace('pub unsafe extern "C" fn process_list_', '#[no_mangle]\npub unsafe extern "C" fn process_list_')
 extracted=prefix+callbackdecl+exported+body
 (E/'extracted.rs').write_text('#![no_std]\n'+extracted)
 rf=[v for f in flags for v in ['-C',f]]
 run('leaf-object',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+rf+['--emit=obj',str(E/'extracted.rs'),'-o',str(E/'leaf.o')])
 names=['process_release_hash_detach_bridge','process_release_sibling_detach_bridge']
 for i,n in enumerate(names):
  nm=run('leaf-nm-'+str(i),['/usr/bin/nm',str(E/'leaf.o')]);assert len(re.findall(r'\bT '+n+'$',nm,re.M))==1
  dis=run('leaf-disassembly-'+str(i),['/usr/bin/objdump','-dr','--disassemble='+n,str(E/'leaf.o')]);code=dis[dis.index('<'+n+'>:'):];assert not re.search(r'\b(?:[xyz]mm\d+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',code)
 cc=['/usr/bin/gcc','-O2','-Wall','-Wextra','-Werror','-Werror=implicit-function-declaration','-fno-pie','-c']
 run('c-reference',cc+[str(O/'reference.c'),'-o',str(E/'reference.o')])
 for label,defs in [('selected',['-DMCKERNEL_RUST_PROCESS_HELPERS']),('fallback',[])]:
  run('c-consumer-'+label,cc+defs+[str(O/'consumer.c'),'-o',str(E/(label+'.o'))]);nm=run('c-nm-'+label,['/usr/bin/nm',str(E/(label+'.o'))]);
  for n in names:assert bool(re.search(r'\bT '+n+'$',nm,re.M))==(label=='fallback')
 # The actual Rust default release_process body resolves both newly local leaves.
 consumer=extracted+(O/'consumer-support.rs').read_text()+(O/'frozen-rust-consumer.rs').read_text()
 (E/'consumer.rs').write_text('#![no_std]\n'+consumer)
 run('rust-default-consumer',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+rf+['--emit=obj',str(E/'consumer.rs'),'-o',str(E/'consumer.o')])
 dis=run('rust-default-consumer-disassembly',['/usr/bin/objdump','-dr','--disassemble=release_process',str(E/'consumer.o')])
 for n in names:assert n in dis
 run('selected-unique-link',['/usr/bin/ld','-r',str(E/'selected.o'),str(E/'consumer.o'),'-o',str(E/'joined.o')])
 nm=run('joined-nm',['/usr/bin/nm',str(E/'joined.o')])
 for n in names:assert len(re.findall(r'\bT '+n+'$',nm,re.M))==1 and not re.search(r'\bU '+n+'$',nm,re.M)
 (E/'parity.rs').write_text(extracted.replace(callbackdecl,'')+(O/'harness.rs').read_text())
 run('parity-compile',[rc,'--edition=2021','-Awarnings','-C','opt-level=2',str(E/'parity.rs'),'-C','link-arg='+str(E/'reference.o'),'-C','link-arg=-no-pie','-o',str(E/'parity')])
 out=run('parity-run',[str(E/'parity')]);assert 'PASS 468' in out
 (E/'summary.json').write_text(json.dumps(dict(status='PASS_PRIVATE_TWO_LIVE_CALLBACKS',cases=468,commands=len(records),actual_C_reference=True,selected_fallback_fixture=True,real_Rust_default_consumer=True,unique_linked_leaves=2,full_production_crate=False,actual_C_layout_proof=False,native_retirement=False),indent=2)+'\n')
 print('PASS private two live release callbacks; 468 cases; no production/native claim')
if __name__=='__main__':main()
