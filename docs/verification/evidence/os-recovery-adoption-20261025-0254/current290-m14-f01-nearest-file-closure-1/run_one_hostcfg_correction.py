"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One Root-granted HOST-cfg correction only; reuse seven passed prefixes.
"""
import hashlib,importlib.util,json,os,pathlib,re,resource,signal,struct,subprocess,sys,time
E=pathlib.Path(__file__).resolve().parent;D=E.parent
G=D/'m14-f06-selected-residual-implementation-20261026-1/next-process-vm-selected-1/next-prctl-getter-selected-1/actual-host-getter-1/reviewed-account-supervisor-correction-1'
S=pathlib.Path(json.load(open(D/'current290-unprivileged-build-only-source-1/PROFILE.SOURCE-ONLY.json'))['inputs']['source6153'])
R=pathlib.Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/nightly-2026-02-19-x86_64-unknown-linux-gnu/bin/rustc')
def ref(p):
 p=pathlib.Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def verify(rows):
 for row in rows:assert ref(row['path'])==row,'input drift:'+row['path']
class Elf:
 def __init__(self,p):
  self.b=pathlib.Path(p).read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',self.b);assert self.b[:6]==b'\x7fELF\x02\x01';self.sections=[]
  for i in range(h[12]):
   z=struct.unpack_from('<IIQQQQIIQQ',self.b,h[6]+i*h[11]);self.sections.append(dict(nameoff=z[0],type=z[1],addr=z[3],off=z[4],size=z[5],link=z[6],entsize=z[9]))
  st=self.sections[h[13]];names=self.b[st['off']:st['off']+st['size']]
  for s in self.sections:s['name']=names[s['nameoff']:].split(b'\0')[0].decode()
  self.symbols=[]
  for s in self.sections:
   if s['type']!=2:continue
   ns=self.sections[s['link']];names=self.b[ns['off']:ns['off']+ns['size']]
   for n in range(0,s['size'],s['entsize']):
    no,info,other,ndx,value,size=struct.unpack_from('<IBBHQQ',self.b,s['off']+n);self.symbols.append(dict(name=names[no:].split(b'\0')[0].decode(),type=info&15,bind=info>>4,ndx=ndx,value=value,size=size))
 def funcs(self):return {s['name']:s for s in self.symbols if s['type']==2 and s['ndx']}
def origin_proof(obj,exe,mapfile,out):
 host=Elf(obj);final=Elf(exe);hf=host.funcs();ef=final.funcs();fixture=(E/'existing-focused-inputs/mem_init_helpers_equiv.c').read_text();names={n for n in re.findall(r'\b(?:mem_[A-Za-z0-9_]+|rusage_[A-Za-z0-9_]+|ihk_mc_clear_dump_page_completion)\s*(?=\()',fixture) if n in hf and n in ef};assert 'mem_rusage_init_body_result' in names and 'mem_query_mem_areas_result' in names
 text=mapfile.read_text();text=text.split('Linker script and memory map',1)[1].split('Cross Reference Table',1)[0];lines=text.splitlines();entries=[];pending=None
 for line in lines:
  m=re.match(r'^\s+(\.[^\s]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.+?)\s*$',line)
  if m:entries.append((m[1],int(m[2],16),int(m[3],16),m[4]));pending=None;continue
  m=re.match(r'^\s+(\.[^\s]+)\s*$',line)
  if m:pending=m[1];continue
  m=re.match(r'^\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.+?)\s*$',line)
  if pending and m:entries.append((pending,int(m[1],16),int(m[2],16),m[3]));pending=None
 rows=[]
 for n in sorted(names):
  hs=hf[n];fs=ef[n];section=host.sections[hs['ndx']]['name'];matching=[x for x in entries if x[0]==section and x[3]==str(obj) and x[2]>0];assert len(matching)==1,('host inputsection missing/ambiguous',n,section,matching)
  sec,base,size,provider=matching[0];assert fs['value']==base+hs['value'],('Cstub masks testedRust',n,hex(fs['value']),hex(base+hs['value']))
  rows.append(dict(name=n,provider=provider,section=section,host_value=hs['value'],linked_value=hex(fs['value']),exact_origin=True))
 out.write_text(json.dumps(dict(status='PASS_EXACT_TESTED_F01_RUST_INPUTSECTION_AND_FINAL_SYMBOL_ADDRESSES',functions=rows,source=ref(E/'existing-focused-inputs/mem_init_helpers_equiv.c')),indent=2)+'\n');return len(rows)
def main():
 os.sched_setaffinity(0,{6})
 for k,v in [(resource.RLIMIT_AS,2*2**30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,64*2**20),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 assert ref(G/'run_sealed.py')['sha256']=='e8b84de39128433542b213fc3a374dd50d3e12f232bd397dddaa24859349a805'
 sys.path.insert(0,str(G));spec=importlib.util.spec_from_file_location('f01_correction_guard',G/'run_sealed.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 pins=json.load(open(E/'HOSTCFG-CORRECTION-PINS.json'));verify(pins['inputs']+pins['tools']);initial=guard.admission();A=E/'actual-hostcfg-correction-1';A.mkdir(mode=0o700);logs=A/'logs';logs.mkdir(mode=0o700);obj=A/'mckernel_rust.HOST-EQUIVALENCE.o';exe=A/'mem_init_helpers_rust';mp=A/'Rust.map';prefix=E/'actual-focused-attempt-1/output';f=E/'existing-focused-inputs'
 commands=[['/usr/bin/env','MCKERNEL_RUST_VERSION=equiv-version','MCKERNEL_RUST_BUILDID=equiv-buildid',str(R),'--crate-name','mckernel_rust','--crate-type','lib','--edition=2021','--cfg','mckernel_equivalence','--cfg','enable_rusage','-C','panic=abort','-C','opt-level=2','-C','debuginfo=2','-C','code-model=large','-C','relocation-model=static','-C','no-redzone=yes','-C','force-frame-pointers=yes','-C','overflow-checks=off','-C','force-unwind-tables=no','-C','no-vectorize-loops','-C','no-vectorize-slp','-C','target-feature=-sse,-sse2,-sse3,-ssse3,-ssse4.1,-sse4.2,-avx,-avx2,-fma','--emit=obj='+str(obj),'kernel/rust/lib.rs'],['/usr/bin/objcopy','--weaken-symbol=main',str(obj)],['/usr/bin/gcc-9','-Wl,-Map='+str(mp),'-Wl,--cref','-no-pie','-fno-builtin','-Wl,--gc-sections','-Wl,--allow-multiple-definition',str(f/'mem_init_helpers_equiv.c'),str(f/'rust_stubs.c'),str(obj),'-o',str(exe)],[str(prefix/'mem_init_helpers_c')],[str(exe)],['/usr/bin/diff','-u',str(A/'C.stdout'),str(A/'Rust.stdout')]]
 assert all('MEM_INIT_C_FALLBACK' not in x for x in commands[2]);assert hashlib.sha256((S/'kernel/rust/mem_helpers.rs').read_bytes()).hexdigest()==json.load(open(E/'F01-FOCUSED-PROOF-JOIN.json'))['selected_source']['sha256']
 # Existing stub source contains no tested rusage/dump entry names at all.
 stubs=(f/'rust_stubs.c').read_text();tested=['mem_rusage_init_body_result','mem_clear_dump_page_completion_result','mem_dump_free_pages_public_result','mem_dump_first_free_chunk_public_result','mem_dump_next_free_chunk_result','mem_dump_chunk_addr_result','mem_dump_chunk_size_result','mem_query_mem_areas_result'];assert not [n for n in tested if re.search(r'\b'+n+r'\b',stubs)]
 results=[];failure=None;origins=None
 try:
  for index,cmd in enumerate(commands):
   verify(pins['inputs']+pins['tools']);admission=guard.admission();wall=time.time();start=time.monotonic();stdoutfile=A/('C.stdout' if index==3 else 'Rust.stdout') if index in (3,4) else logs/(str(index)+'.stdout')
   with stdoutfile.open('xb') as out,(logs/(str(index)+'.stderr')).open('xb') as err:
    child=subprocess.Popen(cmd,cwd=S,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,env={'PATH':'/usr/bin:/bin','LC_ALL':'C','RUST_BACKTRACE':'0'})
    while True:
     pid,status,u=os.wait4(child.pid,os.WNOHANG)
     if pid:break
     if time.monotonic()-start>=90:os.killpg(child.pid,signal.SIGKILL);pid,status,u=os.wait4(child.pid,0);break
     time.sleep(.01)
    child.returncode=os.waitstatus_to_exitcode(status)
   try:os.killpg(child.pid,0);absent=False
   except ProcessLookupError:absent=True
   row=dict(index=index,argv=cmd,purpose=__doc__.strip(),pid=child.pid,started_wall=wall,elapsed=time.monotonic()-start,returncode=child.returncode,CPU_user=u.ru_utime,CPU_system=u.ru_stime,max_RSS_KiB=u.ru_maxrss,direct_wait=True,group_absent=absent,admission=admission,stdout=ref(stdoutfile),stderr=ref(logs/(str(index)+'.stderr')));results.append(row);(A/'RESULTS.json').write_text(json.dumps(dict(status='RUNNING',results=results),indent=2)+'\n')
   if child.returncode or not absent:raise RuntimeError('ONE correction firstfailure command'+str(index))
   if index==2:origins=origin_proof(obj,exe,mp,A/'EXACT-F01-PROVIDER-ORIGINS.json')
 except BaseException as exc:failure=repr(exc)
 final=dict(scope=__doc__.strip(),status='FAIL_ONE_CORRECTION_STOPPED' if failure else 'PASS_EXISTING_FOCUSED_HOST_EQUIVALENCE_EXACT_COMPARATOR_AND_RUST_ORIGINS',initial_admission=initial,pins=ref(E/'HOSTCFG-CORRECTION-PINS.json'),results=results,failure=failure,exact_Rust_provider_origin_count=origins,first_compiler_timestamp=results[0]['started_wall'] if results else None,production_object_mutated=False,old_seven_passed_prefix_replayed=False,reference_C_executable_reused=True,HOSTcfgdistinctfromProductionNative=True,whole_file_acceptance=False)
 (A/'RESULTS.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(dict(status=final['status'],commands=len(results),failure=failure,origins=origins,all_joined=all(x['direct_wait'] and x['group_absent'] for x in results))))
 if failure:sys.exit(1)
if __name__=='__main__':main()
