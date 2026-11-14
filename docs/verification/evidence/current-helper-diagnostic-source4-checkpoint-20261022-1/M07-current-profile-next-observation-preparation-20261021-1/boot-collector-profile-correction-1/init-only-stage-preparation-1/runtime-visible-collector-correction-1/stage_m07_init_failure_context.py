"""One existing init-only M07 failure-visibility stage derivative with accepted053d/sentinel33f. No native execution.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Requires dispatcher ordinary source/profile release; preserves accepted metadata route.
"""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,os,resource,shutil,stat,sys
D=Path(__file__).resolve().parent
PAYLOAD_CONTRACT={'argv': ['/bin/mcexec', '-t', '1', '0', 'app', 'threads'], 'cwd': '/case/work', 'env': {'COKERNEL_PATH': '/apps', 'PATH': '/usr/bin:/bin'}, 'oracle': {'exit_code': 0, 'stderr_hex': '', 'stdout_hex': '454e41424c45445f52455155495245445f584352303d303030303030303030303030303030370a454e41424c45445f53595343414c4c5f504153530a454e41424c45445f46555445585f504153530a454e41424c45445f5349474e414c5f504153530a454e41424c45445f50524f46494c455f504153530a'}, 'stderr_limit_bytes': 1024, 'stdout_limit_bytes': 1024}
REPO=Path('/home/holden/mckernel');SCRATCH=Path('/home/holden/mckernel-work/scratch')
def need(x,s):
 if not x:raise ValueError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 p=Path(p);s=p.stat();return dict(path=str(p),sha256=sha(p.read_bytes()),size=s.st_size,mode=s.st_mode)
def exact(r):need(ref(r['path'])==r,'exact input '+r['path'])
def write(p,b):
 with p.open('xb')as f:f.write(b)
def js(p,v):write(p,(json.dumps(v,indent=2)+'\n').encode())
def mod(n,p):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);sys.modules[n]=m;spec.loader.exec_module(m);return m
def private(p):
 s=p.lstat();need(p.resolve()==p and stat.S_ISDIR(s.st_mode)and s.st_uid==1000 and stat.S_IMODE(s.st_mode)==0o700,'private canonical directory '+str(p))
def verify_init_only_delta(old,final):
 need(len(final)==len(old)==60 and set(final)==set(old),'exact full60 final members')
 deltas={n:{k:[old[n][k],final[n][k]] for k in old[n] if old[n][k]!=final[n][k]} for n in final if final[n]!=old[n]}
 need(set(deltas)=={'init'} and all(set(v)<={'sha256','size'} for v in deltas.values()),'exact init-only content delta')
 need(all(final[n]==old[n] for n in ('images/mckernel.img','bin/mcexec','apps/app','bin/native-boot')) and sum(final[n]==old[n] for n in final)==59,'exact59 unchanged; kernel/launcher/app/boot explicitly equal')
 return deltas
def main():
 ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--case',choices=['numa'],required=True);ap.add_argument('--binding',required=True);ap.add_argument('--binding-sha256',required=True);ap.add_argument('--preflight-only',action='store_true');a=ap.parse_args()
 need(os.sched_getaffinity(0)=={7}and resource.getrlimit(resource.RLIMIT_AS)[0]<=1073741824,'CPU7/1GiB')
 need(sha(Path(a.binding).read_bytes())==a.binding_sha256,'binding bytes');b=json.loads(Path(a.binding).read_text());c=b['cases'][a.case]
 review=b['image_artifact_review'];exact(review);r=json.loads(Path(review['path']).read_bytes())
 need(review['sha256']=='afdf6a8d5dcf9aec104e5d68f4bbf57d82034ade5d3ea20cbc1576bf319cfa41','fixed genuine image artifact decision')
 need(r['schema']=='mckernel.current-numa-scheduler.production-image-artifact-review.v1'and r['decision']=='PASS_ACTUAL_CURRENT_NUMA_SCHEDULER_IMAGE_AND_REAL_MCEEXEC_LINK_ARTIFACTS_ONLY'and r['implementation_ownership']is False,'independent actual artifact acceptance')
 need(r['status']=='PASS_CURRENT_IMAGE_BUILD_LINK_AND_NAMED_BOUNDARIES_NO_NATIVE_ACCEPTANCE' and r['reviewer'] and r['source_derivative_sha256']=='cae8b221bdaa12f2212e4e8d0cfd8f39ab6b5dce6ba30c821f4997a2be8b0d87' and r['materialization_sha256']=='3b2cac15a99f4a6a85e5ca213ce915d615d74b6ed854abd3cd2840bf327d857f','actual current source artifact decision')
 need(r['named_insert_clear_default_compile_and_link_joins'] is True and r['observations']['production_default_MCKERNEL_RUST_SYSCALL_POLICY_HELPERS'] is True and r['observations']['unique_provider_each'] is True and r['observations']['no_named_final_strong_or_weak_undefined'] is True and r['artifact_descriptors_verified']['artifacts/mcexec']['sha256']=='689dcad27b2ce3a30f49df1bfe9452f2169a14e9c350c24c9677c88b1f152876' and r['artifact_descriptors_verified']['artifacts/mcexec']['bytes']==394656,'actual named Rust default/link proof and separate production launcher evidence')
 for key,role in [('image_source','artifacts/mckernel.img')]:
  fact=r['artifact_descriptors_verified'][role];v=b[key];need(v['path']==fact['path']and v['sha256']==fact['sha256']and v['size']==fact['bytes'],'accepted exact artifact '+key);exact(v)
 need(type(b.get('launcher_artifact_review')) is dict and type(b.get('launcher_dependency_join')) is dict and type(b.get('mcexec_source')) is dict,'genuine new launcher artifact/dependency references remain pending')
 launcher_review=b['launcher_artifact_review'];exact(launcher_review);lr=json.loads(Path(launcher_review['path']).read_bytes())
 need(lr['schema']=='mckernel.launcher-only-production-artifact-review.v1' and lr['status']=='PASS_ACTUAL_LAUNCHER_ONLY_PRODUCTION_TARGET_ARTIFACT' and lr['implementation_ownership'] is False and lr['reviewer'],'independent actual launcher-only artifact acceptance')
 need(lr['launcher_source_sha256']=='da71f31656ccfc58a79c4dcca01f9c6742135c292b213b7d86113ebddc4cae0a' and lr['target']=='mcexec' and lr['kernel_rebuilt'] is False and lr['source_change']=='PLD_MPOL_MAX4→5 only','exact launcher-only Rust sentinel repair, no kernel rebuild')
 launcher_fact=lr['artifact_descriptors_verified']['artifacts/mcexec'];new_launcher=b['mcexec_source']
 need(set(launcher_fact)=={'path','sha256','bytes'} and new_launcher['path']==launcher_fact['path'] and new_launcher['sha256']==launcher_fact['sha256'] and new_launcher['size']==launcher_fact['bytes'] and c['mcexec']==new_launcher,'exact new launcher descriptor and overlay consumer');exact(new_launcher)
 exact(b['launcher_dependency_join']);dep=json.loads(Path(b['launcher_dependency_join']['path']).read_bytes())
 need(dep['schema']=='mckernel.launcher-only-dependency-join-review.v1' and dep['status']=='PASS_ACTUAL_LAUNCHER_ONLY_DEPENDENCY_JOIN' and dep['implementation_ownership'] is False and dep['reviewer'],'independent actual new launcher dependency join')
 need(dep['launcher']==launcher_fact and dep['baseline_dependency_acceptance']==b['dynamic_closure_observation'] and dep['actual_elf_needed_provider_join'] is True,'actual new ELF/needed/provider join to unchanged dependency ancestry')
 exact(b['consumer_contract']);exact(b['accepted_actual_app_review']);exact(b['accepted_threads_stage']);exact(b['dynamic_closure_observation'])
 stage=json.loads(Path(b['accepted_threads_stage']['path']).read_bytes());need(b['accepted_threads_stage']['sha256']=='4b01ae242456e9d338e724951d9fba51ed6d819c3779d823e3abdced7539847a','accepted actual current M07 two-member baseline stage');need(stage['status']=='PASS_ACTUAL_OFFLINE_STAGE_AND_STRICT_MANIFEST_ONLY' and stage['implementation_ownership'] is False and stage['reviewer'],'genuine current stage descriptor projection')
 need(c['old_manifest']==stage['manifest'] and c['old_base']==stage['base'] and c['old_overlay']==stage['overlay'] and c['old_overlay_manifest']==stage['overlay_manifest'],'exact actual current threads baseline')
 need(stage['mcexec']['sha256']==new_launcher['sha256']=='33f88082a995857c17ca07dab698e51d78064632462b4069b3c2396e0d29a131' and stage['mcexec']['size']==new_launcher['size']==394656,'separately accepted sentinel launcher equals current baseline')
 need(b['dynamic_closure_observation']['sha256']=='338f6eafeefce26cf4fb826c58d17762c7c204806e146b09ec480facd4452314','reuse genuine unchanged dependency ancestry; new launcher join independently bound above')
 need(b['accepted_actual_app_review']['sha256']=='6405dc4064bd9d60889e3f7d5db891567f004d663e4feadfd0f68e0ce06add13','genuine accepted M07 source/oracle/native reference')
 app_review=json.loads(Path(b['accepted_actual_app_review']['path']).read_bytes())
 need(app_review['status']=='PASS_SCOPED_NEW_IMAGE_AVX_AND_POSITIVE_RETIREMENT' and app_review['application_acceptance'] is True and app_review['implementation_ownership'] is False and app_review['independent_reviewer'],'genuine scoped historical M07 acceptance, not current image acceptance')
 need(c['payload']['sha256']=='5b116839f8cfbb796793d88f7792d21e5e29bd0510d527e8782284ae18239177' and c['payload']['size']==1522832,'fixed retained M07 payload; no compilation')
 need(b['payload_contract']==PAYLOAD_CONTRACT,'exact typed M07 suffix exit0; actual CPUID/XCR0 headers must be parsed by accepted case adapter')
 exact(b['two_cpu_native_boot']);exact(b['header_producer']);exact(b['accepted_two_cpu_batch'])
 need(b['two_cpu_native_boot']['sha256']=='4312f9a8f53d8db7b2b6be4c7d5e409f5c0f82cf8215728209be0f6ff4a5d5c5' and b['two_cpu_native_boot']['size']==35784,'existing accepted two-McKernel-CPU native bootstrap')
 batch=json.loads(Path(b['accepted_two_cpu_batch']['path']).read_bytes())
 need(batch['status']=='PASS_ACTUAL_CURRENT_053D_SIX_STRICT_APPLICATION_LAUNCHES_ONLY' and batch['application_acceptance'] is True and batch['implementation_ownership'] is False and batch['observed_scope']['mckernel_cpus']==[0,1],'genuine current twoCPU batch authority')
 for k in ['old_manifest','old_base','old_overlay','old_overlay_manifest','payload','collector','mcexec']:exact(c[k])
 exact(b['overlay_source']);exact(b['diagnostic_source']);assets=Path(b['assets_root']);manifests=Path(b['manifests_root']);out=Path(c['output_dir']);mp=Path(c['manifest_dir'])
 need(REPO in assets.parents and SCRATCH in manifests.parents,'unchanged visible mount roots');need(not os.path.lexists(out)and not os.path.lexists(mp),'fresh case output')
 for row in b['cases'].values():need(len(os.fsencode(row['endpoint']))==row['endpoint_encoded_bytes']<=107,'full endpoint preflight')
 need(shutil.disk_usage(REPO).free>=16*1024**3+640*1024**2+64*1024**2,'host floor plus640MiB reserve plus64MiBstage')
 need(shutil.disk_usage(SCRATCH).free>=12*1024**3+640*1024**2+64*1024**2,'scratch floor plus640MiB reserve plus64MiBstage')
 if a.preflight_only:
  print(json.dumps(dict(status='PASS_EXACT_REVIEWED_IMAGE_STAGE_PREFLIGHT',case=a.case,archives=0,runtime_release=False)));return
 need(not assets.exists()and not manifests.exists(),'fresh roots');assets.mkdir(mode=0o700);manifests.mkdir(mode=0o700)
 private(assets);private(manifests);out.mkdir(mode=0o700);mp.mkdir(mode=0o700)
 collector_visible=assets/'collector.init';write(collector_visible,Path(c['collector']['path']).read_bytes());collector_visible.chmod(0o755);collector_ref=ref(collector_visible);need(collector_ref['sha256']==c['collector']['sha256'] and collector_ref['size']==c['collector']['size'],'exact runtime-visible collector copy')
 visible=Path(stage['image']['path']);launcher=Path(c['mcexec']['path']);launcher_ref=c['mcexec'];payload_visible=Path(c['payload']['path']);payload_ref=c['payload'];boot_ref=stage['native_boot']
 image=stage['image'];m=json.loads(Path(c['old_manifest']['path']).read_text());ov=mod('scheduler_stage_overlay',b['overlay_source']['path']);nd=mod('scheduler_stage_nd',b['diagnostic_source']['path']);base_bytes=Path(c['old_base']['path']).read_bytes();raw=gzip.decompress(base_bytes)
 need(image['sha256']=='053d59b533665eef9d56fe1b348e699d97159e954fbc1fbff973bbe46113f485' and image['size']==8435496,'accepted kernel bytes reused unchanged')
 patched=raw;proof=[]
 base=out/'base.cpio.gz';write(base,base_bytes);need(base.read_bytes()==base_bytes,'accepted compressed base copied byte-exact, no header mutation');overlay=out/'lifecycle.cpio.gz'
 om=ov.build_overlay(str(base),str(payload_visible),str(collector_visible),str(launcher),str(overlay),collector_sha256=c['collector']['sha256'],mcexec_sha256=c['mcexec']['sha256'],payload_sha256=c['payload']['sha256'],base_sha256=ref(base)['sha256'],base_size=base.stat().st_size,base_cpio_sha256=sha(patched),base_cpio_size=len(patched));js(out/'overlay-manifest.json',om)
 old=json.loads(Path(c['old_overlay_manifest']['path']).read_text())['final_map'];full=ov._replay_records(ov.parse_newc(gzip.decompress(overlay.read_bytes()))[0]);final=ov._manifest(full);need(final==om['final_map']and len(final)==len(old)==60 and set(final)==set(old),'full60 concatenated replay')
 deltas=verify_init_only_delta(old,final)
 oldfull=ov._replay_records(ov.parse_newc(gzip.decompress(Path(c['old_overlay']['path']).read_bytes()))[0])
 for n in full:
  for k in full[n]:
   if k not in {'data','size','sha256'}:need(full[n][k]==oldfull[n][k],'all final metadata '+n+' '+k)
 m['case_id']='vector.enabled-avx-preservation';m['payload']=b['payload_contract'];m['artifacts']['payload']=payload_ref;m['artifacts']['mckernel_image']=image;m['artifacts']['mcexec']=launcher_ref;m['artifacts']['native_boot']=boot_ref
 for k in ['initramfs','root_base']:m['artifacts'][k]=ref(base)
 m['staging'].update(collector=collector_ref,base_initramfs=ref(base),derived_initramfs=ref(overlay),overlay_manifest=ref(out/'overlay-manifest.json'));js(mp/'manifest.json',m);nd.load_manifest(str(mp/'manifest.json'))
 used=sum(p.stat().st_size for p in assets.rglob('*')if p.is_file());need(used<=64*1024**2,'64MiB aggregate stage output')
 js(out/'stage-result.json',dict(status='PASS_M07_INIT_ONLY_STAGE_PENDING_ACTUAL_CONSUMER_BINDING_AND_REVIEW',manifest=ref(mp/'manifest.json'),collector=collector_ref,image=image,mcexec=launcher_ref,payload=payload_ref,artifact_review=review,launcher_artifact_review=launcher_review,launcher_dependency_join=b['launcher_dependency_join'],base=ref(base),overlay=ref(overlay),deltas=deltas,raw_header_proof=proof,final_map=final,accepted_base_byte_exact=True,all_other_final_metadata_equal=True,aggregate_stage_bytes=used,runtime_release=False))
 print(json.dumps(dict(status='PASS_SINGLE_M07_INIT_ONLY_STAGE',case=a.case,image_sha256=image['sha256'],image_bytes=image['size'],aggregate_stage_bytes=used,guests=0,runtime_release=False)))
if __name__=='__main__':main()
