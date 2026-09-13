"""Build isolated actual transport-fault overlay; restore both shared production trees."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,os,re,shlex,shutil,stat,sys
assert os.getuid()==1000 and os.sched_getaffinity(0)=={2,3,4,5}
repo,work=Path('/workspace'),Path('/work')
assert shutil.disk_usage(work).free>3*1024**3
mode,attempt=sys.argv[1:];assert mode in ('prepublish-hard','postpublish-notify','recoverable-backpressure','permanent-backpressure') and attempt.isdecimal()
out=work/('stability-transport-fault-module-20260913-'+mode+'-'+attempt);out.mkdir()
parent=work/'native-ultra-module-20260909-2026091301'
stage=work/'native-source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel'
modules=work/'native-build-base-24a151fe/drivers/misc/mckernel'
record=dict(status='RUNNING',commands=[],inputs=[],started_utc=datetime.now(timezone.utc).isoformat(),verification_only=True,phase_wiring='SMP_IOCTL_AND_UNLOCKED_ACCEPTED_BARRIER',mode=mode,actual_guest_transport_fault_verified=False,production_gate_credit=False)
moved_stage=moved_modules=False

def identity(p):
 digest=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):digest.update(b)
 return dict(path=str(p),size=p.stat().st_size,sha256=digest.hexdigest())
def tree(p):
 rows=[]
 for q in sorted(p.rglob('*')):
  s=q.lstat();row=dict(path=str(q.relative_to(p)),mode=stat.S_IMODE(s.st_mode))
  if q.is_symlink():row.update(kind='symlink',target=os.readlink(q))
  elif q.is_file():row.update(kind='file',size=s.st_size,sha256=identity(q)['sha256'])
  elif q.is_dir():row.update(kind='directory')
  else:raise ValueError('unexpected build tree special file: '+str(q))
  rows.append(row)
 return rows

def save():(out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
try:
 shutil.copyfile(__file__,out/'helper.py');shutil.copyfile(repo/'scripts/application-tests/supervisor.py',out/'supervisor.py')
 spec=importlib.util.spec_from_file_location('supervisor',out/'supervisor.py');supervisor=importlib.util.module_from_spec(spec);spec.loader.exec_module(supervisor)
 env=dict(os.environ);(out/'tmp').mkdir();env['TMPDIR']=str(out/'tmp')
 def run(label,argv,timeout=120):
  if not Path(argv[0]).is_absolute():argv[0]=shutil.which(argv[0])
  record['phase']=label;save();print('RUN',label,flush=True)
  result=supervisor.run_supervised(argv,cwd=str(out),env=env,attempt_dir=str(out/(label+'-collection')),timeout_seconds=timeout,cleanup_timeout_seconds=20,stdout_limit_bytes=16*1024**2,stderr_limit_bytes=16*1024**2)
  record['commands'].append(dict(label=label,argv=argv,collection=result));save()
  assert result['status']=='COMPLETED' and result['wait_status']==dict(kind='exited',code=0) and result['cleanup_complete'],(label,result['status'],result['wait_status'])
  return (out/(label+'-collection')/'stdout.bin').read_text()
 pstate=json.loads((parent/'record.json').read_text());assert pstate['status']=='PASS'
 record['parent_record']=identity(parent/'record.json')
 for row in pstate['outputs']+pstate['compiler_inputs']:assert identity(Path(row['path']))==row,row
 record['parent_inputs']=pstate['compiler_inputs']
 record['shared_stage_before']=tree(stage);record['shared_modules_before']=tree(modules)
 package=out/'source/scripts/tests';package.mkdir(parents=True)
 for name in ('prepare_stability_owner_observer.py','prepare_stability_owner_phase.py','prepare_stability_transport_fault.py'):
  shutil.copyfile(repo/'scripts/tests'/name,package/name)
 for name in ('stability-owner-observer','stability-owner-phase','stability-transport-fault'):
  shutil.copytree(repo/'scripts/tests/fixtures'/name,package/'fixtures'/name)
 shutil.copyfile(repo/'scripts/tests/fixtures/stability-ret-observer.rs',package/'fixtures/stability-ret-observer.rs')
 (out/'source/scripts/application-tests').mkdir(parents=True,exist_ok=True)
 shutil.copyfile(repo/'scripts/application-tests/owner_observations.py',out/'source/scripts/application-tests/owner_observations.py')
 shutil.copyfile(repo/'scripts/tests/test_owner_observations.py',out/'source/scripts/tests/test_owner_observations.py')
 record['fixture_inputs']=[identity(p) for p in sorted((out/'source').rglob('*')) if p.is_file()]
 prior_owner = work/'stability-transport-fault-module-20260913-prepublish-hard-3/record.json'
 prior_owner_record = json.loads(prior_owner.read_text())
 assert prior_owner_record['status']=='PASS_BUILD_ONLY' and prior_owner_record['owner_parser_tests']==19
 for relative in ('scripts/tests/test_owner_observations.py','scripts/application-tests/owner_observations.py'):
  actual=identity(out/'source'/relative)
  old=next(row for row in prior_owner_record['fixture_inputs'] if row['path'].endswith('/source/'+relative))
  assert actual['size']==old['size'] and actual['sha256']==old['sha256']
  assert identity(Path(old['path']))==old
 record['reused_owner_parser_tests']=dict(record=identity(prior_owner),passed_cases=19,rerun=False,reason='Exact parser/test bytes unchanged; reuse original pinned proof')
 record['prior_qmp13_record']=identity(work/'stability-transport-fault-module-20260913-prepublish-hard-2/record.json')
 assert identity(package/'fixtures/stability-owner-observer/smp_application.append.rs')['sha256']=='f6f6ec5f859a977c3ebb22998eef891cf480f70dacb97d930bd5844ff9caf2fa'
 assert identity(package/'prepare_stability_owner_phase.py')['sha256']=='cd58971d7a810728f9426dfa10d2b661c831ecfe1328e413554632764f2d1d0d'

 combined=out/'combined-source';shutil.copytree(parent/'staged-source',combined,symlinks=True)
 record['overlays']=[]
 for label,helper,new_module in [('owner','prepare_stability_owner_observer.py','stability_observer.rs'),('phase','prepare_stability_owner_phase.py','stability_phase.rs'),('transport','prepare_stability_transport_fault.py',None)]:
  target=out/(label+'-overlay')
  argv=['python3','-B',str(package/helper),'--source',str(combined),'--output',str(target)]
  if label=='transport':argv+=['--mode',mode]
  run('prepare-'+label,argv)
  overlay=json.loads((target/'record.json').read_text());assert overlay['status']=='PREPARED_NOT_COMPILED_NOT_EXECUTED',overlay['status']
  record['overlays'].append(identity(target/'record.json'))
  for row in overlay['files']:
   actual=identity(combined/row['name']);assert(actual['size'],actual['sha256'])==(row['original']['size'],row['original']['sha256']),row
   shutil.copyfile(target/row['name'],combined/row['name'])
  if new_module:shutil.copyfile(target/new_module,combined/new_module)
 # Complete isolated source preparation precedes any shared tree mutation.
 stage.rename(out/'restoration-stage');moved_stage=True
 shutil.copytree(combined,stage,symlinks=True)
 modules.rename(out/'restoration-module-build');moved_modules=True
 shutil.copytree(out/'restoration-module-build',modules,symlinks=True)
 run('format-overlay',['rustfmt','--edition','2021','--config','skip_children=true,reorder_modules=false']+[str(p) for p in sorted(stage.glob('*.rs'))])
 record['compiler_inputs']=[identity(p) for p in sorted(stage.rglob('*')) if p.is_file()]
 command=work/'native-irq-transport-exact-stage-20260907-1/module-build.command';record['build_command_input']=identity(command)
 run('native-module-build',shlex.split(command.read_text()),1800)
 for name in ('ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko'):
  shutil.copyfile(modules/name,out/name)
  asm=run(name+'-disassembly',['objdump','-d',str(out/name)])
  assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|mm[0-7])\b',asm),name
  run(name+'-symbols',['nm','-S',str(out/name)])
  run(name+'-undefined',['nm','-u',str(out/name)])
  run(name+'-modinfo',['modinfo',str(out/name)])
 record['compiled_modules']=[identity(out/name) for name in ('ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko')]
 # Retain demangled instructions for actual frame/call-chain review; no static
 # source size or successful link alone is a stack-budget acceptance claim.
 for name in ('ihk-smp-x86_64.ko','mcctrl.ko'):
  run(name+'-demangled-disassembly',['objdump','-Cd',str(out/name)])
 record.update(status='PASS_BUILD_ONLY',actual_stack_frames_verified=False,observer_guest_verified=False)

except BaseException as error:
 record.update(status='FAIL',error_type=type(error).__name__,error=str(error));raise
finally:
 try:
  if moved_modules:
   if modules.exists():modules.rename(out/'module-build')
   (out/'restoration-module-build').rename(modules)
  if moved_stage:
   if stage.exists():stage.rename(out/'staged-source')
   (out/'restoration-stage').rename(stage)
  if 'shared_stage_before' in record:
   record['shared_stage_after']=tree(stage);record['shared_modules_after']=tree(modules)
   assert record['shared_stage_after']==record['shared_stage_before'],'stage restoration mismatch'
   assert record['shared_modules_after']==record['shared_modules_before'],'module restoration mismatch'
   record['shared_production_trees_restored']=True
  if (out/'staged-source').exists() and 'compiler_inputs' in record:
   bindings=[]
   for old in record['compiler_inputs']:
    current=out/'staged-source'/Path(old['path']).relative_to(stage)
    actual=identity(current);assert (actual['size'],actual['sha256'])==(old['size'],old['sha256'])
    bindings.append(dict(historical_compile_path=old['path'],retained=actual))
   record['retained_compiler_bindings']=bindings
 except BaseException as error:
  record.update(status='RESTORATION_FAILED',restoration_error=str(error));raise
 finally:
  record['finished_utc']=datetime.now(timezone.utc).isoformat();save();print(record['status'],out,flush=True)
