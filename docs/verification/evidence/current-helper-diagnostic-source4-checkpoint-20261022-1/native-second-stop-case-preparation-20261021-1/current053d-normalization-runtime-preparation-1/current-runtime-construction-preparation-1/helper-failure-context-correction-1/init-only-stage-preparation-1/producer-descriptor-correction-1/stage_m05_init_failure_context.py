"""One existing init-only M05 failure-visibility stage derivative with accepted053d/sentinel33f. No native execution.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Requires dispatcher ordinary source/profile release; preserves accepted metadata route.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,importlib.util,json,os,resource,shutil,stat,sys
D=Path(__file__).resolve().parent
PAYLOAD_CONTRACT={'argv': ['/bin/mcexec', '-t', '1', '0', 'app', 'A', '', 'B'], 'cwd': '/case/work', 'env': {'COKERNEL_PATH': '/apps', 'PATH': '/usr/bin:/bin'}, 'oracle': {'exit_code': 0, 'stderr_hex': '', 'stdout_hex': '68616e646c65643d31206f627365727665645f626c6f636b65643d3120726573746f7265643d310a'}, 'stderr_limit_bytes': 1024, 'stdout_limit_bytes': 1024}
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
 need(len(final)==len(old)==61 and set(final)==set(old),'exact full61 final members')
 deltas={n:{k:[old[n][k],final[n][k]] for k in old[n] if old[n][k]!=final[n][k]} for n in final if final[n]!=old[n]}
 need(set(deltas)=={'init'} and all(set(v)<={'sha256','size'} for v in deltas.values()),'exact init-only content delta')
 need(all(final[n]==old[n] for n in ('images/mckernel.img','bin/mcexec','apps/app','bin/native-boot')) and sum(final[n]==old[n] for n in final)==60,'exact60 unchanged; kernel/launcher/app/boot explicitly equal')
 return deltas
def accepted_m05_baseline(b,c):
 keys=['accepted_original_stage','original_stage_result','original_stage_manifest','boot_alias_result','boot_alias_review','boot_alias_manifest','source_alias_result','source_alias_review','source_alias_manifest','normalization_review','normalization_settings','helper_source_review','helper_source','helper_actual_result']
 for k in keys:exact(b[k])
 stage=json.loads(Path(b['accepted_original_stage']['path']).read_bytes())
 need(b['accepted_original_stage']['sha256']=='12582123b7eccaeb970fa90b427bd5b438a0957033e2743eca5e846c8503091f' and stage['schema']=='mckernel.m05-native-stage.actual-consumer-projection.v1' and stage['status']=='PASS_ACTUAL_CURRENT053D_EXACT67_OFFLINE_STAGE_ONLY' and stage['decision']=='ACCEPT_ACTUAL_FINITE_STAGE_FOR_DOWNSTREAM_NORMALIZATION_PREPARATION','genuine original M05 stage')
 need(stage['implementation_ownership'] is False and stage['reviewer'] and stage['strict_loader_passed'] is True and stage['base_prefix_verified'] is True and stage['all_metadata_equal'] is True and stage['archive_members']==61 and stage['unchanged_members']==57 and stage['changed_final_members']==['bin/mcexec','bin/native-boot','images/mckernel.img','init'],'unchanged original stage scope')
 need(stage['actual_stage_result']==dict(path=b['original_stage_result']['path'],sha256=b['original_stage_result']['sha256'],bytes=b['original_stage_result']['size']) and stage['manifest']==b['original_stage_manifest'],'original65ac/28d producer and manifest joins')
 for k,sk in [('old_base','base'),('old_overlay','overlay'),('old_overlay_manifest','overlay_manifest')]:need(c[k]==stage[sk],'genuine baseline archive '+k)
 boot=json.loads(Path(b['boot_alias_result']['path']).read_bytes());br=json.loads(Path(b['boot_alias_review']['path']).read_bytes())
 need(br['schema']=='mckernel.m05-visible-boot-alias.actual-metadata-review.v1' and br['status']=='PASS_ACTUAL_VISIBLE_BOOT_ALIAS_AND_MANIFEST_SUCCESSOR_ONLY' and br['actual_alias_result']==b['boot_alias_result'] and br['implementation_ownership'] is False and br['reviewer'],'genuine separate boot alias review')
 need(boot['status']=='PASS_IDENTICAL_BOOT_ALIAS_AND_ONE_MANIFEST_DESCRIPTOR_SUCCESSOR_ONLY' and boot['original_manifest']==b['original_stage_manifest'] and boot['manifest']==b['boot_alias_manifest'] and boot['only_manifest_delta']=='/artifacts/native_boot/path' and boot['archive_rewrites']==0 and boot['strict_loader_passed'] is True,'original boot alias scope')
 original=json.loads(Path(b['original_stage_manifest']['path']).read_bytes());bootdoc=json.loads(Path(b['boot_alias_manifest']['path']).read_bytes());expected=copy.deepcopy(original);expected['artifacts']['native_boot']=boot['native_boot'];need(bootdoc==expected and br['manifest']==b['boot_alias_manifest'] and br['native_boot']==boot['native_boot']==b['two_cpu_native_boot'],'exact28d to a8 boot-only successor')
 source=json.loads(Path(b['source_alias_result']['path']).read_bytes());sr=json.loads(Path(b['source_alias_review']['path']).read_bytes())
 need(sr['status']=='PASS_ACTUAL_VISIBLE_STAGE_SOURCE_ALIAS_AND_MANIFEST_SUCCESSOR_ONLY' and sr['actual_producer']==b['source_alias_result'] and sr['implementation_ownership'] is False and sr['reviewer'],'genuine separate source alias review')
 need(source['status']=='PASS_IDENTICAL_STAGE_SOURCE_ALIAS_AND_ONE_MANIFEST_DESCRIPTOR_SUCCESSOR_ONLY' and source['original_manifest']==b['boot_alias_manifest'] and source['manifest']==b['source_alias_manifest'] and source['only_manifest_delta']=='/staging/overlay_source/path' and source['archive_rewrites']==0 and source['strict_loader_passed'] is True,'a8 to bce source-only alias scope')
 expected=copy.deepcopy(bootdoc);expected['staging']['overlay_source']=source['source_alias'];need(json.loads(Path(b['source_alias_manifest']['path']).read_bytes())==expected and sr['manifest']==b['source_alias_manifest'],'complete separate alias chain')
 for alias,oldkey,newkey in [(boot,'original_native_boot','native_boot'),(source,'original_stage_source','source_alias')]:need({k:v for k,v in alias[oldkey].items()if k!='path'}=={k:v for k,v in alias[newkey].items()if k!='path'},'byte/mode identical alias')
 norm=json.loads(Path(b['normalization_review']['path']).read_bytes());need(b['normalization_review']['sha256']=='866c982775bb7ef3327cd0cb6456763b848d93a8aaf02af964e2de01691c0f4e' and norm['status']=='PASS_ACTUAL_M05_PAIRED_NORMALIZATION_ONLY' and norm['normalization_accepted'] is True and norm['implementation_ownership'] is False and norm['reviewer'] and norm['runtime_permission'] is False and norm['native_acceptance'] is False,'actual normalization only')
 need(norm['normalized_manifest']==c['old_manifest'] and Path(c['old_manifest']['path']).read_bytes()==Path(b['source_alias_manifest']['path']).read_bytes(),'actual normalized bce bytes')
 need(norm['settings_sha256']==b['normalization_settings']['sha256'] and norm['verified']['source_FD_rows']==16 and norm['verified']['unique_consumed_paths']==32 and norm['verified']['read_only_roots']==3 and norm['verified']['all_consumed_paths_covered'] is True and norm['verified']['actual_corrected_runner_loader_positive'] is True,'actual16FD/32path/3root loader source closure')
 cfg=json.loads(Path(b['normalization_settings']['path']).read_bytes());need(b['runtime_source_pins']==cfg['runtime_source_pins'] and len(b['runtime_source_pins'])==16,'actual normalized runtime source pins')
 for row in b['runtime_source_pins']:exact(row)
 current=json.loads(Path(c['old_manifest']['path']).read_bytes())
 for k,sk in [('mckernel_image','image'),('mcexec','mcexec'),('payload','payload')]:need(current['artifacts'][k]==stage[sk],'unchanged actual artifact '+k)
 need(current['payload']==stage['payload_contract']==PAYLOAD_CONTRACT and current['modules']==stage['module_tuple'] and current['artifacts']['native_boot']==b['two_cpu_native_boot'] and current['staging']['collector']==stage['collector'],'actual M05 tuple and old collector')
 review=json.loads(Path(b['helper_source_review']['path']).read_bytes());need(b['helper_source_review']['sha256']=='aad814d5f9747c03aa20b70b8e5b66d2c590bb98aafaa2231417468a9e6921d4' and review['decision']=='ACCEPT_M05_SHARED_HELPER_FAILURE_CONTEXT_SOURCE_AND_ACTUAL_COMPONENT_EVIDENCE_ONLY' and review['reviewer']=='/root/numa_clear_range_review' and review['blockers_within_reviewed_scope']==[],'actual M05 shared helper source review')
 need(review['source']['sha256']==b['helper_source']['sha256']=='e4a2a4f5278c6fd1588571431f0fe7ec3840af531e3ea18fa2fb750308d9f38b' and review['actual_evidence']['sha256']==b['helper_actual_result']['sha256']=='619bb89b4c5faa162966bd68698b3aef3f77f6f6e1c688bf759766ba3265620a','actual changed source and helper evidence')
 need(review['actual_evidence']['static_binary']['sha256']==c['collector']['sha256']=='f6ef8e3cc1ec50a871339f0550f1f1ba53f5bcf3b44e950059825a73d7cc4850' and review['actual_evidence']['static_binary']['bytes']==c['collector']['size']==1034408 and c['collector']['mode']==0o100700,'actual accepted full-static collector; original0700 preserved')
 return stage

def verify_consumed_paths(manifest_path,manifest,overlay,b):
 roots=[Path('/home/holden/mckernel'),Path('/home/holden/mckernel-work/scratch'),Path('/home/holden/mckernel-work/host-preparation/native-second-stop-case-preparation-20261021-1/current053d-normalization-runtime-preparation-1/runtime-source-1')]
 need(b['read_only_roots']==[str(x)for x in roots],'fixed three read-only roots')
 paths=[str(manifest_path),*[r['path']for r in b['runtime_source_pins']]]
 for table in (manifest['artifacts'].values(),manifest['modules'],manifest['staging'].values(),overlay['sources'].values()):
  paths.extend(r['path']for r in table if isinstance(r,dict)and 'path'in r)
 paths=sorted(set(paths));need(len(paths)==32,'exact32 runtime consumed paths')
 for p in paths:need(any(Path(p)==r or r in Path(p).parents for r in roots),'runtime-visible consumed path '+p)
 return paths

def main():
 ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--case',choices=['m05'],required=True);ap.add_argument('--binding',required=True);ap.add_argument('--binding-sha256',required=True);ap.add_argument('--preflight-only',action='store_true');a=ap.parse_args()
 need(os.sched_getaffinity(0)=={6}and resource.getrlimit(resource.RLIMIT_AS)[0]<=1073741824,'CPU6/1GiB')
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
 need(set(launcher_fact)=={'path','sha256','bytes'} and new_launcher['path']==launcher_fact['path'] and new_launcher['sha256']==launcher_fact['sha256'] and new_launcher['size']==launcher_fact['bytes'] and all(c['mcexec'][k]==new_launcher[k] for k in ('sha256','size','mode')),'exact new launcher descriptor and overlay consumer');exact(new_launcher)
 exact(b['launcher_dependency_join']);dep=json.loads(Path(b['launcher_dependency_join']['path']).read_bytes())
 need(dep['schema']=='mckernel.launcher-only-dependency-join-review.v1' and dep['status']=='PASS_ACTUAL_LAUNCHER_ONLY_DEPENDENCY_JOIN' and dep['implementation_ownership'] is False and dep['reviewer'],'independent actual new launcher dependency join')
 need(dep['launcher']==launcher_fact and dep['baseline_dependency_acceptance']==b['dynamic_closure_observation'] and dep['actual_elf_needed_provider_join'] is True,'actual new ELF/needed/provider join to unchanged dependency ancestry')
 stage=accepted_m05_baseline(b,c)
 need(stage['mcexec']['sha256']==new_launcher['sha256']=='33f88082a995857c17ca07dab698e51d78064632462b4069b3c2396e0d29a131' and stage['mcexec']['size']==new_launcher['size']==394656,'separately accepted sentinel launcher equals M05 baseline')
 need(b['dynamic_closure_observation']['sha256']=='338f6eafeefce26cf4fb826c58d17762c7c204806e146b09ec480facd4452314','unchanged real v2/lifecycle/payload dynamic dependency ancestry')
 exact(b['dynamic_closure_observation'])
 need(c['payload']['sha256']=='8be0b167d7267d4ef5aa122f62ebdbd95d6aa0be4f75384b9285d9983683c234' and c['payload']['size']==872056,'fixed signal-mask payload; no compilation')
 need(b['payload_contract']==PAYLOAD_CONTRACT,'exact M05 signal-mask output40/empty stderr/exit0')
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
 visible=Path(stage['image']['path']);launcher=Path(c['mcexec']['path']);launcher_ref=c['mcexec'];payload_visible=Path(c['payload']['path']);payload_ref=c['payload'];boot_ref=b['two_cpu_native_boot']
 image=stage['image'];m=json.loads(Path(c['old_manifest']['path']).read_text());ov=mod('scheduler_stage_overlay',b['overlay_source']['path']);nd=mod('scheduler_stage_nd',b['diagnostic_source']['path']);base_bytes=Path(c['old_base']['path']).read_bytes();raw=gzip.decompress(base_bytes)
 need(image['sha256']=='053d59b533665eef9d56fe1b348e699d97159e954fbc1fbff973bbe46113f485' and image['size']==8435496,'accepted kernel bytes reused unchanged')
 patched=raw;proof=[]
 base=out/'base.cpio.gz';write(base,base_bytes);need(base.read_bytes()==base_bytes,'accepted compressed base copied byte-exact, no header mutation');overlay=out/'lifecycle.cpio.gz'
 om=ov.build_overlay(str(base),str(payload_visible),str(collector_visible),str(launcher),str(overlay),collector_sha256=c['collector']['sha256'],mcexec_sha256=c['mcexec']['sha256'],payload_sha256=c['payload']['sha256'],base_sha256=ref(base)['sha256'],base_size=base.stat().st_size,base_cpio_sha256=sha(patched),base_cpio_size=len(patched));js(out/'overlay-manifest.json',om)
 old=json.loads(Path(c['old_overlay_manifest']['path']).read_text())['final_map'];full=ov._replay_records(ov.parse_newc(gzip.decompress(overlay.read_bytes()))[0]);final=ov._manifest(full);need(final==om['final_map']and len(final)==len(old)==61 and set(final)==set(old),'full61 concatenated replay')
 deltas=verify_init_only_delta(old,final)
 oldfull=ov._replay_records(ov.parse_newc(gzip.decompress(Path(c['old_overlay']['path']).read_bytes()))[0])
 for n in full:
  for k in full[n]:
   if k not in {'data','size','sha256'}:need(full[n][k]==oldfull[n][k],'all final metadata '+n+' '+k)
 m['case_id']='native.second-stop.current053d.twoCPU.exact67.helper-context';m['payload']=b['payload_contract'];m['artifacts']['payload']=payload_ref;m['artifacts']['mckernel_image']=image;m['artifacts']['mcexec']=launcher_ref;m['artifacts']['native_boot']=boot_ref
 for k in ['initramfs','root_base']:m['artifacts'][k]=ref(base)
 m['staging'].update(collector=collector_ref,base_initramfs=ref(base),derived_initramfs=ref(overlay),overlay_manifest=ref(out/'overlay-manifest.json'),overlay_source=b['overlay_source']);js(mp/'manifest.json',m);nd.load_manifest(str(mp/'manifest.json'));consumed=verify_consumed_paths(mp/'manifest.json',m,om,b)
 used=sum(p.stat().st_size for p in assets.rglob('*')if p.is_file());need(used<=64*1024**2,'64MiB aggregate stage output')
 js(out/'stage-result.json',dict(status='PASS_M05_INIT_ONLY_STAGE_PENDING_ACTUAL_CONSUMER_BINDING_AND_REVIEW',manifest=ref(mp/'manifest.json'),collector=collector_ref,image=image,mcexec=launcher_ref,payload=payload_ref,artifact_review=review,launcher_artifact_review=launcher_review,launcher_dependency_join=b['launcher_dependency_join'],base=ref(base),overlay=ref(overlay),deltas=deltas,raw_header_proof=proof,final_map=final,accepted_base_byte_exact=True,all_other_final_metadata_equal=True,aggregate_stage_bytes=used,consumed_paths=consumed,read_only_roots=b['read_only_roots'],unchanged_members=60,changed_final_members=['init'],normalization_release=False,runtime_release=False))
 print(json.dumps(dict(status='PASS_SINGLE_M05_INIT_ONLY_STAGE',case=a.case,image_sha256=image['sha256'],image_bytes=image['size'],aggregate_stage_bytes=used,guests=0,runtime_release=False)))
if __name__=='__main__':main()
