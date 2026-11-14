import ast,datetime,hashlib,importlib.util,json,os,pathlib,shutil,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).resolve().parent;OUT=HERE/'execution-1'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
request=HERE/'REQUEST.json';assert sha(request)=='48bf56c5aef19585cae9132375e17153c8a51bef19e7a26e7608a1576e526838'
review=pathlib.Path(sys.argv[1]);assert sha(review)==sys.argv[2]
q=json.loads(request.read_text());rv=json.loads(review.read_text());assert rv['decision'].startswith('GO')
assert not OUT.exists();OUT.mkdir(mode=0o700);started=now();owner=None;admitted=False
shared=pathlib.Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py')
exec(compile(ast.Module(body=[n for n in ast.parse(shared.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('guard','overhead')],type_ignores=[]),str(shared),'exec'))
try:
 inputs=pathlib.Path(q['inputs']['path']);assert sha(inputs)==q['inputs']['sha256'];bound=json.loads(inputs.read_text())
 for x in bound['files']+[bound['interpreter']]:
  assert sha(x['path'])==x['sha256'],x['path']
  if 'bytes' in x:assert pathlib.Path(x['path']).stat().st_size==x['bytes'],x['path']
 release=json.loads((pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/time-bridge-image-operation-sdk-max-1/capture-binding-correction-1/execution-1/RESOURCE-RELEASE.json')).read_text());assert release['current_jobs']=='RELEASED'
 stamp=guard();mem=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;over=overhead();GiB=1024**3;cap=q['profile']['max_address_space_bytes'];growth=q['profile']['output_disk_reservation_bytes']
 assert mem>=26*GiB and over+cap<=4*GiB and shutil.disk_usage(ROOT).free>=16*GiB+growth and shutil.disk_usage(HERE).free>=12*GiB+growth
 output=pathlib.Path(q['fresh_output_root']);assert not output.exists();output.mkdir(mode=0o700);pathlib.Path(q['private_tmp']).mkdir(mode=0o700)
 save('ADMISSION.json',{'at':now(),'guard_updated_at':stamp,'MemAvailable_bytes':mem,'all_current_overhead_bytes':over,'new_job_bytes':cap,'CPU':7,'new_jobs':1,'aggregate_HOST_bytes':4*GiB,'aggregate_jobs_max':3,'other_current_payloads':[],'prior_clock_three_phase_scope_positive_retired':True,'source_or_native_holds_released':False,'request_sha256':sha(request),'review_sha256':sha(review)});admitted=True
 helper=pathlib.Path(q['ownership']['helper']['path']);assert sha(helper)==q['ownership']['helper']['sha256'];spec=importlib.util.spec_from_file_location('exact_owned_process',str(helper));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);owner=module.Owner(OUT)
 results=[]
 for i,c in enumerate(q['commands']):
  guard();label=q['ownership']['labels'][i];r=owner.run(c['argv'],env=os.environ.copy(),cwd=q['cwd'],timeout=c['wall_seconds'],label=label);rec=owner.records[-1]
  assert int(rec['leader'])>0 and int(rec['leader_birth'])>0 and rec['leader_parent_joined'] and rec['whole_descendants_joined'] and rec['streams_closed'] and not rec['timed_out'] and not rec['leader_group_signalled'] and not rec['adopted_reaps'] and not rec['adopted_kills'] and not rec['remaining_direct_children'] and rec['error'] is None,rec
  assert r.returncode==c['expected_exit']==rec['status'],c['id']
  if c.get('required_stdout')=='empty':assert r.stdout==b''
  if c.get('required_stderr')=='empty':assert r.stderr==b''
  if 'required_output' in c:
   executable=pathlib.Path(c['required_output']);assert executable.stat().st_size>0 and executable.read_bytes()[:4]==b'\x7fELF';save('EXECUTABLE.json',{'path':str(executable),'bytes':executable.stat().st_size,'sha256':sha(executable),'mode':oct(executable.stat().st_mode&0o777)})
  if 'required_stdout_json' in c:assert json.loads(r.stdout)==c['required_stdout_json']
  results.append({'id':c['id'],'argv':c['argv'],'cwd':q['cwd'],'exit':r.returncode,'ownership':rec});save('PARTIAL.json',{'started_at':started,'results':results})
 remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert len(owner.records)==1 and not remaining
 save('RESULT.json',{'status':'PASS_CHANGED_CALL_THREE_MOCK_CASES_FIVE_AST_INVOCATIONS_NO_REAL_CLIENTS','started_at':started,'finished_at':now(),'request_sha256':sha(request),'review_sha256':sha(review),'results':results,'all_waits_streams_joined':True,'remaining_direct_children':remaining,'kernel_native_actual_provider_executed':False,'original_acceptance':False});save('RESOURCE-RELEASE.json',{'at':now(),'current_job_retired':True,'released_new_job_bytes':cap,'released_new_jobs':1,'other_holds_or_history_changed':False});print(json.dumps({'status':'PASS','commands':1,'mock_cases':3,'AST_invocations':5,'finished_at':now()}))
except BaseException as e:
 try:save('RESULT.json',{'status':'FAILED_PRESERVED_NO_UNCHANGED_RETRY','started_at':started,'finished_at':now(),'error':type(e).__name__+': '+str(e),'traceback':traceback.format_exc(),'admitted':admitted,'ownership':owner.records if owner else [],'original_acceptance':False})
 except BaseException:pass
 raise
