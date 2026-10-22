"""Bound current launcher component bodies on genuine saved evidence; no root/census.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
from datetime import datetime
import ast,copy,hashlib,json,os,re,stat
PINS = {'case': {'path': '/home/holden/mckernel-work/host-preparation/native-exec-delivery-transfer-rust-repair-20261021-1/launcher-error-propagation-1/target-build-preparation-1/postbuild-terminal-preparation-1/actual-current-binding-1/generated-source-1/LAUNCHER-CASE-STATIC.json', 'sha256': '0c1946f4f0bd33113cac3f7848e570719756f41ef756a496a2ebae6735b68c9c', 'bytes': 61564}, 'engine': {'path': '/home/holden/mckernel-work/host-preparation/native-exec-delivery-transfer-rust-repair-20261021-1/launcher-error-propagation-1/target-build-preparation-1/postbuild-terminal-preparation-1/actual-current-binding-1/generated-source-1/cleanup_launcher.py', 'sha256': '4fe17a2e23ab840742a8db812dc7dc7fbd6d345e392c49a6cac8b0029b5531c4', 'bytes': 99128}, 'observer': {'path': '/home/holden/mckernel-work/host-preparation/native-exec-delivery-transfer-rust-repair-20261021-1/launcher-error-propagation-1/target-build-preparation-1/postbuild-terminal-preparation-1/actual-current-binding-1/generated-source-1/observe_current_launcher_retirement.py', 'sha256': 'bc0b1b28b491a237b8163eb03a3b00bf5658b71888d5efeeb70e8f50920c17bc', 'bytes': 29302}, 'retirement': {'bytes': 7619, 'path': '/home/holden/mckernel-work/host-preparation/native-exec-delivery-transfer-rust-repair-20261021-1/launcher-error-propagation-1/target-build-preparation-1/postbuild-terminal-preparation-1/actual-current-binding-1/ROOT-MECHANICAL-CURRENT-RETAINED-CONSUMER.json', 'sha256': 'c3ce098ba01d78e02da06933cdce8d1484221ecaced8658a28862a6459d1148e'}, 'artifact': {'bytes': 6685, 'path': '/home/holden/mckernel-work/host-preparation/current-focused-progress-recording-20261021-1/current-normalization-review-recording-1/ROOT-MECHANICAL-CURRENT-C9-LAUNCHER-ARTIFACT-CONSUMER-1.json', 'sha256': 'c8a734c59b070d8bc79b01dbf5c05ee726d073e60bfa7088cd77b7027741a764'}, 'postjoin': {'bytes': 1470, 'path': '/home/holden/mckernel-work/host-preparation/native-exec-delivery-transfer-rust-repair-20261021-1/launcher-error-propagation-1/target-build-preparation-1/latest-native12-release-binding-preparation-1/image-guard-postjoin-readback.json', 'sha256': 'c13ef4140fb24ed00d68287b9b94c5fe074e9c583f7868f3bfe5c2a89c616978'}, 'terminal_inspect': {'bytes': 16382, 'path': '/home/holden/mckernel-work/scratch/native-rust-launcher-sentinel-guard-122b155b78be4c01abd3a51a525236f4/inspect-terminal-fresh.json', 'sha256': 'fd1922902d01b27f97963b801da5114cf057d3501b11b0e44d46d0fbe1a563d6'}}
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
 en=dict(Path=Path,os=os,stat=stat,json=json,hashlib=hashlib,re=re,Refusal=Refusal,DOCUMENT_LIMIT=256<<20,PROTECTED_LIMIT=128<<20)
 for node in ast.parse(engine).body:
  if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id in ('SOURCE_REFS','CURRENT_LAUNCHER_PLAN','KNOWN_TARGET','REQUEST_SHA')for t in node.targets):
   exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual bound engine constants>','exec'),en)
 en['REQUEST']=Path(case['request']['path'])
 for name in ('digest','canonical','parse','identity','directory','read_bounded','validate_attempt_binding','image_layout'):function(engine,name,en)
 request=json.loads(Path(case['request']['path']).read_bytes())
 en['validate_attempt_binding'](case['target'],case['request'])
 args,mounts=en['image_layout'](request);item=json.loads(read('terminal_inspect'))
 assert type(item)is dict and item['Id']==case['target']['container_id']
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
