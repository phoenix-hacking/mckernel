"""Exact M05 second-stop adapter; preserve original full raw observation.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import hashlib,importlib.util,json
from pathlib import Path
CASE_ID='native.second-stop.current68.twoCPU.exact67.two-generation'
BASE=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-first-v3-failure-1/coherent-successor-preparation-1/runtime-source-successor-1/strict-native/native_diagnostic.py')
BASE_SHA='f4c3db94bb9de130577be73f3a1cda1d8ef18b3ec8941d70584751db3f5d86eb'
CONSUMER=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-first-v3-failure-1/coherent-successor-preparation-1/runtime-source-successor-1/second_stop_capture.py')
CONSUMER_SHA='4757c058a1811aecdb60d74eb312af03320dae1325e8f16ceed13ab8490be9a5'
MANIFEST=Path('/home/holden/mckernel-work/scratch/nm05h1a1/m.json')
MANIFEST_SHA='663ea9be9eea62b2cdc3fd19b1b9b7ba739e2d186cb9833cce41e1ba32933935'
ORACLE={'exit_code': 0, 'stderr_hex': '', 'stdout_hex': '68616e646c65643d31206f627365727665645f626c6f636b65643d3120726573746f7265643d310a'}


SECOND_BOOT_MEMBER={'gid': 0, 'mode': 33261, 'mtime': 0, 'nlink': 1, 'rdevmajor': 0, 'rdevminor': 0, 'sha256': '1a7fd6e3ff3d31c79c7c2665766a2b0e74bb895b2df0ebeff845b67f1dddd609', 'size': 35768, 'uid': 0}
def verify_second_boot_helper_member(nd,manifest):
 row=manifest['staging']['overlay_manifest'];raw=Path(row['path']).read_bytes()
 nd._need(hashlib.sha256(raw).hexdigest()==row['sha256']and len(raw)==row['size'],'M05 addedhelper metadata source')
 table=json.loads(raw)['final_map']
 nd._need(len(table)==62 and table.get('bin/native-boot-second')==SECOND_BOOT_MEMBER,'M05 exact addedsecondhelper/root0755/48B-proof-source hash')

def load(name,path,digest):
 if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('M05 exact source drift '+str(path))
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def binding(manifest_path,expected_sha):
 nd=load('m05_original_nd',BASE,BASE_SHA)
 try:
  nd._need(str(manifest_path)==str(MANIFEST)and expected_sha==MANIFEST_SHA,'M05 exact normalized manifest')
  nd._need(hashlib.sha256(MANIFEST.read_bytes()).hexdigest()==MANIFEST_SHA,'M05 manifest bytes')
  consumer=load('m05_strict_second_stop',CONSUMER,CONSUMER_SHA);frozen=nd.load_manifest(str(MANIFEST));verify_second_boot_helper_member(nd,frozen)
  nd._need(frozen['case_id']==CASE_ID and frozen['payload']['oracle']==ORACLE,'M05 exact case and signal oracle')
  return nd,consumer,frozen
 except Exception as error:raise nd.DiagnosticError('M05 binding: '+str(error))from error

def case_evaluate(manifest,observation):
 nd,consumer,frozen=binding(str(MANIFEST),MANIFEST_SHA)
 try:
  nd._need(nd._same_plan(nd._freeze(nd._thaw(manifest)),nd._freeze(nd._thaw(frozen))),'M05 original immutable plan changed')
  protocol=consumer.evaluate(manifest,observation)
  first=consumer.bound('workload')
  record=nd.evaluate(manifest,dict(observation,serial=first.workload_view(observation['serial'],1,manifest)))
  record['observation']=observation
  record['second_stop_protocol']=protocol
  return record
 except Exception as error:raise nd.DiagnosticError('M05 case: '+str(error))from error
