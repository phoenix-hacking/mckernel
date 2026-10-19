"""Case-specific14 adapter of accepted FP finite capture producer; no root/Docker/decoder."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,time
R=Path(__file__).resolve().parent.parent;O=R/'heavy-proposal-1/postbuild-readonly-1'
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def bound(row):
 p=Path(row['path']);assert digest(p)==row['sha256'];return json.loads(p.read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
def identity(p):
 s=os.lstat(p);assert stat.S_ISREG(s.st_mode)
 return dict(dev=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),bytes=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def main(argv=None):
 args=sys.argv[1:] if argv is None else argv;assert len(args)==2,'exact observation release path/hash required'
 release=bound(dict(path=args[0],sha256=args[1]));assert release['status']=='PASS_EXACT_ORDINARY_POSTBUILD_READONLY_RELEASE'
 review=bound(release['execution_review']);payload={k:v for k,v in release.items() if k!='execution_review'}
 assert review['decision']=='PASS_EXACT_ORDINARY_POSTBUILD_READONLY' and review['implementation_ownership'] is False and review['reviewer']!=release['author']
 assert review['reviewed_release_payload_sha256']==hashlib.sha256((json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()).hexdigest()
 for key in ['dispatcher','descriptor_facts_producer','actual_role_adapter']:assert digest(release[key]['path'])==release[key]['sha256']
 assert release['dispatcher']['path']==str(Path(__file__).resolve())
 plan=bound(release['commands']);copyplan=bound(release['copies']);profile=bound(release['profile']);tools=bound(release['tools']);artifacts=bound(release['actual_artifacts']);extra=bound(release['inspection_extra_artifacts'])
 assert set(artifacts)=={'cpu','process','rust','image'} and set(extra)=={'fallback'} and len(plan['operations'])==14
 assert release['operation_completion_contracts'].keys()=={str(i) for i in range(1,15)}
 assert not any(any(arg.startswith('--debug-dump') or arg=='-w' for arg in op['argv']) for op in plan['operations']),'historical fullDWARF13 replay excluded'
 completion={k:bound(v) for k,v in release['owner_completion'].items()}
 owner=completion['owner_receipt'];guard=completion['guard_result'];post=completion['postjoin_readback']
 assert owner['status']=='PASS' and owner['exit_code']==0 and owner['retired'] is True and owner['terminal_container_retained'] is True
 assert guard['retired'] is True and guard['retained_for_separate_cleanup'] is True and post['guard_direct_joined'] is True and post['root27_4_reacquired_after_join'] is True
 assert guard['owner_receipt_sha256']==post['owner_receipt_sha256']==release['owner_completion']['owner_receipt']['sha256']
 assert post['guard_result_sha256']==release['owner_completion']['guard_result']['sha256']
 assert owner['container_id']==guard['container_id']==post['container_id']==release['container_id']
 build_review=bound(release['actual_build_acceptance'])
 assert build_review['decision']=='PASS_ACTUAL_IMAGE_BUILD_AND_PREBUILD_COMPILERS' and build_review['actual_build_result_accepted'] is True and build_review['implementation_ownership'] is False and build_review['reviewer']!=release['author']
 assert build_review['container_id']==release['container_id'] and build_review['full_process_C_assertions']==71 and build_review['complete_native_legacy_crates']==2 and build_review['request_sha256']==release['request_sha256']
 assert build_review['image']['sha256']==artifacts['image']['sha256'] and build_review['image']['bytes']==artifacts['image']['bytes']
 c71=release['actual_C71'];assert digest(c71['assertion_source']['path'])==c71['assertion_source']['sha256']
 assertions=Path(c71['assertion_source']['path']).read_text();assert assertions.count('_Static_assert(')==71
 assert digest(c71['full_actual_C_TU']['path'])==c71['full_actual_C_TU']['sha256'] and Path(c71['full_actual_C_TU']['path']).read_text().endswith(assertions)
 proof=bound(c71['compiler_proof']);assert proof['status']=='PASS'
 for phase in ['release-tid-full-process-selected','release-tid-full-process-fallback']:
  selected=[row for row in proof['checks'] if row['phase']==phase];assert len(selected)==1 and selected[0]['exit_code']==0 and selected[0]['full_TU_fixture_sha256']==c71['full_actual_C_TU']['sha256']
 assert bound(release['actual_CPU_fullcrate_proof'])['status']=='PASS'
 for row in tools.values():assert str(Path(row['path']).resolve())==row['resolved_path'] and digest(Path(row['path']))==row['sha256'] and identity(Path(row['path']).resolve())==row['identity']
 observed=dict(artifacts,**extra)
 def sourcecheck():
  for row in observed.values():assert identity(row['path'])=={k:row[k] for k in ['dev','inode','uid','gid','mode','bytes','mtime_ns','ctime_ns']}
 def capacitycheck(remaining):
  for label,path in [('host',Path('/home/holden')),('scratch',Path('/home/holden/mckernel-work/scratch'))]:
   cap=profile['fresh_admission'][label];fs=os.statvfs(path);minimum=cap['floor_bytes']+cap['emergency_bytes']+(remaining if label=='host' else 0);assert fs.f_bavail*fs.f_frsize>=minimum
 for p in profile['required_absent_paths']:assert not os.path.lexists(p),p
 sourcecheck();remaining=profile['absolute_total_output_cap_bytes'];capacitycheck(remaining);(O/'captures').mkdir(mode=0o700);results=[]
 # Exact accepted receipt schema and direct wait are preserved from FP producer.
 def run(argv,stdout,stderr,status_path,label,reservation,contract):
  nonlocal remaining
  assert reservation<=remaining;capacitycheck(remaining);sourcecheck()
  write(Path(str(status_path)+'.command.json'),dict(argv=argv,stage=label,reservation_bytes=reservation,release_sha256=args[1]))
  start=time.monotonic();observer_error=None
  with Path(stdout).open('xb') as out,Path(stderr).open('xb') as err:
   child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
   try:write(Path(str(status_path)+'.child.json'),dict(pid=child.pid,monotonic_start=start,proc_queries=False))
   except BaseException as ex:observer_error=dict(type=type(ex).__name__,error=str(ex))
   finally:code=child.wait()
  row=dict(stage=label,observer_error=observer_error,argv=argv,returncode=code,direct_child_joined=True,elapsed_seconds=time.monotonic()-start,stdout_bytes=Path(stdout).stat().st_size,stderr_bytes=Path(stderr).stat().st_size,stdout_sha256=digest(stdout),stderr_sha256=digest(stderr))
  write(Path(status_path),row);results.append(row)
  assert code==contract['returncode'] and observer_error is None,label
  if contract['stderr_policy']=='empty':assert row['stderr_bytes']==0,label
  if label.startswith('command-'):assert row['stdout_bytes']<reservation//2 and row['stderr_bytes']<reservation//2,label
  sourcecheck();remaining-=reservation
 copyargv=[release['actual_artifacts']['sha256'] if x=='ACTUAL_ARTIFACTS_SHA256_FROM_GENERATED_METADATA' else x for x in copyplan['argv']]
 run(copyargv,copyplan['captures']['stdout'],copyplan['captures']['stderr'],copyplan['captures']['status'],'fourcopy',32*2**20+2048,dict(returncode=0,stderr_policy='empty'))
 for op in plan['operations']:
  i=op['index'];run(op['argv'],op['stdout_path'],op['stderr_path'],op['status_path'],'command-'+str(i),op['both_stream_reservation_bytes'],release['operation_completion_contracts'][str(i)])
 completionpath=O/'completed-command-receipt.json';write(completionpath,dict(status='PASS_EXACT_FOUR_COPY_AND14_DECLARED_COMPLETION_CONTRACTS_ONLY',results=results,release_sha256=args[1],container_id=release['container_id'],original_full_DWARF_gap_open=True,production_or_native_acceptance=False))
 facts=release['descriptor_facts_producer']['path'];factsargv=['/usr/bin/env','-i','PATH=/usr/bin:/bin','LC_ALL=C','/usr/bin/timeout','--signal=TERM','--kill-after=2s','35s','/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=1073741824','--cpu=30','--fsize=33554432','--','/home/holden/anaconda3/bin/python3','-I','-B',facts,'--plan',release['commands']['path'],'--plan-sha256',release['commands']['sha256'],'--release',args[0],'--release-sha256',args[1],'--completion',str(completionpath),'--completion-sha256',digest(completionpath),'--output',str(O/'four-leaf-facts-v2.json')]
 run(factsargv,str(O/'facts-v2.stdout'),str(O/'facts-v2.stderr'),str(O/'facts-v2.status.json'),'facts-v2',2*1048576,dict(returncode=0,stderr_policy='empty'))
 write(O/'postbuild-v2-result.json',dict(status='PASS_EXACT_FOUR_COPY_DECLARED14_AND_V2_MECHANICAL_FACTS_ONLY',release_sha256=args[1],stages=len(results),artifact_copies=4,declared_commands=14,completed_receipt_sha256=digest(completionpath),facts_sha256=digest(O/'four-leaf-facts-v2.json'),original_full_DWARF_gap_open=True,cleanup_authorized=False,production_or_native_acceptance=False))
 print('PASS fourcopy +14declaredcompletion/FDhash +v2facts; originalDWARFgap OPEN; no cleanup/native credit')
if __name__=='__main__':main()
