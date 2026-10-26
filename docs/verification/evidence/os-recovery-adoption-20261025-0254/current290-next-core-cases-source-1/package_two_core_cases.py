"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private HOST overlays/manifests only; scratch staging and native execution absent.
"""
import copy,hashlib,importlib.util,json,pathlib,time
E=pathlib.Path(__file__).resolve().parent;M=E.parent/'current290-m14-f05-nearest-file-closure-1'
def ref(p):
 p=pathlib.Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),size=len(b),mode=p.stat().st_mode)
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save(p,d):
 with p.open('x') as f:f.write(json.dumps(d,indent=2)+'\n')
base=json.loads((M/'memory-manifest.json').read_text());old=json.loads((M/'memory-overlay.json').read_text());over=module('next_core_existing_overlay',base['staging']['overlay_source']['path']);ndpath=pathlib.Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/runtime-provider-rebind-1/native/native_diagnostic.py');nd=module('next_core_existing_validator',ndpath)
rows=[]
for case in ['files','threads']:
 started=time.time();out=E/case;m=copy.deepcopy(base);m['case_id']='baseline.core.'+case;m['payload']['argv']=['/bin/mcexec','-t','1','0','app',case];stdout=('NATIVE_CORE PASS '+case+'\n').encode();m['payload']['oracle']=dict(exit_code=37,stderr_hex='',stdout_hex=stdout.hex());collector=ref(out/'init');compile=json.loads((out/'ACTUAL-COMPILE-RESULT.json').read_text());assert compile['returncode']==0 and compile['collector']['sha256']==collector['sha256']
 output=out/(case+'.cpio.gz');receipt=out/'overlay.json';assert not output.exists() and not receipt.exists()
 result=over.build_overlay(m['artifacts']['initramfs']['path'],m['artifacts']['payload']['path'],str(out/'init'),m['artifacts']['mcexec']['path'],str(output),collector_sha256=collector['sha256'],mcexec_sha256=m['artifacts']['mcexec']['sha256'],payload_sha256=m['artifacts']['payload']['sha256'],base_sha256=old['base_sha256'],base_size=m['artifacts']['initramfs']['size'],base_cpio_sha256=old['base_cpio_sha256'],base_cpio_size=old['base_cpio_size']);save(receipt,result)
 m['staging']['collector']=collector;m['staging']['derived_initramfs']=ref(output);m['staging']['overlay_manifest']=ref(receipt);mp=out/'manifest.HOST-STATIC.json';save(mp,m);validated=nd.load_manifest(str(mp));assert validated['case_id']==m['case_id']
 row=dict(scope=__doc__.strip(),status='PASS_HOST_OVERLAY_AND_EXISTING_MANIFEST_VALIDATOR_ONLY',case_id=m['case_id'],started_at=started,finished_at=time.time(),manifest=ref(mp),overlay=ref(output),overlay_receipt=ref(receipt),collector=collector,image=m['artifacts']['mckernel_image'],modules=m['modules'],payload=m['artifacts']['payload'],payload_contract=m['payload'],stdout_bytes=len(stdout),validator=ref(ndpath),native_execution=False,root_runtime_authority=None,scratch_staged_manifest=None,next_required='Root-authorized exclusive copy of exact manifest bytes under scratch and outside separate empty writable parent; owner _manifest_identity/_manifest_outside_writable_parent; publication then actual fresh native admission/review',owner_manifest_path_eligible=False,compiler_replay_required=False)
 save(out/'STATIC-CASE-READY.json',row);rows.append(row)
 print(json.dumps({k:row[k] for k in ['case_id','status','manifest','overlay','collector','stdout_bytes']}),flush=True)
save(E/'NEXT-NATIVE-QUEUE.SOURCE-ONLY.json',dict(scope=__doc__.strip(),status='TWO_HOST_STATIC_CASES_READY_FOR_FUTURE_SCRATCH_STAGING_NOT_NATIVE_RELEASE',cases=rows,source_parent='Existing208204ff collector presence profiles only; existing558d1607 payload, currentimagee6a82/modules',admission=None,review=None,resource_proof=None,nonce=None,one_heavy_only=True,batching_authorized=False))
