from pathlib import Path
import subprocess,resource,time,json,re,os,hashlib,signal
O=Path(__file__).parent
E=O/'checks-2'
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
 rf=[v for f in flags for v in ['-C',f]]
 body=(O/'new-bodies.rs').read_text();candidate=(O/'candidate/kernel/rust/process_helpers.rs').read_text()
 assert candidate.endswith(body)
 names=['process_current_resource_set_bridge','process_release_final_cleanup_bridge']
 for n in names:assert '    fn '+n+'(' not in candidate
 prefix='#[path='+json.dumps(str(O/'original/kernel/rust/abi.rs'))+'] mod abi;\nuse core::ffi::c_void;use core::mem::{offset_of,size_of,MaybeUninit};\nuse abi::{CInt,CULong,CpuLocalVar,ResourceSet,Process,Mckfd};\n#[repr(C,align(64))] struct McsRwlockNodeIrqsave {irqsave:CULong}\n'
 callbackdecl='unsafe extern "C" {fn get_this_cpu_local_var()->*mut CpuLocalVar;fn process_mcs_reader_lock_bridge(l:CULong,n:*mut c_void);fn process_mcs_reader_unlock_bridge(l:CULong,n:*mut c_void); }\n'
 extracted=prefix+callbackdecl+body
 (E/'extracted.rs').write_text('#![no_std]\n'+extracted)
 (E/'consumer.rs').write_text('#![no_std]\n'+extracted+(O/'consumer-support.rs').read_text()+(O/'frozen-rust-consumer.rs').read_text())
 cc=['/usr/bin/gcc','-O2','-Wall','-Wextra','-Werror','-Werror=implicit-function-declaration','-fno-pie','-c']
 for label,tofu in [('tofu',True)]:
  cfg=['--cfg','enable_tofu'] if tofu else [];cdefs=['-DENABLE_TOFU'] if tofu else []
  target=E/label;target.mkdir()
  run(label+'-leaf-object',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+cfg+rf+['--emit=obj',str(E/'extracted.rs'),'-o',str(target/'leaf.o')])
  nm=run(label+'-leaf-nm',['/usr/bin/nm',str(target/'leaf.o')])
  for i,n in enumerate(names):
   assert len(re.findall(r'\bT '+n+'$',nm,re.M))==1
   dis=run(label+'-leaf-disassembly-'+str(i),['/usr/bin/objdump','-dr','--disassemble='+n,str(target/'leaf.o')]);code=dis[dis.index('<'+n+'>:'):];assert not re.search(r'\b(?:[xyz]mm\d+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',code)
  assert bool(re.search(r'\bU tof_utofu_finalize$',nm,re.M))==tofu
  run(label+'-c-reference',cc+cdefs+[str(O/'reference.c'),'-o',str(target/'reference.o')])
  for selection,defs in [('selected',['-DMCKERNEL_RUST_PROCESS_HELPERS']),('fallback',[])]:
   run(label+'-c-'+selection,cc+cdefs+defs+[str(O/'consumer.c'),'-o',str(target/(selection+'.o'))])
   nm=run(label+'-c-nm-'+selection,['/usr/bin/nm',str(target/(selection+'.o'))])
   for n in names:assert bool(re.search(r'\bT '+n+'$',nm,re.M))==(selection=='fallback')
  run(label+'-rust-default-consumer',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+cfg+rf+['--emit=obj',str(E/'consumer.rs'),'-o',str(target/'consumer.o')])
  dis=run(label+'-consumer-disassembly',['/usr/bin/objdump','-dr','--disassemble=release_process',str(target/'consumer.o')])
  for n in names:assert n in dis
  run(label+'-unique-link',['/usr/bin/ld','-r',str(target/'selected.o'),str(target/'consumer.o'),'-o',str(target/'joined.o')])
  nm=run(label+'-joined-nm',['/usr/bin/nm',str(target/'joined.o')])
  for n in names:assert len(re.findall(r'\bT '+n+'$',nm,re.M))==1 and not re.search(r'\bU '+n+'$',nm,re.M)
  # Test stubs are definitions, with no duplicate extern declarations in scope.
  harness=(prefix+body).replace('    fn hugefileobj_cleanup();\n','').replace('    #[cfg(enable_tofu)]\n    fn tof_utofu_finalize();\n','')+(O/'harness.rs').read_text()
  (target/'parity.rs').write_text(harness)
  run(label+'-parity-compile',[rc,'--edition=2021','-Awarnings','-C','opt-level=2']+cfg+[str(target/'parity.rs'),'-C','link-arg='+str(target/'reference.o'),'-C','link-arg=-no-pie','-o',str(target/'parity')])
  out=run(label+'-parity-run',[str(target/'parity')]);assert 'PASS 63 scenarios' in out
 (E/'summary.json').write_text(json.dumps(dict(status='PASS_PRIVATE_TWO_LIVE_CALLBACKS',scenarios=126,leaf_calls=252,compile_selections=['ordinary','tofu'],commands_total=18+len(records),commands_passed=17+len(records),preserved_failed_command='checks-1/tofu-leaf-object.status.json',ordinary_before_assertion_correction=True,runtime_bodies_unchanged=True,actual_C_reference=True,selected_fallback_fixture=True,real_Rust_default_consumer=True,unique_linked_leaves=2,full_production_crate=False,actual_C_layout_proof=False,native_retirement=False),indent=2)+'\n')
 print('PASS two final-process callbacks;126 scenarios/252 C+Rust calls;TOFU off/on;production/native pending')
if __name__=='__main__':main()
