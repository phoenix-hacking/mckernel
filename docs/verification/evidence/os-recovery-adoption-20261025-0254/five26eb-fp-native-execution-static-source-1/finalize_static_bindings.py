"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only exact26eb composition binding and real namespace-aware manifest check.
No scratch stage, nonce, clock/resource/account query, Docker or guest.
"""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json
A=Path(__file__).resolve().parent;E=A.parent
OWNER=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/runtime-provider-rebind-1/native/native_diagnostic_container_owner.py')

def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def artifact(p):
 r=ref(p);return dict(path=r['path'],size=r['bytes'],sha256=r['sha256'],mode=p.stat().st_mode)
def write(p,value):
 with p.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def validate(manifest,result,acceptance):
 assert acceptance['decision']=='PASS_ACTUAL_OFFLINE_26EB_FP_COMPOSITION' and acceptance['independent'] is True and acceptance['implementation_ownership'] is False
 assert acceptance['manifest']==ref(manifest) and acceptance['result']==ref(result)
 m=json.loads(manifest.read_bytes());r=json.loads(result.read_bytes())
 assert r['manifest']==artifact(manifest) and r['image']==m['artifacts']['mckernel_image']
 assert r['changed_base_records']==['images/mckernel.img'] and r['guest_runs']==0 and r['runtime_authority'] is None
 assert m['case_id']=='practical.rust-std.fp-thread-state' and m['artifacts']['mckernel_image']['sha256']=='26eb201ab8160b98e9a95ac3bae116a6392f343faf60641bb62faa7116a793eb'
 assert m['artifacts']['payload']['sha256']=='3488648514aa2d8d5eacfdbdd111ad33f17c2abccfff4755f3ebcefef45ec583'
 assert len(bytes.fromhex(m['payload']['oracle']['stdout_hex']))==254 and m['payload']['oracle']['exit_code']==0 and m['payload']['oracle']['stderr_hex']==''
 assert [x['sha256'] for x in m['modules']]==['daced2910f2391f15f1963399838c5089ef7ac6be8f6614db88ff8443c48900c','887dc3567e6035c921588e61b45b41a8ef32a972d142fe2ba82ec48442353b12','57546af5110c0674b307e5ac5a328228abbe784f890f69521db5f594f21f6ae8']
 # Literal actual004 same-path bind map of unchanged owner45010; no assumed
 # visibility merely because a host path exists. No new mount is introduced.
 assert hashlib.sha256(OWNER.read_bytes()).hexdigest()=='45010e54e1f78e3efcd6572b71342ee6078abeea98961f2c5d49849575dd5048'
 actual=E/'f42-fp-readonly-artifact-path-correction-source-1/ACTUAL-004-CREATE.json'
 assert ref(actual)['sha256']=='973ee413e09a5b97574fa0e3894585e5021904867050234d3c35a1e41136eddc'
 argv=json.loads(actual.read_bytes())['argv'];mounts=[]
 for i,arg in enumerate(argv):
  if arg=='--mount':
   fields=argv[i+1].split(',');d=dict(x.split('=',1) for x in fields if '=' in x);assert d['src']==d['dst'];d['readonly']='readonly' in fields;d['directory']=Path(d['src']).is_dir();mounts.append(d)
 coverage=[]
 def visible(path):
  p=Path(path);matches=[d for d in mounts if p==Path(d['dst']) or (d['directory'] and Path(d['dst']) in p.parents)]
  assert matches,'outside actual owner exports: '+path
  d=max(matches,key=lambda x:len(Path(x['dst']).parts));assert d['readonly'] and str(p.resolve(strict=True))==path
  coverage.append(dict(path=path,readonly_export=d['src']))
 def walk(obj):
  if isinstance(obj,dict):
   if {'path','size','sha256','mode'}<=set(obj):visible(obj['path'])
   for x in obj.values():walk(x)
  elif isinstance(obj,list):
   for x in obj:walk(x)
 walk(m);visible(str(manifest));overlay=json.loads(Path(m['staging']['overlay_manifest']['path']).read_bytes())
 for row in overlay['sources'].values():visible(row['path'])
 assert len(coverage)==27
 source=OWNER.with_name('native_diagnostic.py');assert ref(source)['sha256']=='f368324242bfdfb0ad1f3f524a906dcf51730ef0beb311315e6b66f5d585748c'
 spec=importlib.util.spec_from_file_location('real26eb_manifest_preflight',source);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
 realref=v._ref;realidentity=v._identity
 def namespace_ref(r,n):visible(r['path']);return realref(r,n)
 def namespace_identity(path):visible(path);return realidentity(path)
 v._ref=namespace_ref;v._identity=namespace_identity;v.load_manifest(str(manifest))
 return m,r,coverage[:27]

def main():
 p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--composition-result',required=True,type=Path);p.add_argument('--offline-acceptance',required=True,type=Path);p.add_argument('--check-only',action='store_true');a=p.parse_args()
 b=json.loads((A/'STATIC-NATIVE-BINDINGS.PROPOSAL.NOT-RELEASED.json').read_bytes());assert ref(a.offline_acceptance)==b['proposed_offline_acceptance']
 m,r,coverage=validate(a.manifest,a.composition_result,json.loads(a.offline_acceptance.read_bytes()))
 assert m['payload']['oracle']==b['expected_oracle'] and m['payload']['argv']==b['expected_guest_argv']
 proof=dict(scope=__doc__.splitlines()[0],status='PASS_LITERAL_26EB_FINALIZER_REAL_MANIFEST_AND_ALL27_READONLY_EXPORTS',manifest=ref(a.manifest),composition=ref(a.composition_result),offline_acceptance=ref(a.offline_acceptance),coverage=coverage,runtime_authority=None,stage_performed=False,nonce=None)
 if a.check_only:print(json.dumps(proof));return
 b.update(status='STATIC_ACTUAL26EB_FP_ONLY_NO_STAGE_NONCE_CLOCK_OR_RELEASE',offline_manifest=ref(a.manifest),payload=ref(Path(m['artifacts']['payload']['path'])),overlay=ref(Path(m['staging']['derived_initramfs']['path'])),overlay_manifest=ref(Path(m['staging']['overlay_manifest']['path'])),offline_stage_binding=ref(a.composition_result),offline_composition_acceptance=ref(a.offline_acceptance),latest_serial_operation_artifact_acceptance=b['artifact_acceptance'])
 b['frozen_runtime_refs']={name:ref(Path(r['path'])) for name,r in m['artifacts'].items()};b['frozen_runtime_refs']['collector']=ref(Path(m['staging']['collector']['path']));b['module_refs']=[ref(Path(r['path'])) for r in m['modules']]
 write(A/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',b);write(A/'STATIC-FINALIZATION.PROOF.json',proof)
 print(json.dumps(dict(status='STATIC_FINALIZED_NO_STAGE_NONCE_OR_RELEASE',template=ref(A/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json'),proof=ref(A/'STATIC-FINALIZATION.PROOF.json'),runtime_authority=None)))
if __name__=='__main__':main()
