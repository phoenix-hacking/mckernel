"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,time,re
E=Path('/home/holden/mckernel/docs/verification/evidence/compute-idle-rust-cutover-20261023-1/page-unmap-body-1/production-consumer-1');R=Path('/home/holden/mckernel');D=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/page-unmap-body-1/production-consumer-1')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def types(text,name):return [line.split()[-2] for line in text.splitlines() if line.split()[-1:]==[name]]
def main():
 start=time.monotonic();os.sched_setaffinity(0,{0});os.environ['RUST_MIN_STACK']='2097152'
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 helper=R/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py';raw=helper.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 nodes=[]
 for node in ast.parse(raw).body:
  if isinstance(node,(ast.Import,ast.ImportFrom)):nodes.append(node)
  elif isinstance(node,ast.FunctionDef) and node.name in {'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}:nodes.append(node)
  elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'} for t in node.targets):nodes.append(node)
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
 signal.setitimer(signal.ITIMER_REAL,90)
 assert sha(E/'PREPARED-COMMANDS.json')=='eee05a3cc909c6f1cd723db57622d51e139cd104ef4bad5a18b09ab085c03b39'
 c=json.loads((E/'PREPARED-COMMANDS.json').read_text());bind=json.loads((E/'SOURCE-BINDINGS.json').read_text())
 for row in bind['inputs'].values():assert sha(Path(row['path']))==row['sha256']
 assert sha(Path(c['fullcrate']['argv'][6]))=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 assert os.statvfs(D).f_bavail*os.statvfs(D).f_frsize>=16*2**30+(128<<20) and os.statvfs('/home/holden/mckernel-work/scratch').f_bavail*os.statvfs('/home/holden/mckernel-work/scratch').f_frsize>=12*2**30
 results=[];out={};error=None;status='FAIL_FIRST_COMMAND_OR_ASSERTION_RETAINED';build=D/'build';rust=build/'mckernel_rust.o';mem=build/'mem.c.o';part=build/'partial.o'
 def run(label,command):
  assert time.monotonic()-start<84
  cap=D/'correction1'/(label+'-capture-1');cap.mkdir(mode=0o700);cmd=dict(command,purpose=__doc__,shell=False);write(cap/'command.json',cmd);os.chdir(cmd.get('cwd',str(build)))
  j=ns['owned_capture'](cmd,cap,max(1,84-(time.monotonic()-start)),lambda:None);write(cap/'whole-join.json',j);results.append(dict(label=label,whole_join=j));out[label]=(cap/'stdout').read_text()
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'],'first failure '+label
  return out[label]
 geometry=['page_unmap_hash_shift','page_unmap_hash_mask','page_unmap_lock_stride'];callbacks=['page_hash_lock_bridge','page_hash_unlock_bridge','page_unmap_log_bridge'];imports=geometry+callbacks+['page_hash_locks'];exports={};geometry_sizes={}
 try:
  assert sha(rust)=='2dd241e13d7d4293660eaf5d5f23ee0af5166a2265ca543c20e8e150c27a57d9' and sha(mem)=='d53cf2a1135ab74fcfc67a811ac5abecb5b0f20582537b5bfee6a5e1b2deaab1';rust_before=sha(rust)
  text=(D/'Rust-symbols-capture-1/stdout').read_text();prior=json.loads((R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-4/RESULT.json').read_text())['exports'];expected=list(prior)+['page_unmap'];assert len(expected)==13
  exports={n:types(text,n) for n in expected};assert all(v==['T'] for v in exports.values())
  assert all(types(text,n)==['U'] for n in imports)
  pp=(D/'preprocess-capture-1/stdout').read_text();assert not re.search(r'\bint\s+page_unmap\s*\([^;{}]*\)\s*\{',pp,re.S);assert re.search(r'\bint\s+page_unmap\s*\([^;{}]*\)\s*;',pp,re.S)
  symbols=(D/'C-symbols-capture-1/stdout').read_text();assert 'T' not in types(symbols,'page_unmap')
  assert all(types(symbols,n)==['T'] for n in callbacks) and types(symbols,'page_hash_locks') in (['B'],['C'])
  for name,size in zip(geometry,[4,8,8]):
   entries=[l.split() for l in symbols.splitlines() if l.split()[-1:]==[name]];assert len(entries)==1 and entries[0][-2]=='R' and int(entries[0][1],16)==size;geometry_sizes[name]=size
  rel=run('Rust-relocations',dict(argv=['/usr/bin/objdump','-dr','--disassemble=page_unmap',str(rust)]));assert all(n in rel for n in imports)
  run('partial-link',c['partial_link']);joined=run('partial-symbols',dict(argv=['/usr/bin/nm','-S','-g',str(part)]));assert types(joined,'page_unmap')==['T'];assert all(types(joined,n)==['T'] for n in callbacks) and types(joined,'page_hash_locks') in (['B'],['C']) and all(types(joined,n)==['R'] for n in geometry)
  assert all(types(joined,n)==['T'] for n in expected);assert sha(rust)==rust_before
  status='PASS_PRODUCTION_82RUST_FULLCRATE_GCC9_MEM_TU_PUBLIC_ABI_GEOMETRY_RELOC_PARTIAL_LINK'
 except BaseException as exc:error=repr(exc)
 result=dict(scope=__doc__,status=status,error=error,seconds=time.monotonic()-start,combined_cpu_seconds=ns['cpu_used'](),commands=results,exports=exports,geometry_sizes=geometry_sizes,source_bindings_sha256=sha(E/'SOURCE-BINDINGS.json'),pinned_GCC14_default_image_link=False,native=False,retirement_credit=False,canonical_modified=False)
 for key,path in [('Rust_object',rust),('C_object',mem),('partial_object',part)]:result[key]=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size) if path.exists() else None
 result['reused_initial_result_sha256']='d66596620181b7f966812395bfbe84b47e6a249326726d3555b1c9d09d630bd8';result['bounded_correction']='Observer only: unique COMMON or BSS tentative page_hash_locks provider; no source/flags/recompile. GCC9 defaults to COMMON for uninitialized global.';write(D/'correction1/RESULT.json',result)
 for p in [D/'correction1/RESULT.json']+[q for cap in (D/'correction1').glob('*-capture-1') for q in cap.iterdir() if q.is_file()]:
  target=E/p.relative_to(D);target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(p.read_bytes())
 signal.setitimer(signal.ITIMER_REAL,0);print(json.dumps({k:result[k] for k in ['status','error','seconds','combined_cpu_seconds','Rust_object','C_object','partial_object','geometry_sizes']}))
if __name__=='__main__':main()
