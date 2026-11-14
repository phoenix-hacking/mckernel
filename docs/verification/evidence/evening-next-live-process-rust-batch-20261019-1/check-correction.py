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
 source=(O/'checks-1/parity.rs').read_text()
 assert source.count(' let order=match shape')==1
 corrected=source.replace(' let order=match shape',' let mut order=match shape')
 (E/'parity.rs').write_text(corrected)
 rc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
 run('parity-compile-correction',[rc,'--edition=2021','-Awarnings','-C','opt-level=2',str(E/'parity.rs'),'-C','link-arg='+str(O/'checks-1/reference.o'),'-C','link-arg=-no-pie','-o',str(E/'parity')])
 out=run('parity-run',[str(E/'parity')]);assert 'PASS 468 ' in out
 prior=json.loads((O/'checks-1/commands.json').read_text())
 assert len(prior)==17 and all(r['returncode']==0 for r in prior[:-1]) and prior[-1]['label']=='parity-compile' and prior[-1]['returncode']==1
 summary=dict(status='PASS_PRIVATE_TWO_LIVE_CALLBACKS',cases=468,leaf_calls=3744,commands_total=len(prior)+len(records),commands_passed=len(prior)-1+len(records),preserved_failed_command='checks-1/parity-compile.status.json',actual_C_reference=True,selected_fallback_fixture=True,real_Rust_default_consumer=True,unique_linked_leaves=2,full_production_crate=False,actual_C_layout_proof=False,native_retirement=False)
 (E/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print('PASS private two live release callbacks;468 scenarios;3744 leaf calls;no production/native claim')
if __name__=='__main__':main()
