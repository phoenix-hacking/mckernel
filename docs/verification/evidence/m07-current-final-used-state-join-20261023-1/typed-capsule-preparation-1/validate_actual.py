"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import importlib.util,json,hashlib,os
D=Path(__file__).resolve().parent;A=D/'actual-stage-1';recipe=json.loads((D/'CAPSULE-RECIPE.json').read_bytes());source=next(x for x in recipe['source_cohort'] if x['path'].endswith('/native_diagnostic.py'))
assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()==source['sha256']
spec=importlib.util.spec_from_file_location('typed',source['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
m=module.load_manifest(A/'manifest.json');overlay=json.loads((A/'overlay-manifest.json').read_bytes())
baseline=next(x for x in recipe['source_cohort'] if x['path'].endswith('/manifest.json'));old=json.loads(Path(baseline['path']).read_bytes());oldmap=json.loads(Path(old['staging']['overlay_manifest']['path']).read_bytes())['final_map'];newmap=overlay['final_map'];assert set(oldmap)==set(newmap) and len(newmap)==62
changed=[p for p in sorted(newmap) if newmap[p]!=oldmap[p]];assert changed==['apps/app','init'],changed
for name in ('mckernel_image','mcexec','bzImage','root_base','initramfs','loader','libc','native_boot'):assert m['artifacts'][name]==old['artifacts'][name],name
assert m['modules']==old['modules'] and m['cleanup_profile']==old['cleanup_profile']
result={'status':'PASS_ACTUAL_TYPED_FULL_LOAD_MANIFEST','manifest_sha256':hashlib.sha256((A/'manifest.json').read_bytes()).hexdigest(),'capsule_sha256':overlay['output_sha256'],'capsule_size':overlay['size'],'member_count':len(newmap),'changed_full_map_rows':changed,'unchanged_sdk5_image_launcher':True,'consumer_sha256':source['sha256'],'native_result':None}
fd=os.open(A/'VALIDATION.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
