"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual unprivileged LONG consumers. All synthetic releases/observations explicitly TESTONLY.
No Docker backend, root identity, native owner run or accepted input publication.
"""
import ast,copy,hashlib,importlib.util,json,os,signal,sys,time,traceback
from pathlib import Path
D=Path(__file__).resolve().parent;S=D/'source';F=D/'fixture-data-1';F.mkdir(mode=0o700)
M='/home/holden/mckernel-work/scratch/p12s5l1/m.json';MSHA='6c3c80bff36af0f96ce05f73294c37f035a3e12d7fdc3aeeef88fc7532c11471'
P='/home/holden/mckernel-work/native-runs/l12a1/p';PYTHON='/home/holden/anaconda3/bin/python3'
report=dict(scope=__doc__,status='RUNNING',python=sys.version,executable=sys.executable,root=0,Docker=0,live_owner=0,native_acceptance=False,families=[],checks=[],source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in S.iterdir() if p.is_file()})
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def digest(raw):return hashlib.sha256(raw).hexdigest()
def check(name,fn,reject=False):
 try:result=fn()
 except (ValueError,RuntimeError,OSError,AssertionError) as e:
  if not reject:raise
  report['checks'].append(dict(name=name,result='PASS_REFUSE',error=type(e).__name__+': '+str(e)));return
 if reject:raise AssertionError('guard accepted: '+name)
 report['checks'].append(dict(name=name,result='PASS'));return result
begin=time.monotonic()
try:
 assert sys.version_info[:2]==(3,9) and sys.executable==PYTHON and os.getuid()==os.geteuid()==1000
 o=load(S/'native_diagnostic_container_owner.py','long_actual_owner');g=o._long_transport();runner=load(S/'native_diagnostic_runner.py','long_actual_runner')
 # Family1: full unchanged real manifest consumer, relative imports and command construction.
 assert o.SELF==str(S/'native_diagnostic_container_owner.py') and o.RUNNER==str(S/'native_diagnostic_runner.py')
 owner_sha=digest(Path(o.SELF).read_bytes());cohort=json.loads((D/'COHORT-BINDINGS.json').read_bytes())
 assert owner_sha==cohort['native_diagnostic_container_owner.py']['sha256']
 d,m=check('actual_full_bound_manifest_156_sources_and_archive_oracles',lambda:o.bound_manifest(M,MSHA))
 assert Path(d.__file__)==S/'native_diagnostic.py' and m['pair_long_session']==g.PROFILE and m['pair']['apps'][0]['timeout_ms']==10000
 rdiag,backend=runner._runtime();assert Path(rdiag.__file__)==S/'native_diagnostic.py' and Path(backend.__file__)==S/'native_diagnostic_backend.py'
 check('actual_HOST_output_parent',lambda:o.private_parent(P,True,fresh=True))
 check('manifest_inside_writable_parent',lambda:o._manifest_outside_writable_parent(M,str(Path(M).parent)),True)
 check('stale_inside_owner_hash',lambda:o._inside(P,'0123456789abcdef0123456789abcdef','0'*64,M,MSHA),True)
 key=str(S/'native_diagnostic.py');old=o.SOURCE_HASHES[key];o.SOURCE_HASHES[key]='0'*64
 try:check('actual_bound_manifest_diagnostic_source_drift',lambda:o.bound_manifest(M,MSHA),True)
 finally:o.SOURCE_HASHES[key]=old
 obj=object.__new__(o.DiagnosticOwner);obj.owner_sha=owner_sha;obj.manifest_path=M;obj.manifest_sha256=MSHA;obj.parent=Path(P);obj.nonce='0123456789abcdef0123456789abcdef';obj.name='nd-'+obj.nonce;obj.label='mckernel.native-diagnostic.owner='+obj.nonce;obj.long_requested=True;obj.long_release='/TESTONLY/long-release.json';obj.long_release_sha='0'*64
 inside=obj._inside_args();create=obj._create_argv();assert inside[1]==o.SELF and inside[inside.index('--owner-sha256')+1]==owner_sha and '--log-driver=none' in create and '--cpuset-cpus=2-5' in create and '--memory=12g' in create and str(S) in str(create)
 check('actual_runner_inside_and_NONE_create_builders',lambda:None)
 report['families'].append(dict(name='actual_bound_manifest_and_builders',status='PASS',source_hash_rows=len(o.SOURCE_HASHES),readonly_roots=len(o.EXTRA_READONLY),backend_calls=0))
 # Family2: actual release consumer. Every release below is isolated TESTONLY data.
 proto=json.loads((D/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());proto.update(status='PASS_EXECUTION_RELEASE',boot_id='TESTONLY-BOOT-NOT-LIVE',expires_unix=1200,author='TESTONLY-author')
 def review(v):
  v['independent_review']=dict(status='PASS',reviewer='TESTONLY-independent-reviewer',implementation_ownership=False,payload_sha256=g.digest(g.canonical({k:x for k,x in v.items() if k!='independent_review'})))
  return v
 proto=review(proto);seq=[0]
 def release_call(value):
  seq[0]+=1;p=F/('TESTONLY-release-'+str(seq[0])+'.json');raw=(json.dumps(value,sort_keys=True)+'\n').encode();p.write_bytes(raw)
  return g.validate_release(str(p),digest(raw),M,value['nonce'],P,clock=lambda:1000,boot_id='TESTONLY-BOOT-NOT-LIVE')
 check('actual_validate_release_TESTONLY_full_cohort_budget',lambda:release_call(copy.deepcopy(proto)))
 for name,mut in [
  ('zero_emergency',lambda x:x['storage_admission'].update(emergency_bytes=0)),
  ('zero_campaign',lambda x:x['storage_admission'].update(campaign_bytes=0)),
  ('missing_input_growth',lambda x:x['storage_admission'].pop('scratch_input_growth_bytes')),
  ('altered_quota',lambda x:x['profile']['producer'].update(min_launches=99)),
  ('altered_deadline',lambda x:x['profile'].update(inner_seconds=7799)),
  ('altered_capture_profile',lambda x:x['profile']['external_capture'].update(retained_copies=2)),
  ('manifest_drift',lambda x:x['manifest'].update(sha256='0'*64)),
  ('wrong_parent',lambda x:x.update(attempt_parent=P+'/wrong')),
  ('wrong_boot',lambda x:x.update(boot_id='FOREIGN-BOOT')),
  ('expired_release',lambda x:x.update(expires_unix=999)),
  ('too_distant_release',lambda x:x.update(expires_unix=1601)),
  ('source_drift',lambda x:x['source_sha256'].update({'native_diagnostic.py':'0'*64})),
  ('self_review',lambda x:x.update(author='TESTONLY-independent-reviewer')),
  ('unreviewed',lambda x:x['independent_review'].update(status='FAIL'))]:
  x=copy.deepcopy(proto);mut(x)
  if name!='unreviewed':review(x)
  check('release_'+name,lambda x=x:release_call(x),True)
 old=g.EXTERNAL_CAPTURE_BINDING;g.EXTERNAL_CAPTURE_BINDING=None
 try:check('release_unbound_external_capture',lambda:release_call(copy.deepcopy(proto)),True)
 finally:g.EXTERNAL_CAPTURE_BINDING=old
 x=copy.deepcopy(proto);x['nonce']='FOREIGN-NONCE';review(x)
 seq[0]+=1;p=F/('TESTONLY-wrong-nonce-'+str(seq[0])+'.json');raw=json.dumps(x).encode();p.write_bytes(raw)
 check('release_wrong_nonce',lambda:g.validate_release(str(p),digest(raw),M,proto['nonce'],P,clock=lambda:1000,boot_id='TESTONLY-BOOT-NOT-LIVE'),True)
 report['families'].append(dict(name='actual_validate_release',status='PASS',qualification='All author/review/boot/time data TESTONLY and isolated; actual source/archive/hash functions execute; no live execution authority published'))
 # Family3: production prelaunch statements; privileged uid/limits cannot execute as UID1000.
 # Omit exactly those3 original admission need-statements, do not substitute mocked successes.
 # Every remaining prefix statement is copied AST-identically and executes with real filepin/imports/argv guards.
 ctl=D/'capture_root_LONG.NOT-RELEASED.py';q=load(ctl,'actual_controller_prefix');tree=ast.parse(ctl.read_bytes());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');prefix=[];omitted=[]
 for n in main.body:
  if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='mkdir':break
  segment=ast.get_source_segment(ctl.read_text(),n)
  if "os.getuid()==os.geteuid()==0" in segment or 'resource.getrlimit(' in segment:
   omitted.append(segment);continue
  prefix.append(n)
 assert len(omitted)==3
 prefix.append(ast.Return(value=ast.Name(id='r',ctx=ast.Load())))
 fn=ast.FunctionDef(name='actual_unprivileged_prefix',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=prefix,decorator_list=[])
 code=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));exec(compile(code,str(ctl),'exec'),q.__dict__)
 req=json.loads((D/'CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());req.update(status='TESTONLY-CONTROLLER-PREFIX-NO-LAUNCH',capture_directory=str(F/'actual-capture-1'));req['long_profile_release']['sha256']=digest(json.dumps(proto).encode());req['argv'][-1]=req['long_profile_release']['sha256']
 count=[0]
 def prefix_call(x):
  count[0]+=1;p=F/('TESTONLY-controller-'+str(count[0])+'.json');raw=json.dumps(x).encode();p.write_bytes(raw);saved=sys.argv;sys.argv=[str(ctl),str(p),digest(raw)]
  try:return q.actual_unprivileged_prefix()
  finally:sys.argv=saved
 check('actual_controller_prefix_source_request_longargv',lambda:prefix_call(copy.deepcopy(req)))
 for name,mut in [
  ('tiny60s',lambda x:x.update(soft_wall_seconds=60)),
  ('system_python38_argv',lambda x:x['argv'].__setitem__(10,'/usr/bin/python3')),
  ('owner_source_drift',lambda x:x['command_source'].update(sha256='0'*64)),
  ('owner_path_drift',lambda x:x['command_source'].update(path=str(S/'native_diagnostic_runner.py'))),
  ('manifest_path',lambda x:x['argv'].__setitem__(x['argv'].index('--manifest')+1,'/foreign')),
  ('manifest_digest',lambda x:x['argv'].__setitem__(x['argv'].index('--manifest-sha256')+1,'0'*64)),
  ('nonce',lambda x:x['argv'].__setitem__(x['argv'].index('--nonce')+1,'foreign')),
  ('release_path',lambda x:x['long_profile_release'].update(path='/foreign')),
  ('release_digest_argv_mismatch',lambda x:x['argv'].__setitem__(-1,'0'*64)),
  ('capture_wrong_parent',lambda x:x.update(capture_directory=str(D/'actual-capture-1'))),
  ('capture_wrong_name',lambda x:x.update(capture_directory=str(F/'foreign'))),
  ('wrapper_digest',lambda x:x.update(wrapper_sha256='0'*64))]:
  x=copy.deepcopy(req);mut(x);check('controller_'+name,lambda x=x:prefix_call(x),True)
 report['families'].append(dict(name='actual_controller_prefix',status='PASS',privileged_statements_omitted=omitted,qualification='No mocked UID/rlimit checks. These3 privileged guards are preserved byte-identically but not executed here. All other actual main statements through capturepath guard run; execution stops before mkdir/Popen/signals.'))
 # Family4: real terminal children, actual bounded_command/CommandChild.wait/ledger retirement.
 children=[]
 for label,tail,expected in [('exit0','raise SystemExit(0)',0),('nonzero37','raise SystemExit(37)',37),('signaledTERM','os.kill(os.getpid(),signal.SIGTERM)',-15)]:
  ledger=o.CommandLedger();argv=[PYTHON,'-I','-B','-c',"import os,signal,time;time.sleep(.03);os.write(1,b'fixture-out');os.write(2,b'fixture-err');"+tail]
  result=o.bounded_command(argv,timeout=3,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},ledger=ledger);record=result.command_record
  assert result.returncode==expected and result.stdout==b'fixture-out' and result.stderr==b'fixture-err'
  assert record['reaped'] and record['returncode']==expected and record['pid']==record['pgid'] and record['proc_starttime']>0
  try:os.waitpid(record['pid'],os.WNOHANG)
  except ChildProcessError:pass
  else:raise AssertionError('child not ECHILD')
  try:os.getpgid(record['pid'])
  except ProcessLookupError:pass
  else:raise AssertionError('child identity not absent')
  assert not ledger.pending and not ledger.errors and not ledger.final_reap_records
  ledger.retire_pending(timeout=.1);snapshot=ledger.peek_final_reap_records();ledger.ack_final_reap_records(snapshot);assert snapshot==() and not ledger.pending and not ledger.final_reap_records
  children.append(dict(case=label,record=record,returncode=result.returncode,stdout=result.stdout.decode(),stderr=result.stderr.decode(),echild=True,identity_absent=True,pending_ledger=0))
  check('actual_Anaconda_wait_'+label,lambda:None)
 report['families'].append(dict(name='actual_Anaconda_terminal_child_waits',status='PASS',children=children,wait_implementation='Unmodified actual CommandChild.wait/bounded_command; no wrapper or substitute',all_reaped_ECHILD=True))
 report.update(status='PASS_FOUR_ACTUAL_LONG_CONSUMER_FAMILIES_NOT_NATIVE_ACCEPTANCE',seconds=time.monotonic()-begin)
except BaseException:
 report.update(status='FAIL_FIRST_CANDIDATE_PRESERVED',traceback=traceback.format_exc(),seconds=time.monotonic()-begin)
(D/'ACTUAL-LONG-CONSUMER-RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,sort_keys=True))
if report['status'].startswith('FAIL'):raise SystemExit(1)
