"""Literal changed stager comparison/ancestry and existing strict loader only; no stage/archive."""
import copy,hashlib,importlib.util,json,pathlib,sys
sys.dont_write_bytecode=True
D=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('m05_init_stage_body',D/'stage_m05_init_failure_context.py');stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
b=json.loads((D/'BINDING.M05-INIT-ONLY.PROPOSED.json').read_bytes());c=b['cases']['m05'];out=D/'actual-consumer-body-check-1';out.mkdir(mode=0o700)
def js(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def refused(fn):
 try:fn()
 except (ValueError,AssertionError)as exc:return str(exc)
 raise AssertionError('boundary unexpectedly accepted')
assert stage.ref(D/'stage_m05_init_failure_context.py')==b['stage_source']
accepted=stage.accepted_m05_baseline(b,c)
old=json.loads(pathlib.Path(c['old_overlay_manifest']['path']).read_bytes())
final=copy.deepcopy(old['final_map']);final['init']['sha256']=c['collector']['sha256'];final['init']['size']=c['collector']['size']
negative_original=refused(lambda:stage.verify_init_only_delta(old['final_map'],old['final_map']))
delta=stage.verify_init_only_delta(old['final_map'],final);assert set(delta)=={'init'}
negative={}
bad=copy.deepcopy(final);bad['init']['mode']=0o100700;negative['init_mode']=refused(lambda:stage.verify_init_only_delta(old['final_map'],bad))
bad=copy.deepcopy(final);bad['apps/app']['sha256']='0'*64;negative['payload_change']=refused(lambda:stage.verify_init_only_delta(old['final_map'],bad))
bad=copy.deepcopy(final);bad.pop('bin/native-resource-release-probe');negative['missing_probe']=refused(lambda:stage.verify_init_only_delta(old['final_map'],bad))
nd=stage.mod('m05_stage_strict_nd',b['diagnostic_source']['path']);original=json.loads(pathlib.Path(c['old_manifest']['path']).read_bytes());nd.load_manifest(c['old_manifest']['path'])
manifest=copy.deepcopy(original);manifest['staging']['collector']=c['collector'];manifest['staging']['overlay_source']=b['overlay_source'];js(out/'ORIGINAL-NEGATIVE-MANIFEST.json',manifest)
try:nd.load_manifest(str(out/'ORIGINAL-NEGATIVE-MANIFEST.json'))
except nd.DiagnosticError as exc:loader_negative=str(exc)
else:raise AssertionError('old overlaymetadata/new collector mismatch accepted')
metadata=copy.deepcopy(old);metadata['collector_sha256']=c['collector']['sha256'];metadata['sources']['collector']={'path':c['collector']['path'],'sha256':c['collector']['sha256'],'identity':nd._identity(c['collector']['path'])};metadata['final_map']=final
js(out/'OVERLAY-METADATA-LOADER-FIXTURE.json',metadata);manifest['staging']['overlay_manifest']=stage.ref(out/'OVERLAY-METADATA-LOADER-FIXTURE.json');js(out/'CHANGED-POSITIVE-MANIFEST.json',manifest);nd.load_manifest(str(out/'CHANGED-POSITIVE-MANIFEST.json'))
# Metadata fixture only: archives are original and unmodified, no claim newinit in oldarchive.
planned=copy.deepcopy(original);visible=dict(c['collector']);visible.update(path=b['assets_root']+'/collector.init',mode=0o100755);planned['staging']['collector']=visible;planned['staging']['overlay_source']=b['overlay_source']
for key in ['initramfs','root_base']:planned['artifacts'][key]['path']=c['output_dir']+'/base.cpio.gz'
for key,filename in [('base_initramfs','base.cpio.gz'),('derived_initramfs','lifecycle.cpio.gz'),('overlay_manifest','overlay-manifest.json')]:planned['staging'][key]['path']=c['output_dir']+'/'+filename
pmeta=copy.deepcopy(old)
for name,path in [('base',c['output_dir']+'/base.cpio.gz'),('collector',visible['path'])]:pmeta['sources'][name]['path']=path
paths=stage.verify_consumed_paths(c['manifest_dir']+'/manifest.json',planned,pmeta,b)
exterior=copy.deepcopy(planned);exterior['staging']['collector']=c['collector'];exteriormeta=copy.deepcopy(pmeta);exteriormeta['sources']['collector']['path']=c['collector']['path'];path_negative=refused(lambda:stage.verify_consumed_paths(c['manifest_dir']+'/manifest.json',exterior,exteriormeta,b))
assert pathlib.Path(c['collector']['path']).stat().st_mode==0o100700
result=dict(scope=b['scope'],status='PASS_ACTUAL_M05_INIT_ONLY_61_60_ANCESTRY_AND_STRICT_LOADER_COMPONENT_BODIES_ONLY',source=b['stage_source'],binding=stage.ref(D/'BINDING.M05-INIT-ONLY.PROPOSED.json'),baseline_ancestry_positive=True,original_no_delta_rejected=negative_original,changed_init_only_delta=delta,negative_boundaries=negative,original_collector_mismatch_loader_rejected=loader_negative,changed_coupled_metadata_strict_loader_positive=True,original_static0700_preserved=True,planned_collector_mode=0o100755,all_consumed_paths=paths,consumed_count=len(paths),read_only_roots=b['read_only_roots'],exterior_original_collector_path_rejected=path_negative,source_descriptor=b['overlay_source'],original_archive_descriptors_preserved=[c[k]for k in ['old_base','old_overlay','old_overlay_manifest']],stage_executed=False,archives_generated=0,external_aliases_written=0,native_release=False,limitations='Loader fixture couples metadata only while original archive bytes remain unchanged; it is no stage or new archive content proof. Planned path guard validates32 paths within existing3 roots; output paths are absent until separately granted stage.')
js(out/'ACTUAL-M05-INIT-ONLY-CONSUMER-BODY-RESULT-1.json',result);print(json.dumps({'status':result['status'],'paths':len(paths),'stage_executed':False}))
