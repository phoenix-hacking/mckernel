"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,runpy,sys,traceback
H=Path(__file__).resolve().parent;S=H/'source';records=[]
def load(name):
 p=S/(name+'.py');spec=importlib.util.spec_from_file_location('merged_'+name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
try:
 assert sys.version_info[:2]==(3,8)and os.getuid()==os.geteuid()==1000 and not hasattr(os,'waitstatus_to_exitcode')
 runpy.run_path(str(H/'check_direct_consumer.py'),run_name='__main__');wait=json.loads((H/'DIRECT-CONSUMER-RESULT.json').read_text());assert wait['status'].startswith('PASS_3');records.append(dict(case='actual_CommandChild_wait_0_37_SIGTERM',result=wait['status']))
 o=load('native_diagnostic_container_owner');d=load('native_diagnostic');t=load('long_transport')
 assert d.BEGIN_CLEANUP_SOURCE_REFS['provider']['sha256']=='f5c56d83a13f10a712a4555849f52078c2d410254080150d34408011daf527a5';assert d.BEGIN_CLEANUP_SOURCE_REFS['consumer']['sha256']=='8bf30cd8ae79cc778bd91816f30aaf7a37ccc2aab59822ca2a03587426a212b8'
 m=json.loads(Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/next-stage-preparation-1/source-ready-1/case-235/ACTUAL-V3-NATIVE235-MANIFEST.json').read_text());original=d._legacy_cleanup_validate_manifest;d._legacy_cleanup_validate_manifest=lambda obj:dict(obj)
 obj=dict(case_id=m['case_id'],modules=m['modules'],cleanup_profile=m['cleanup_profile'],pair={},pair_long_session=dict(t.PROFILE));checked=d._validate_manifest(obj);assert checked['cleanup_profile']==m['cleanup_profile']and checked['pair_long_session']==t.PROFILE;assert d._begin_cleanup_enabled(checked)and d._begin_process_case(checked);d._legacy_cleanup_validate_manifest=original;records.append(dict(case='real_BEGIN_source_profile_and_LONG_wrapper_composition',controlled_adapter='legacybasevalidator only; actualcurrentcleanup/sourcechecks and actuallongtypedprofilepredicate run'))
 serial='terminal\napplication_process=cleanup_requested os=0 generation=1 pid=7 intent_errno=0\napplication cleanup ACK os=0 generation=1 pid=7 token=9 errno=0 abandoned=0\napplication retirement os=0 generation=1 pid=7 token=10 errno=0\n';ack=d._check_begin_cleanup(serial,'os=0 generation=1 pid=7',0);assert ack==dict(entry_token=9,query_tokens=[10]);rejected=False
 try:d._check_begin_cleanup(serial.replace('application cleanup ACK os=0 generation=1 pid=7 token=9 errno=0 abandoned=0\n',''),'os=0 generation=1 pid=7',0)
 except ValueError:rejected=True
 assert rejected;records.append(dict(case='real_ACK_required',valid_ACK=ack,missing_ACK_rejected=rejected))
 owner=o.DiagnosticOwner.__new__(o.DiagnosticOwner);owner.name='controlled';owner.label='controlled=fixture';owner.parent=H;owner.owner_sha='0'*64;owner.manifest_path=str(H/'controlled-manifest');owner.manifest_sha256='1'*64;owner.nonce='2'*32;owner.long_release=str(H/'controlled-release');owner.long_release_sha='3'*64
 for mode in (False,True):
  owner.long_requested=mode;argv=owner._create_argv();assert ('--log-driver=none'in argv)is mode;assert ('fsize={0}:{0}'.format(t.file_limit(mode)))in argv;assert any('src='+str(S)+',dst='+str(S)+',readonly'==arg[len('type=bind,'):]for arg in argv if arg.startswith('type=bind,'));assert '--network=none'in argv and '--cpuset-cpus=2-5'in argv and '--memory=12g'in argv;records.append(dict(case='actual_NONE_create_argv_LONG'if mode else'actual_SHORT_create_argv',none_driver=mode,file_bytes=t.file_limit(mode)))
 calls=[];owner._call=lambda *a,**kw:calls.append((a,kw));owner.long_requested=True;assert owner._capture_logs(1)is None and calls==[];owner.long_requested=False;owner.container='controlledCID';owner._capture_logs(1);assert calls[0][0][0]==['logs','--timestamps','controlledCID'];records.append(dict(case='NONE_no_logs_and_SHORT_logs_preserved'))
 lifecycle=d.exercise_lifecycle;build=d.build_command;observed=[];d.exercise_lifecycle=lambda *a,**kw:observed.append(kw)or{'controlled':True};d.build_command=lambda manifest,attempt:dict(runtime_ready=True,manifest=manifest,argv=['controlled'])
 for mode in (False,True):
  manifest={'pair':{},'pair_long_session':dict(t.PROFILE)}if mode else{};d.run_diagnostic(manifest,H,lambda:None,lambda:None,timeout=7800 if mode else 300);assert ('long_profile'in observed[-1])is mode
 d.exercise_lifecycle=lifecycle;d.build_command=build;records.append(dict(case='actual_LONG_SHORT_run_dispatch',controlled_adapter='commandplan/lifecycle endpoints only; no QEMU/processfactory called'))
 assert t.TRANSPORT['logical_growth_bytes']==4294967296 and t.DOCKER_LOG==dict(Type='none',Config={});records.append(dict(case='accepted_NONE_4GiB_accounting'))
 result=dict(scope=__doc__,status='PASS_PRIVATE_MERGED_PYTHON38_ACTUAL_CONSUMERS_AND_CONTROLLED_HOOKS',python=sys.version,cases=records,root=0,Docker=0,guest=0,compiler=0)
except BaseException:
 result=dict(scope=__doc__,status='FAIL_FIRST_CANDIDATE_PRESERVED',python=sys.version,cases=records,traceback=traceback.format_exc(),root=0,Docker=0,guest=0,compiler=0)
with(H/'MERGED-FIXTURE-RESULT.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result));raise SystemExit(0 if result['status'].startswith('PASS')else 1)
