"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Static overlay packaging only. No compiler, guest, admission or root mutation.
"""
import hashlib,importlib.util,json,pathlib,time
E=pathlib.Path(__file__).resolve().parent

def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def ref(p):
 p=pathlib.Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'size':len(b),'mode':p.stat().st_mode}

def save(p,d):
 with p.open('x') as f:f.write(json.dumps(d,indent=2)+'\n')
started=time.time()
plan=json.loads((E/'NEXT-CORE-MEMORY-SOURCE-PLAN.json').read_text());m=plan['manifest_postimage_before_staging']
compiled=ref(E/'init');assert compiled['sha256']=='70a6de490cf025e79cf7ea3e815ee4f8bfff61d8cf2e9ed493317db829af3a39'
old=json.loads(pathlib.Path('/home/holden/mckernel-work/scratch/n290startup2/startup-overlay.json').read_text())
overlay_source=pathlib.Path(m['staging']['overlay_source']['path'])
assert ref(overlay_source)==m['staging']['overlay_source']
over=module('f05_existing_overlay',overlay_source)
output=E/'memory.cpio.gz';receipt=E/'memory-overlay.json'
if output.exists():
 assert receipt.is_file(),'Prior output has no receipt; preserve and stop'
 result=json.loads(receipt.read_text());assert ref(output)['sha256']==result['output_sha256']
else:
 result=over.build_overlay(m['artifacts']['initramfs']['path'],m['artifacts']['payload']['path'],str(E/'init'),m['artifacts']['mcexec']['path'],str(output),collector_sha256=compiled['sha256'],mcexec_sha256=m['artifacts']['mcexec']['sha256'],payload_sha256=m['artifacts']['payload']['sha256'],base_sha256=old['base_sha256'],base_size=m['artifacts']['initramfs']['size'],base_cpio_sha256=old['base_cpio_sha256'],base_cpio_size=old['base_cpio_size'])
 save(receipt,result)
m['staging']['collector']=compiled;m['staging']['derived_initramfs']=ref(output);m['staging']['overlay_manifest']=ref(receipt)
manifest=E/'memory-manifest.json'
if manifest.exists():assert json.loads(manifest.read_text())==m
else:save(manifest,m)
validator=pathlib.Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/runtime-provider-rebind-1/native/native_diagnostic.py')
nd=module('f05_existing_native_validator',validator);validated=nd.load_manifest(str(manifest))
assert validated['case_id']=='baseline.core.memory'
ready={'scope':__doc__.strip(),'status':'PASS_STATIC_MEMORY_OVERLAY_AND_EXISTING_NATIVE_MANIFEST_VALIDATOR_ONLY','started_at':started,'finished_at':time.time(),'manifest':ref(manifest),'overlay':ref(output),'overlay_receipt':ref(receipt),'collector':compiled,'validator':ref(validator),'image':m['artifacts']['mckernel_image'],'modules':m['modules'],'payload':m['artifacts']['payload'],'payload_contract':m['payload'],'native_execution':False,'admission':None,'unresolved_root_fields':['Fresh Root-admitted nonce and fresh attempt-parent','Latest accepted physical/resource/common/shared ownership proof after growth FD closure','Independent execution release binding this exact manifest and unchanged owner/profile','Static publication/fetched checkpoint before fresh admission clock'],'next_owner_template':plan['native_invocation_template']}
ready['next_owner_template'][-3]=str(manifest);ready['next_owner_template'][-1]=ready['manifest']['sha256']
p=E/'STATIC-MEMORY-READY.json'
if not p.exists():save(p,ready)
print(json.dumps({k:ready[k] for k in ['status','manifest','overlay','collector','native_execution']}))
