"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,re,time
D=Path(__file__).resolve().parent;REPO=Path('/home/holden/mckernel');E=REPO/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-3/ordinary-selected-memory-callback3-1'
PRIOR=REPO/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/phys-to-virt-callback-1/PREPARED-COMMANDS.NOT-EXECUTED.json'
RUST=D.parent/'ordinary-fullcrate-callback3-1/build/mckernel_rust.o'
SCOPE=__doc__
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
assert sha(RUST)=='a125e872882f8a90e44ba28d344b1d751942732992ea620fe133ba63587963b4'
src=REPO/'arch/x86_64/kernel/memory.c';assert sha(src)=='49244e64283fa51f4ab7a9eed42a388934a9227b640657d34a7eca4d8f18136b'
source=D/'memory.c';source.write_bytes(src.read_bytes());obj=D/'memory.c.o';partial=D/'selected-consumer-provider.o'
old=json.loads(PRIOR.read_text());pre=old['preprocess'][:];pre[-1]=str(source)
cc=old['whole_C_TU'][:];cc[-1]=str(source);cc[cc.index('-o')+1]=str(obj)
commands=[('preprocess',pre),('whole-C-TU',cc),('C-symbols',['/usr/bin/nm','-a',str(obj)]),('relocations',['/usr/bin/readelf','-rW',str(obj)]),('partial-link',['/usr/bin/ld','-r',str(obj),str(RUST),'-o',str(partial)]),('partial-symbols',['/usr/bin/nm','-g',str(partial)])]
helperpath=REPO/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py';assert sha(helperpath)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('accepted',helperpath);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
os.sched_setaffinity(0,{6})
for kind,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(kind,(value,value))
os.chdir(D);start=time.monotonic();results=[];captures={};status='FAIL_STOP_RETAIN_EVIDENCE';error=None
write(D/'SOURCE-BINDINGS.json',{'scope':SCOPE,'canonical_memory':{'path':str(src),'sha256':sha(src)},'private_memory':{'path':str(source),'sha256':sha(source)},'Rust_object':{'path':str(RUST),'sha256':sha(RUST),'bytes':RUST.stat().st_size},'prior_commands':{'path':str(PRIOR),'sha256':sha(PRIOR)},'headers':'Exact unchanged include roots from prior accepted GCC9 full-TU profile; no new stubs/includes/flags.','proof_scope':'Host GCC9 full C TU and actual accepted fullRust object partial link only; GCC14/finalimage/native remain open.'})
try:
 for label,argv in commands:
  cap=D/(label+'-capture-1');cap.mkdir();command={'argv':argv,'purpose':SCOPE,'shell':False};write(cap/'command.json',command);j=h.owned_capture(command,cap,90,lambda:None);write(cap/'whole-join.json',j);results.append({'label':label,'whole_join':j});captures[label]=(cap/'stdout').read_text()
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'],'first failed command: '+label
  if label=='preprocess':
   assert 'extern int x86_clear_page_unmap_bridge(void *page);' in captures[label]
   assert not re.search(r'\bx86_clear_page_unmap_bridge\s*\([^;{}]*\)\s*\{',captures[label],re.S)
  if label=='C-symbols':
   rows=[line.split() for line in captures[label].splitlines() if line.split()[-1:] == ['x86_clear_page_unmap_bridge']];assert len(rows)==1 and rows[0][-2]=='U',rows
  if label=='relocations':assert 'x86_clear_page_unmap_bridge' in captures[label]
  if label=='partial-symbols':
   rows=[line.split() for line in captures[label].splitlines() if line.split()[-1:] == ['x86_clear_page_unmap_bridge']];assert len(rows)==1 and rows[0][-2]=='T',rows
 status='PASS_SELECTED_GCC9_FULL_TU_AND_ACTUAL_RUST_FULLCRATE_PARTIAL_LINK'
except BaseException as exc:error=repr(exc)
result={'scope':SCOPE,'status':status,'error':error,'seconds':time.monotonic()-start,'commands':results,'memory_object':h.hashed(obj,32<<20) if obj.exists() else None,'partial_object':h.hashed(partial,32<<20) if partial.exists() else None,'Rust_object_unchanged':sha(RUST)=='a125e872882f8a90e44ba28d344b1d751942732992ea620fe133ba63587963b4','callback_relocation_lines':[l for l in captures.get('relocations','').splitlines() if 'x86_clear_page_unmap_bridge' in l],'public_page_unmap_remaining_unresolved':[l for l in captures.get('partial-symbols','').splitlines() if l.split()[-1:]==['page_unmap']],'production_GCC14':False,'final_image_link':False,'native':False,'file_or_area_retirement':False,'first_failure_stops':True}
write(D/'RESULT.json',result)
for q in D.rglob('*'):
 if q.is_file() and q.suffix!='.o':
  target=E/q.relative_to(D);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(q.read_bytes())
print(json.dumps({'status':status,'error':error,'seconds':result['seconds'],'commands':len(results),'relocations':result['callback_relocation_lines'],'page_unmap':result['public_page_unmap_remaining_unresolved']}))
