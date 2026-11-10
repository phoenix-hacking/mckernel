import ast,datetime,hashlib,importlib.util,json,os,pathlib,shutil,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel')
HERE=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/do-mmap-default-ownership-1/provider-correction-1/test-type-correction-1')
OUT=HERE.parent/'host-execution-2'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
qpath=HERE/'HOST-REQUEST.PROPOSED.json';assert sha(qpath)=='5787c7a16a6a0555d64793593485192480f56f21cda6775ac149103ec7f31469';q=json.loads(qpath.read_text())
review=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/do-mmap-default-review-source-acquisition-max-1/provider-correction-1/test-type-correction-1/REVIEW.json');assert sha(review)=='5b0deae129e79f59c6b65c7a5cd3c500b9256940289fd000f940a630342ad7c1'
shared=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py')
tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
ownerpath=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/program-behavior-1/owned_process.py');assert sha(ownerpath)=='afe7403ead1bf8b2c527dfa34a0c0c19010cde5f27a646ccf1545fb8f3b9bc1d'
assert not OUT.exists();OUT.mkdir(mode=0o700);started=now();completed=[]
try:
 addendum=HERE/'RESOURCE-ADMISSION.ADDENDUM.json';assert sha(addendum)=='dcc74c0ac79fcf8aeb95a7108fd5c1a32a6fcbd8c90320f114e58d6757448097'
 stamp=guard();available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;over=overhead();host=shutil.disk_usage(str(ROOT)).free;scratch=shutil.disk_usage(str(HERE)).free
 assert available>=26*1024**3 and over+2147483648+536870912<=4294967296
 assert host>=16*1024**3+33554432 and scratch>=12*1024**3+33554432
 save('ADMISSION.json',{'at':now(),'guard_updated_at':stamp,'MemAvailable_bytes':available,'overhead_bytes':over,'new_reserved_bytes':2147483648,'old_CPU0_UNKNOWN_bytes':268435456,'new_CPU7_NUMA_UNKNOWN_bytes':268435456,'old_UNKNOWN_released':False,'new_jobs':1,'retained_UNKNOWN_jobs':2,'max_aggregate_jobs':3,'host_free_bytes':host,'scratch_free_bytes':scratch,'native_admitted':False})
 inp=q['inputs'];assert sha(inp['path'])==inp['sha256'];data=json.loads(pathlib.Path(inp['path']).read_text())
 for row in data['files']+[data['compiler']]:
  assert sha(row['path'])==row['sha256'],row['path']
  if 'bytes' in row:assert pathlib.Path(row['path']).stat().st_size==row['bytes']
 output=pathlib.Path(q['fresh_output_root']);assert not output.exists();output.mkdir(mode=0o700);pathlib.Path(q['private_tmp']).mkdir(mode=0o700)
 spec=importlib.util.spec_from_file_location('mmap_owner',str(ownerpath));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);owner=mod.Owner(OUT)
 for i,cmd in enumerate(q['commands'],1):
  guard();r=owner.run(cmd['argv'],env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},cwd=q['cwd'],timeout=cmd['wall_seconds'],label='phase-'+str(i));rec=owner.records[-1]
  assert rec['leader_birth'] and rec['leader_parent_joined'] and rec['whole_descendants_joined'] and rec['streams_closed'] and not rec['adopted_reaps'] and not rec['adopted_kills'] and not rec['remaining_direct_children'] and not rec['error']
  assert r.returncode==cmd['expected_exit'],(cmd['id'],r.returncode)
  if cmd.get('required_stdout')=='empty':assert not r.stdout
  if cmd.get('required_stderr')=='empty':assert not r.stderr
  if 'required_stdout_json' in cmd:assert json.loads(r.stdout)==cmd['required_stdout_json']
  if 'required_output' in cmd:assert pathlib.Path(cmd['required_output']).is_file() and pathlib.Path(cmd['required_output']).stat().st_size>0
  completed.append({'phase':i,'id':cmd['id'],'exit':r.returncode,'ownership':rec});save('PARTIAL.json',{'started_at':started,'completed':completed})
 assert len(owner.records)==3 and not pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
 exe=output/'add-range-rollback';save('RESULT.json',{'status':'PASS_SAFE_BASELINE42_AND_SIX_CHANGED_ROLLBACK_RSS_CASES_HOST_ONLY','started_at':started,'finished_at':now(),'request_sha256':sha(qpath),'review_sha256':sha(review),'phases':completed,'executable':{'path':str(exe),'bytes':exe.stat().st_size,'sha256':sha(exe)},'all_three_positive_owned_records':True,'kernel_runtime':False,'native_admitted':False,'old_UNKNOWN_released':False,'original_acceptance':False})
 print(json.dumps({'status':'PASS','phases':3,'finished_at':now()}))
except BaseException as exc:
 save('RESULT.json',{'status':'FAILED_PRESERVED_NO_RETRY','started_at':started,'finished_at':now(),'error':type(exc).__name__+': '+str(exc),'traceback':traceback.format_exc(),'phases':completed,'native_admitted':False,'old_UNKNOWN_released':False});raise
