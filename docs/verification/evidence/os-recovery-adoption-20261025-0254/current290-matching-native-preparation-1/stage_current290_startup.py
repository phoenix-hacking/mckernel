"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite offline archive transform only. Reuses exact existing source consumers;
no compiler, Docker, root, IHK, guest, subprocess or native cleanup operation.
"""
import argparse,contextlib,copy,gzip,hashlib,json,os
from pathlib import Path
import types

HERE=Path(__file__).resolve().parent
OUTPUT=Path('/home/holden/mckernel-work/scratch/n290startup1')
IMAGE_SHA='e6a82f87461e3bbf262c1a1eb3bb47398c5b820bb3c974c8f22b3577dfe51da4'
OLD_IMAGE_SHA='10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,why):
 if not ok:raise ValueError(why)
def pinned(ref):
 path=Path(ref['path']);need(path.is_absolute() and path.resolve(strict=True)==path and not path.is_symlink() and path.is_file(),'canonical-regular-input')
 raw=path.read_bytes();need(len(raw)==ref['size'] and sha(raw)==ref['sha256'] and path.stat().st_mode==ref['mode'],'exact-input-reference');return raw
def module(ref,name):
 raw=pinned(ref);m=types.ModuleType(name);m.__file__=ref['path'];exec(compile(raw,ref['path'],'exec'),m.__dict__);return m

def stage(inputs_path,inputs_sha):
 need(os.getuid()==os.geteuid()==1000,'ordinary-user-offline-only')
 raw=Path(inputs_path).read_bytes();need(sha(raw)==inputs_sha,'exact-stage-inputs-sha');d=json.loads(raw)
 need(d['output_directory']==str(OUTPUT) and not os.path.lexists(OUTPUT),'fresh-exact-output-only')
 # Offline packaging may proceed while separate image qualification is pending.
 # This never sets native release/admission or image-acceptance authority.
 if d['current_image_abi_link_qualification'] is not None:pinned(d['current_image_abi_link_qualification'])
 image=pinned(d['new_image']);need(sha(image)==IMAGE_SHA,'exact-current290-image')
 ov=module(d['overlay_module'],'_exact_existing_overlay');p=module(d['record_deriver'],'_exact_existing_record_deriver')
 inherited=json.loads(pinned(d['inherited_native_manifest']));startup=json.loads(pinned(d['retained_startup_manifest']))
 for ref in d['preserved_runtime_refs']:pinned(ref)
 base_ref=inherited['staging']['base_initramfs'];base_raw=gzip.decompress(pinned(base_ref))
 derived,header_proof=p.derive_base_payloads(ov,base_raw,{'images/mckernel.img':(image,OLD_IMAGE_SHA)})
 old=ov._manifest(ov._replay_records(ov.parse_newc(base_raw)[0]));new=ov._manifest(ov._replay_records(ov.parse_newc(derived)[0]))
 need(set(old)==set(new) and [k for k in old if old[k]!=new[k]]==['images/mckernel.img'],'exact-image-only-record-delta')
 need(new['images/mckernel.img']['sha256']==IMAGE_SHA,'new-image-selected')
 need(all(old[k]==new[k] for k in old if k!='images/mckernel.img'),'all-other-final-records-identical')
 OUTPUT.mkdir(mode=0o700);(OUTPUT/'p').mkdir(mode=0o700)
 base_path=OUTPUT/'base.cpio.gz';p.write(base_path,ov._gzip(derived));base=p.ref(base_path)
 collector=d['collector'];payload=d['payload'];launcher=inherited['artifacts']['mcexec']
 overlay_path=OUTPUT/'startup.cpio.gz'
 overlay=ov.build_overlay(str(base_path),payload['path'],collector['path'],launcher['path'],str(overlay_path),collector_sha256=collector['sha256'],mcexec_sha256=launcher['sha256'],payload_sha256=payload['sha256'],base_sha256=base['sha256'],base_size=base['size'],base_cpio_sha256=sha(derived),base_cpio_size=len(derived))
 overlay_manifest=OUTPUT/'startup-overlay.json';p.js(overlay_manifest,overlay)
 manifest=copy.deepcopy(inherited);manifest['case_id']='startup.argv-empty';manifest['payload']=startup['payload'];manifest['artifacts']['payload']=payload;manifest['artifacts']['mckernel_image']=d['new_image'];manifest['artifacts']['initramfs']=base;manifest['artifacts']['root_base']=base
 manifest['staging']=dict(base_initramfs=base,derived_initramfs=p.ref(overlay_path),collector=collector,overlay_source=d['overlay_module'],overlay_manifest=p.ref(overlay_manifest))
 # Keep the current accepted BEGIN/ACK/procfs/retirement consumer and modules;
 # startup has no children, so no child-case oracle is activated.
 need(manifest['profile']==d['retained_profile'],'unchanged-accepted-guest-profile')
 diagnostic=module(d['diagnostic_module'],'_exact_existing_diagnostic');diagnostic._validate_manifest(manifest)
 p.js(OUTPUT/'m.json',manifest)
 result=dict(status='OFFLINE_STAGE_ONLY_NO_NATIVE',changed_base_records=['images/mckernel.img'],raw_header_proof=header_proof,all_other_base_records_identical=True,manifest=p.ref(OUTPUT/'m.json'),new_image=d['new_image'],preserved_modules=inherited['modules'],collector=collector,payload=payload,guest_runs=0,current_image_abi_link_qualification=d['current_image_abi_link_qualification'],physical_admission=None,independent_execution_release=None)
 p.js(OUTPUT/'stage-result.json',result);print(json.dumps(result,sort_keys=True));return 0

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--inputs',required=True);parser.add_argument('--inputs-sha256',required=True);a=parser.parse_args();raise SystemExit(stage(a.inputs,a.inputs_sha256))
