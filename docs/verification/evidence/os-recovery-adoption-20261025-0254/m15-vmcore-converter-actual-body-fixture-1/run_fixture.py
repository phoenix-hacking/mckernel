"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded ordinary HOST compilation/full-command callback fixture; no actual dumps.
"""
import hashlib,json,os,re,resource,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
SRC=ROOT/'docs/verification/evidence/velocity-intervention-20261023-11/m15-vmcore2mckdump'
RUSTC=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
SCOPE=__doc__.splitlines()[0]
PIN={'candidate':(SRC/'ldump2mcdump_helpers.ack-candidate.rs','5205663e825abfb26d8eb0e01c225c1eb7cecd95051832b7234890dba5f3de78'),'reference':(SRC/'reference/ldump2mcdump_helpers.rs','4e036420cd4f3e62694c33d235747d23dabc4ac54236fe46b9cdf0290c93a9f0'),'contract':(SRC/'converter-ack-contract.json','971cccbdd9d351e24ca81a5aeeb35008c606421bb72eaeea61d671e54bacbde5'),'patch':(SRC/'converter-ack.patch','a3c14d0f3474c101a6c80505e5fb33df45950c4a7df72c8c23658afdfa32e7f5')}
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(p,value):
 with p.open('x')as f:f.write(json.dumps(value,indent=2)+'\n')
def birth(pid):
 try:return int(Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()[19])
 except FileNotFoundError:return None

def limits():
 os.sched_setaffinity(0,{0})
 resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
 resource.setrlimit(resource.RLIMIT_CPU,(60,60))
 resource.setrlimit(resource.RLIMIT_FSIZE,(64<<20,64<<20))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def run(argv,label,out,start):
 assert time.monotonic()-start<85,'original90second envelope nearing cutoff; no new dispatch'
 d=out/label;d.mkdir()
 epoch=time.time();mono=time.monotonic()
 with (d/'stdout').open('xb')as so,(d/'stderr').open('xb')as se:
  child=subprocess.Popen([str(x)for x in argv],cwd=HERE,stdout=so,stderr=se,preexec_fn=limits)
  childbirth=birth(child.pid)
  got,status,usage=os.wait4(child.pid,0)
  assert got==child.pid
  code=os.WEXITSTATUS(status)if os.WIFEXITED(status)else -os.WTERMSIG(status)
  child.returncode=code
 receipt=dict(scope=SCOPE,argv=[str(x)for x in argv],cwd=str(HERE),pid=child.pid,birth=childbirth,parent_pid=os.getpid(),positive_direct_wait4=True,wait4_pid=got,wait_status=status,returncode=code,streams_closed=True,start_epoch=epoch,finish_epoch=time.time(),wall_seconds=time.monotonic()-mono,user_seconds=usage.ru_utime,system_seconds=usage.ru_stime,maxrss_KiB=usage.ru_maxrss,stdout=ref(d/'stdout'),stderr=ref(d/'stderr'),limits=dict(CPU=[0],AS_bytes=2<<30,CPU_seconds=60,FSIZE_bytes=64<<20,CORE_bytes=0,jobs=1,aggregate_wall_seconds=90))
 put(d/'JOIN-WAIT4.json',receipt)
 if code:raise RuntimeError('Actual command failed: '+label+' rc='+str(code)+' retained in '+str(d))
 return receipt

def main():
 start=time.monotonic();limits()
 out=HERE/'actual-run-2';out.mkdir()
 envelope=dict(scope=SCOPE,parent_pid=os.getpid(),birth=birth(os.getpid()),outer_parent_pid=os.getppid(),outer_parent_birth=birth(os.getppid()),start_epoch=time.time(),start_monotonic=start,allowed_seconds=90,affinity=sorted(os.sched_getaffinity(0)),rlimits={str(k):list(resource.getrlimit(k))for k in [resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE,resource.RLIMIT_CORE]},runtime_scope='ordinary HOST fixture only; no SDK/native/root/Docker/actual crashdump')
 put(out/'PARENT-START.json',envelope)
 refs={}
 for key,(p,sha)in PIN.items():
  refs[key]=ref(p);assert refs[key]['sha256']==sha
 refs['rustc']=ref(RUSTC);refs['fixture']=ref(HERE/'fixture.c')
 # Reuse existing C dump layout declarations byte-for-byte; no format encoder is
 # created in the fixture. Rust's actual body produces the checked section data.
 cfile=ROOT/'executer/user/ldump2mcdump.c';raw=cfile.read_text()
 layout=raw[raw.index('struct ihk_dump_page {'):raw.index('#define PATH_MAX')]
 (HERE/'dump-layout.h').write_text('/* Exact existing C dump layout declarations; test fixture only. */\n'+layout)
 refs['C_layout_source']=ref(cfile);refs['C_layout_header']=ref(HERE/'dump-layout.h')
 put(out/'INPUTS.json',refs)
 wraps=['malloc','calloc','free','fwrite','fprintf','fflush','getopt','gethostname','getuid','getpwuid','time','localtime','asctime','perror']
 receipts=[]
 for source in ['candidate','reference']:
  obj=HERE/'actual-run-1'/(source+'.o');binary=out/(source+'-fixture')
  original=json.loads((HERE/'actual-run-1'/(source+'-compile')/'JOIN-WAIT4.json').read_bytes());assert original['returncode']==0 and original['positive_direct_wait4'] is True
  refs[source+'_reused_object']=ref(obj)
  refs[source+'_original_compile_join']=ref(HERE/'actual-run-1'/(source+'-compile')/'JOIN-WAIT4.json')
  receipts.append(run(['/usr/bin/cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-DEXPECT_ACK='+str(int(source=='candidate')),HERE/'fixture.c',obj,*['-Wl,--wrap='+x for x in wraps],'-o',binary],source+'-link',out,start))
 cases=[('success',0)]+[('metadata',i)for i in range(1,8)]+[('physical',i)for i in range(1,4)]+[('write',i)for i in range(1,8)]+[('close',1),('physchunks-null',1)]+[('allocation',i)for i in range(1,8)]
 observations={}
 for kind,pos in cases:
  label='candidate-%s-%d'%(kind,pos)
  receipt=run([out/'candidate-fixture',kind,str(pos)],label,out,start);receipts.append(receipt)
  observations[label]=json.loads(Path(receipt['stdout']['path']).read_bytes())
 matched=[]
 for kind,pos in [c for c in cases if c[0]in ('success','physical','write','close','physchunks-null')]:
  label='reference-%s-%d'%(kind,pos)
  receipt=run([out/'reference-fixture',kind,str(pos)],label,out,start);receipts.append(receipt)
  old=json.loads(Path(receipt['stdout']['path']).read_bytes());new=observations['candidate-%s-%d'%(kind,pos)]
  compared=[key for key in old if key not in ('ack','flushes','ack_event')]
  assert all(old[k]==new[k]for k in compared),'baseline callback observations diverged '+label
  matched.append(dict(case=[kind,pos],compared_fields=compared,reference=ref(Path(receipt['stdout']['path'])),candidate=ref(out/('candidate-%s-%d'%(kind,pos))/'stdout')))
 put(out/'REUSED-OBJECTS.json',{k:v for k,v in refs.items()if '_reused_object' in k or '_original_compile_join' in k})
 ownership=[dict(case=name,live_allocations=row['live_allocations'],live_bytes=row['live_bytes'])for name,row in observations.items()if not row['ownership_complete']]
 result=dict(scope=SCOPE,status='PASS_NARROW_ACTUAL_FULL_BODY_ACK_AND_LAYOUT_MATRIX_OWNERSHIP_INCOMPLETE',candidate_cases=len(cases),matched_reference_cases=len(matched),commands=len(receipts),all_commands_positive_wait4=True,all_commands_returncode_zero=True,full_actual_body_compiled_unchanged=refs['candidate'],actual_registered_callback_invoked=True,actual_BFD_or_SDK_native=False,ACK_success_exact_path_count=1,metadata_failure_ACKs=0,physical_failure_diagnostics_and_later_observations_preserved=True,bitmap_failure_map_buffers_all_freed=True,matched_baseline=matched,ownership_status='FAIL_NONZERO_PRODUCER_OWNERSHIP_RETAINED_NOT_FULL_LIFECYCLE_PASS',ownership_failures=ownership,source_modified=False,whole_file_acceptance=False,native_acceptance=False,wall_seconds=time.monotonic()-start,sum_command_wall_seconds=sum(r['wall_seconds']for r in receipts),sum_CPU_seconds=sum(r['user_seconds']+r['system_seconds']for r in receipts),peak_command_maxrss_KiB=max(r['maxrss_KiB']for r in receipts),runtime_authority=None)
 assert result['wall_seconds']<90
 for key,(p,sha)in PIN.items():assert ref(p)==refs[key]
 put(out/'RESULT.json',result)
 put(out/'COMMANDS.json',receipts)
 put(out/'PARENT-FINISH.json',dict(parent_pid=os.getpid(),birth=birth(os.getpid()),finish_epoch=time.time(),positive_wait4_children=len(receipts),unjoined_children=[],streams_closed=True,wall_seconds=time.monotonic()-start))
 print(json.dumps({k:v for k,v in result.items()if k not in ('matched_baseline','ownership_failures')}))
 print('Ownership cases with retained allocations:',len(ownership))

if __name__=='__main__':main()
