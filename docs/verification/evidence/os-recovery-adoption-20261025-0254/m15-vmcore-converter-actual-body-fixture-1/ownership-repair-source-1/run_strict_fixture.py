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
 out=HERE/'actual-strict-run-1';out.mkdir()
 put(out/'PARENT-START.json',dict(scope=SCOPE,parent_pid=os.getpid(),birth=birth(os.getpid()),outer_parent_pid=os.getppid(),outer_parent_birth=birth(os.getppid()),start_epoch=time.time(),start_monotonic=start,allowed_seconds=90,affinity=sorted(os.sched_getaffinity(0)),rlimits={str(k):list(resource.getrlimit(k))for k in [resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE,resource.RLIMIT_CORE]}))
 pins={}
 for key,(path,sha)in PIN.items():pins[key]=ref(path);assert pins[key]['sha256']==sha
 selected=HERE.parent/'selected-bfd-source-evidence-1/SOURCE-LIFETIME-FACTS.json'
 constraints=HERE.parent/'independent-source-review-1/RUST-OWNERSHIP-REPAIR-CONSTRAINTS.json'
 pins['selected_source_facts']=ref(selected);assert pins['selected_source_facts']['sha256']=='3db997f0c067ce19992d9a0ff57e352abdcecea40ddacb66b406a7aa6381b54c'
 pins['repair_constraints']=ref(constraints);assert pins['repair_constraints']['sha256']=='806086a654ca43bba2ecf42021013fc9df1bea9fa42c55f000dbd8f89ffc6a11'
 pins['private_candidate']=ref(HERE/'ldump2mcdump_helpers.ownership-candidate.rs')
 pins['strict_fixture']=ref(HERE/'strict_fixture.c');pins['dump_layout']=ref(HERE/'dump-layout.h');pins['rustc']=ref(RUSTC)
 put(out/'INPUTS.json',pins)
 receipts=[];obj=out/'ownership-candidate.o';binary=out/'strict-fixture'
 receipts.append(run([RUSTC,'--crate-name','ldump2mcdump_ownership','--crate-type','lib','--edition=2021','--cfg','ldump2_full_body','-C','panic=abort','-C','opt-level=2','-C','codegen-units=1','--emit=obj='+str(obj),HERE/'ldump2mcdump_helpers.ownership-candidate.rs'],'candidate-compile',out,start))
 receipts.append(run(['/usr/bin/nm','-u',obj],'undefined-symbols',out,start))
 undefined=Path(receipts[-1]['stdout']['path']).read_text().splitlines()
 allowed={'argcnt','args','asctime','bfd_close','bfd_close_all_done','bfd_fopen','bfd_get_section_by_name','bfd_init','bfd_make_section_anyway','bfd_perror','bfd_set_format','bfd_set_section_contents','bfd_set_section_flags','bfd_set_section_size','calloc','fflush','fp','fprintf','free','fwrite','gethostname','getopt','getpwuid','getuid','localtime','machdep','malloc','memset','optarg','perror','readmem','register_extension','stderr','strcpy','strlen','symbol_value','time'}
 assert {line.split()[-1]for line in undefined}<=allowed,'new FFI beyond the declared exact alias boundary'
 wraps=['malloc','calloc','free','fwrite','fprintf','fflush','getopt','gethostname','getuid','getpwuid','time','localtime','asctime','perror']
 receipts.append(run(['/usr/bin/cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-DEXPECT_ACK=1',HERE/'strict_fixture.c',obj,*['-Wl,--wrap='+x for x in wraps],'-o',binary],'strict-link',out,start))
 original=[('success',0)]+[('metadata',i)for i in range(1,8)]+[('physical',i)for i in range(1,4)]+[('write',i)for i in range(1,8)]+[('close',1),('physchunks-null',1)]+[('allocation',i)for i in range(1,8)]
 extra=[('open',1),('format',1),('time',1),('localtime',1)]+[(kind,i)for kind in ('make','size','flags')for i in range(1,8)]+[('get-phys',i)for i in range(1,4)]+[('abort-false',1)]
 observed=[];preserved=[]
 stable=['ack','flushes','read_calls','physical_reads','physical_writes','physical_read_mask','physical_write_mask','writes','read_diagnostics','bfd_errors','map_buffers_freed','map_buffers_live']
 for kind,pos in original+extra:
  label='strict-%s-%d'%(kind,pos);receipt=run([binary,kind,str(pos)],label,out,start);receipts.append(receipt)
  lines=Path(receipt['stdout']['path']).read_text().splitlines();assert len(lines)==2 and lines[0].startswith('STRICT_OWNERSHIP ')
  row=json.loads(lines[1]);assert row['ownership_complete'] is True and row['live_allocations']==row['live_bytes']==0
  ownership=dict(token.split('=',1)for token in lines[0].split()[1:]);assert ownership['handles']==ownership['destroyed'] and ownership['live_project']=='0'
  observed.append(dict(case=[kind,pos],ownership=ownership,body=row,join=ref(out/label/'JOIN-WAIT4.json')))
  if (kind,pos)in original:
   oldpath=HERE.parent/'actual-run-2'/('candidate-%s-%d'%(kind,pos))/'stdout';old=json.loads(oldpath.read_bytes())
   assert all(old[k]==row[k]for k in stable),'preserved ACK/read/write/diagnostic effect diverged '+label
   preserved.append(dict(case=[kind,pos],old_observation=ref(oldpath),fields=stable))
 result=dict(scope=SCOPE,status='PASS_PRIVATE_RUST_OWNERSHIP_REPAIR_ACTUAL_FULL_BODY_STRICT_MOCK_ONLY',private_candidate=pins['private_candidate'],original_ACK_candidate_unchanged=pins['candidate'],original_cases_preserved=len(original),additional_repaired_failure_cases=len(extra),strict_cases=len(observed),observations=observed,preserved_original_effects=preserved,all_returns_zero_live_project_allocations=True,all_opened_mock_BFD_handles_terminally_consumed_once=True,borrowed_names_live_through_all_mock_BFD_uses_and_teardown=True,normal_close_FALSE_consumes_no_retry=True,abort_close_FALSE_consumes_no_retry=True,source_package_BFD_semantics=pins['selected_source_facts'],selected_actual_SDK_static_archive_identity='UNBOUND_PREREQUISITE',real_BFD_heap_or_file_or_SDK_or_native_qualified=False,new_import='bool bfd_close_all_done(bfd *) from selected pinned header2968/opncls920-936',whole_file_acceptance=False,native_acceptance=False,commands=len(receipts),all_commands_positive_wait4=True,wall_seconds=time.monotonic()-start,sum_command_wall_seconds=sum(x['wall_seconds']for x in receipts),child_CPU_seconds=sum(x['user_seconds']+x['system_seconds']for x in receipts),peak_command_RSS_KiB=max(x['maxrss_KiB']for x in receipts),runtime_authority=None)
 assert result['wall_seconds']<90
 put(out/'COMMANDS.json',receipts);put(out/'RESULT.json',result)
 put(out/'PARENT-FINISH.json',dict(parent_pid=os.getpid(),birth=birth(os.getpid()),finish_epoch=time.time(),all_direct_children_positive_wait4=True,direct_children=len(receipts),unjoined_children=[],streams_closed=True,wall_seconds=time.monotonic()-start))
 for key,(path,sha)in PIN.items():assert ref(path)==pins[key]
 print(json.dumps({k:v for k,v in result.items()if k not in ('observations','preserved_original_effects')}))

if __name__=='__main__':main()
