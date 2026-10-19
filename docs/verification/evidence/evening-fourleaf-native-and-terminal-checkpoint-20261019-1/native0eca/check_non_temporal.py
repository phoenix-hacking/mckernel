"""One ordinary non-temporal interface check only. No source oracle, owner or root call."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,stat
N=Path(__file__).resolve().parent
PINS={'execution-proposal.json': {'path': '/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/native-final-preparation-1/execution-proposal.json', 'sha256': '36af9a2e31bedf70e2e6cbb88bfefe9a706d438f633c3f3d86e2683a2e2d1ff4', 'size': 15881, 'mode': 33152}, 'conditional-metadata.json': {'path': '/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/native-final-preparation-1/conditional-metadata.json', 'sha256': '33709374a425c75e3dfd5060f65952471cfdc0f24674e2379815ec2d2fec1914', 'size': 4914, 'mode': 33152}, 'machine-release-PENDING.json': {'path': '/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/native-final-preparation-1/machine-release-PENDING.json', 'sha256': 'd9aa7c1358fcfc01e8e30032fe260b38ab7539436123990be3dcc46f092a9b3f', 'size': 1190, 'mode': 33152}, 'snapshot-static-bindings.json': {'path': '/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/native-final-preparation-1/snapshot-static-bindings.json', 'sha256': '6ac23782fff379bc7fb53332aeeb6bd404944e691e8ddce462ddb1e982491cb3', 'size': 4808, 'mode': 33152}, 'dispatch-runtime.py': {'path': '/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/native-final-preparation-1/dispatch-runtime.py', 'sha256': '108d7f1f02ab46f60b9e0b908d75eb83aac23ab67c088b36b3b357ad81e59926', 'size': 5881, 'mode': 33152}, 'root_manual_snapshot.py': {'path': '/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/native-final-preparation-1/root_manual_snapshot.py', 'sha256': 'e96adbe0e4316c51fba19d5f4deb9a394a85afca34452bd1b3ac9d53f7d1683d', 'size': 8099, 'mode': 33152}, 'assemble_final_data.py': {'path': '/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/native-final-preparation-1/assemble_final_data.py', 'sha256': 'fd4c161ca4d0bf1a82287b9b533c14cddf8b5f5dfd96548d6072a879e9a53594', 'size': 3910, 'mode': 33152}}
def checked(r):
 raw=Path(r['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256'];return json.loads(raw)
def main():
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7}and resource.getrlimit(resource.RLIMIT_AS)[0]<=1073741824
 for r in PINS.values():assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
 proposal=checked(PINS['execution-proposal.json']);meta=checked(PINS['conditional-metadata.json']);machine=checked(PINS['machine-release-PENDING.json']);binding=checked(PINS['snapshot-static-bindings.json'])
 assert meta['proposal']==PINS['execution-proposal.json']and meta['runtime_wrapper']==PINS['dispatch-runtime.py']and machine['conditional_metadata_release']==PINS['conditional-metadata.json']
 assert binding['proposal']==PINS['execution-proposal.json']and binding['metadata']==PINS['conditional-metadata.json']and binding['runtime_wrapper']==PINS['dispatch-runtime.py']and binding['machine_template']==PINS['machine-release-PENDING.json']
 ordinary=checked(binding['ordinary_acceptance']);assert ordinary['decision']=='PASS_ACTUAL_METADATA_PROJECTION_FIXTURE_AND_FRESH_PARENT'
 manifest=checked(binding['manifest']);assert manifest['payload']==proposal['payload_contract']and manifest['artifacts']['mckernel_image']==proposal['mckernel_image']
 assert manifest['artifacts']['payload']==proposal['payload']and manifest['staging']['overlay_manifest']==proposal['consumer_overlay_metadata']
 assert proposal['mckernel_image']['sha256']=='0eca91b13bd62ab98441104930eda1a63f247fecd939996858b16f90b7480550'and proposal['profile']['mckernel_cpus']==1
 parent=Path(proposal['parent']['path']);s=parent.lstat();identity=dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)))
 assert identity==proposal['parent']['identity']==binding['parent_identity']==meta['parent_identity']and parent.resolve(strict=True)==parent and not list(parent.iterdir())
 assert all(len(e['path'].encode())==e['encoded_bytes']<=107 for e in proposal['unix_monitor_endpoints'])
 assert proposal['argv']==['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3','-B',proposal['owner']['path'],'--attempt-parent',str(parent),'--nonce',proposal['nonce'],'--owner-sha256',proposal['owner']['sha256'],'--manifest',proposal['manifest']['path'],'--manifest-sha256',proposal['manifest']['sha256']]
 for name in ['dispatch-runtime.py','root_manual_snapshot.py','assemble_final_data.py']:
  spec=importlib.util.spec_from_file_location('non_temporal_'+name.replace('.','_'),N/name);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  if name=='dispatch-runtime.py':assert module.EXPECTED_PARENT_IDENTITY==identity
  if name!='dispatch-runtime.py':assert module.BINDING_SHA256==PINS['snapshot-static-bindings.json']['sha256']
 result=dict(status='PASS_NON_TEMPORAL_FOURLEAF_NATIVE_INTERFACE_ONLY',source_files=3,binding_graph=True,parent_identity=identity,endpoint_bytes=proposal['unix_monitor_endpoints'][0]['encoded_bytes'],mckernel_cpus=1,root_or_guest_invoked=False,passed_app_oracle_replayed=False,runtime_release=False)
 with(N/'non-temporal-check-result.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result))
if __name__=='__main__':main()
