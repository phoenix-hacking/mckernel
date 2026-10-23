"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,time
D=Path(__file__).resolve().parent
REPO=Path('/home/holden/mckernel')
OLD=REPO/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-2'
OLDSRC=D.parent.parent/'production-combined-2/source-materialization-attempt-2/materialized-source'
E=REPO/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-3/ordinary-fullcrate-callback3-1'
SCOPE=__doc__
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
inputs=json.loads((D/'input-bindings-80.json').read_text())
extra={'host-kernel/native-rust/abi/vdso.rs':'d796e3a0723d6a21096a1455c35a7820437dfc2b99e5bb0e1c1f4db79f1c7d7d','host-kernel/native-rust/zero_pages.rs':'47a4e27b63f50366229af4045d79dc5dee6ace179307cc19c08cc338c68b1def'}
for name,want in extra.items():
 src=OLDSRC/name;assert sha(src)==want
 dst=D/'source'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes());assert sha(dst)==want
 inputs[name]={'source':str(src),'path':str(dst),'sha256':want}
assert len(inputs)==82
for name,row in inputs.items():assert sha(Path(row['path']))==row['sha256']
# Resolve every explicit path declaration active in this build (sysfs_verify is gated off).
import re
for name,row in inputs.items():
 for rel in re.findall(r'#\[path\s*=\s*"([^"]+)"\]',Path(row['path']).read_text()):
  dest=(Path(row['path']).parent/rel).resolve()
  if 'mckernel_guest_sysfs.rs' in str(dest):continue
  assert dest in [Path(v['path']).resolve() for v in inputs.values()],str(dest)
 for macro in ('include!','include_str!','include_bytes!'):assert macro not in Path(row['path']).read_text()
helperpath=REPO/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py'
assert sha(helperpath)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('accepted',helperpath);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
descpath=OLD/'EXACT-PINNED-HOST-RUST-CANDIDATE.CORRECTED.NOT-RELEASED.json';assert sha(descpath)=='cdfb8330d97dcbbac78afa1881f0ae316914606fec44bc7594290da8d7a3261b'
desc=json.loads(descpath.read_text());argv=desc['argv_without_shell'].copy();assert len(argv)==46
assert sha(Path(argv[6]))=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
cwd=D/'build';cwd.mkdir();obj=cwd/'mckernel_rust.o';argv[-2]='--emit=obj='+str(obj);argv[-1]=str(D/'source/kernel/rust/lib.rs')
os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for kind,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(kind,(value,value))
write(D/'input-bindings-82.json',{'scope':SCOPE,'inputs':inputs,'previous80binding_limitation':'Two active external module files previously lacked individual old fullcrate input-bindings rows; new82closure binds exact manifest-authorized bytes.','descriptor_sha256':sha(descpath),'helper_sha256':sha(helperpath),'compiler_sha256':sha(Path(argv[6]))})
os.chdir(cwd);capture=D/'compiler-capture-1';capture.mkdir();command={'argv':argv,'cwd':str(cwd),'purpose':SCOPE,'shell':False,'extra_environment':{'RUST_MIN_STACK':'2097152'}};write(D/'command.json',command)
start=time.monotonic();joined=h.owned_capture(command,capture,90,lambda:None);write(D/'whole-join.json',joined)
passed=joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and not joined['error'] and not joined['retirement_error']
result={'scope':SCOPE,'status':'PASS_ACTUAL_82INPUT_FULLCRATE' if passed else 'FAIL_STOP_NO_RETRY','command':command,'whole_join':joined,'elapsed_seconds':time.monotonic()-start,'object':h.hashed(obj,32<<20) if passed else None,'production_default_link_proven':False,'native_proven':False,'C_retirement_proven':False,'no_automatic_retry':True}
write(D/'result.json',result)
if passed:
 before=sha(obj);nmcap=D/'nm-capture-1';nmcap.mkdir();nmcommand={'argv':['/usr/bin/nm','-g','--defined-only',str(obj)],'purpose':SCOPE,'shell':False};write(D/'nm-command.json',nmcommand);j=h.owned_capture(nmcommand,nmcap,90,lambda:None);write(D/'nm-whole-join.json',j)
 expected=list(json.loads((OLD/'ordinary-fullcrate-evidence-1/nm-result.json').read_text())['symbols'])+['x86_clear_page_unmap_bridge'];symbols={name:[] for name in expected}
 for line in (nmcap/'stdout').read_text().splitlines():
  fields=line.split()
  if len(fields)==3 and fields[2] in symbols:symbols[fields[2]].append(fields[1])
 nm_pass=j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'] and all(v==['T'] for v in symbols.values()) and sha(obj)==before
 write(D/'nm-result.json',{'scope':SCOPE,'status':'PASS_11_UNIQUE_ACTUAL_FULLCRATE_EXPORTS' if nm_pass else 'FAIL_STOP_NO_RETRY','symbols':symbols,'whole_join':j,'object_sha256':before,'object_unchanged':sha(obj)==before,'default_C_consumer_or_final_link_proven':False,'native_proven':False})
for name in ['run_fullcrate.py','input-bindings-82.json','command.json','whole-join.json','result.json','nm-command.json','nm-whole-join.json','nm-result.json']:
 if (D/name).exists():(E/name).write_bytes((D/name).read_bytes())
for folder,label in [('compiler-capture-1','compiler'),('nm-capture-1','nm')]:
 for stream in ['stdout','stderr']:
  q=D/folder/stream
  if q.exists():(E/(label+'.'+stream)).write_bytes(q.read_bytes())
print(json.dumps({'status':result['status'],'seconds':result['elapsed_seconds'],'object':result['object'],'nm':json.loads((D/'nm-result.json').read_text())['status'] if (D/'nm-result.json').exists() else None}))
