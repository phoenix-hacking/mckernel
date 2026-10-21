"""Bound current launcher component bodies on genuine saved evidence; no root/census.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
from datetime import datetime
import ast,copy,hashlib,json,os,stat
PINS = {'case': {'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-terminal-data-preparation-1/actual-binding-1/generated-source-1/LAUNCHER-CASE-STATIC.json', 'sha256': '3a943240ee686b3c95e2ffca0cd166fe3edf141b63135eea903fbbfa179f60e9', 'bytes': 56135}, 'engine': {'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-terminal-data-preparation-1/actual-binding-1/generated-source-1/cleanup_launcher.py', 'sha256': '08d8673089544abbbd9a1e09812c638928b026a85e4292d267068c62d5018326', 'bytes': 98419}, 'observer': {'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-terminal-data-preparation-1/actual-binding-1/generated-source-1/observe_current_launcher_retirement.py', 'sha256': '120e130bdf6cfc1d0a0c9fd4e9ee50d6b1eebf3782a1b56870d8da9a123623b7', 'bytes': 29002}, 'retirement': {'bytes': 27685, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-build-review-1/retained-terminal-review-1/ACTUAL-LAUNCHER-RETAINED-TERMINAL-ACCEPTANCE-1.json', 'sha256': '7c90716bcdc6f5e20c6b1aca78c466082893593863152c6e0371e440718605c7'}, 'artifact': {'bytes': 6879, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-artifact-acceptance-1/ROOT-RECORDED-INDEPENDENT-LAUNCHER-ARTIFACT-ACCEPTANCE-1.json', 'sha256': 'a969204e4d7e20281927287952ae2fe5a50366d15813151ad71e4592f5801917'}, 'postjoin': {'bytes': 542, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/launcher-sentinel-successor-preparation-1/correction-1/guard-correction-1/image-guard-postjoin-readback.json', 'sha256': '2a98c96829559293a47864f0771e3d3f789110926ae0863dd044d943aca87104'}, 'terminal_inspect': {'bytes': 16306, 'path': '/home/holden/mckernel-work/scratch/native-rust-launcher-sentinel-guard-b619cde3076741bc84da4e43edfe0544/inspect-terminal-fresh.json', 'sha256': 'f4d1f16ecc9eac0c53098e2ec5a8bc17439d44ec2096edccc5e4dc65c4afaaf3'}}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(name):
 row=PINS[name];raw=Path(row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256'];return raw
def function(source,name,namespace):
 t=ast.parse(source);n=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[n],type_ignores=[]),'<actual-whole-function:'+name+'>','exec'),namespace)
 return namespace[name]

def main():
 case=json.loads(read('case'));observer=read('observer').decode();engine=read('engine').decode()
 retirement=json.loads(read('retirement'));artifact=json.loads(read('artifact'));postjoin=json.loads(read('postjoin'))
 def need(ok,reason):
  if not ok:raise ValueError(reason)
 ns=dict(Path=Path,os=os,stat=stat,json=json,hashlib=hashlib,datetime=datetime,need=need)
 for name in ('sha','stable_bytes'):function(observer,name,ns)
 for node in ast.parse(observer).body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name)and t.id in ('BOOT','PIDS','CURRENT_EXPECTED_SOURCE')for t in node.targets):
   exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual bound observer constants>','exec'),ns)
 validate=function(observer,'current_pass_prerequisites',ns)
 validate(retirement,case,postjoin,artifact)
 class Refusal(ValueError):pass
 en=dict(Path=Path,os=os,stat=stat,json=json,hashlib=hashlib,Refusal=Refusal,DOCUMENT_LIMIT=256<<20,PROTECTED_LIMIT=128<<20)
 for node in ast.parse(engine).body:
  if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id in ('SOURCE_REFS','CURRENT_LAUNCHER_PLAN','KNOWN_TARGET','REQUEST_SHA')for t in node.targets):
   exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual bound engine constants>','exec'),en)
 en['REQUEST']=Path(case['request']['path'])
 for name in ('digest','canonical','parse','identity','directory','read_bounded','validate_attempt_binding','image_layout'):function(engine,name,en)
 request=json.loads(Path(case['request']['path']).read_bytes())
 en['validate_attempt_binding'](case['target'],case['request'])
 args,mounts=en['image_layout'](request);item=json.loads(read('terminal_inspect'))[0]
 actual=sorted((m['Destination'],m['Source'],m['Type'],m['RW'])for m in item['Mounts']if m['Type']=='bind')
 assert mounts==actual and args==item['Config']['Cmd']==item['Args']
 refusals=[]
 for label,changed_retirement,changed_case in [('count',retirement,dict(case,closed_saved_host_client_count=7)),('tool-session',retirement,dict(case,controller_terminal_expected=[case['controller_terminal_expected'][0],'wrong-session',case['controller_terminal_expected'][2]])),('unobserved-outer-group',dict(retirement,outer_group_observation={}),case)]:
  try:validate(changed_retirement,changed_case,postjoin,artifact)
  except (ValueError,KeyError,TypeError):refusals.append(label)
  else:raise AssertionError('accepted changed component boundary:'+label)
 wrong=copy.deepcopy(request);wrong['launcher_plan']['sha256']='0'*64
 try:en['image_layout'](wrong)
 except Refusal:refusals.append('wrong-launcher-plan')
 else:raise AssertionError('accepted changed launcher plan')
 print(json.dumps(dict(status='PASS_ACTUAL_CURRENT_LAUNCHER_CONSUMER_BODY_JOINS_ONLY',positive_actual_retained_artifact_controller_and_source_joins=True,actual_client_count=len(ns['PIDS']),exact_saved_mounts_and_command=True,changed_boundary_refusals=refusals,refusal_count=len(refusals),engine_imported=False,root_actions=False,census_executed=False,cleanup_executed=False,physical_clearance=False,native_acceptance=False),sort_keys=True))
if __name__=='__main__':main()
