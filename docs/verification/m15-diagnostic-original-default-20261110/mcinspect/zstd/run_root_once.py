import ast,datetime,hashlib,json,os,pathlib,re,shutil,signal,subprocess,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel')
HERE=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/mcinspect-original-default-assessment-p04tests-max-1/libzstd-provider-read-1')
OUT=HERE/'execution-1';assert not OUT.exists();OUT.mkdir(mode=0o700)
base=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py')
tree=ast.parse(base.read_text());funcs=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('now','sha','save','call','admission')],type_ignores=[]);code=ast.unparse(funcs);assert 'over + memory + 268435456' in code;code=code.replace('over + memory + 268435456','over + memory + 536870912').replace("'old_UNKNOWN_jobs': 1","'old_CPU0_UNKNOWN_jobs': 1, 'new_CPU7_UNKNOWN_jobs': 1, 'new_CPU7_UNKNOWN_reserved_bytes': 268435456");exec(compile(code,str(base),'exec'))
cap=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/root-reviewed-capture-correction-1/correction-1/phase.py');assert sha(cap)=='4ca162e1a0e68d236a1f22abbeb7b88849e04e6ffac62049ce28604646acc01b'
capreview=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/root-reviewed-capture-review-source-acquisition-max-1/correction-1/REVIEW.json');assert sha(capreview)=='a0341e69f0123791b983151b9fa4dbaec3d34029439d3d4c0ccae8ddade1c7fd';exec(compile(cap.read_text(),str(cap),'exec'))
shared=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py');tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
qpath=HERE/'REQUEST.json';assert sha(qpath)=='b81ee9d9ad81f3b64a83f34bb6d4ea5b4a37c72439cc3eda0f98f63d540b585e';q=json.loads(qpath.read_text())
review=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/diagnostic-shared-provider-review-source-acquisition-max-1/F03-zstd-runtime-operation-1/REVIEW.json');assert sha(review)=='61189ebb62d1f8547cd1af666fbc4ca78bf022404b73d7f28e920d72f6aa02e4'
ENV=os.environ.copy();ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py');docker=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'];clients=[];phases=[];owned=[];started=now()
try:
 admission('ADMISSION.json',268435456,16777216)
 for key in ('input_manifest','owner_helper','probe'):
  row=q[key];assert sha(row['path'])==row['sha256'] and pathlib.Path(row['path']).stat().st_size==row['bytes']
 assert not call('running-preflight',docker+['ps','--no-trunc','--format','{{.ID}}']).strip()
 argv=q['create_argv'];name=argv[argv.index('--name')+1];assert name not in call('names-preflight',docker+['ps','-a','--format','{{.Names}}']).decode().splitlines()
 output=pathlib.Path(q['fresh_output_root']);assert not output.exists();output.mkdir(mode=0o755);(output/'tmp').mkdir(mode=0o700)
 phase('providers',argv,q['mounts'],268435456,32,120)
 report=json.loads((output/'REPORT.json').read_text());assert report['status']==q['expected_status'] and len(report['providers'])==1
 records=json.loads((output/'ownership.json').read_text());assert len(records)==2 and [x['label'] for x in records]==q['expected_two_owned_command_labels']
 for row in records:
  assert int(row['leader_birth'])>0 and row['status']==0 and row['leader_parent_joined'] and row['whole_descendants_joined'] and row['streams_closed']
  assert not any(row.get(k) for k in ('adopted_reaps','adopted_kills','remaining_direct_children','error','timed_out','leader_group_signalled'))
 for row in report['providers']:
  assert row['id']=='zstd' and row['identity_stable_after_metadata']
  assert len(row['ELF_join']['selected_definitions'])==5
 remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining and not owned
 save('RESULT.json',{'status':'PASS_ZSTD_FIVE_TRANSITIVE_DEFINITIONS_VERSIONS_FILE_PACKAGE_PENDING_ORIGINAL_LEAF_REVIEW','started_at':started,'finished_at':now(),'request_sha256':sha(qpath),'review_sha256':sha(review),'capture_sha256':sha(cap),'capture_review_sha256':sha(capreview),'phases':phases,'clients':clients,'report':{'path':str(output/'REPORT.json'),'sha256':sha(output/'REPORT.json')},'inner_owned_records':records,'all_waits_streams_joined':True,'remaining_child_pids':remaining,'both_UNKNOWN_released':False,'original_leaf_credit':False});print(json.dumps({'status':'PASS','finished_at':now(),'inner_records':len(records)}))
except BaseException as exc:
 cleanup=[]
 for cid in list(owned):
  try:
   state=json.loads(call('failure-inspect-'+cid[:8],docker+['inspect',cid]))[0]['State']
   if state['Running']:call('owned-bounded-container-stop-'+cid[:8],docker+['kill',cid]);call('owned-bounded-container-wait-'+cid[:8],docker+['wait',cid]);state=json.loads(call('failure-terminal-'+cid[:8],docker+['inspect',cid]))[0]['State']
   assert not state['Running'] and state['Pid']==0;call('failure-owned-remove-'+cid[:8],docker+['rm',cid]);cleanup.append({'CID':cid,'removed':True})
  except BaseException as secondary:cleanup.append({'CID':cid,'state':'UNKNOWN','secondary_error':type(secondary).__name__+': '+str(secondary)})
 save('RESULT.json',{'status':'FAILED_PRESERVED_NO_RETRY','started_at':started,'finished_at':now(),'primary_error':type(exc).__name__+': '+str(exc),'traceback':traceback.format_exc(),'phases':phases,'clients':clients,'cleanup':cleanup,'both_UNKNOWN_released':False});raise
