"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only validation of already-produced manifest/archive bytes. Private source
authority successor only; never stages, compresses, builds or executes a guest.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,sys
D=Path(__file__).resolve().parent
MANIFEST=Path('/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1/current110-variant-1/capacity-binding-1/producer-implementation-1/real-consumer-1/actual-session-staging-1/bounded-correction-1/actual-stage-1/manifest.json')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def rejected(action,label):
 try:action()
 except (ValueError,KeyError,TypeError):return label
 raise AssertionError('accepted invalid mutation '+label)
raw=MANIFEST.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='6c3c80bff36af0f96ce05f73294c37f035a3e12d7fdc3aeeef88fc7532c11471'
manifest=json.loads(raw)
module=load('SDK5_module_authority',D/'source/composite_module_binding.py')
image=load('current68_image_authority',D/'source/repaired_image_authority.py')
binding=json.loads(Path(manifest['pair']['source_authority']['path']).read_text())
if sys.argv[1]=='authorities':
 module.validate_module_binding(manifest)
 image.validate(binding,manifest['artifacts']['mckernel_image'])
 negatives=[]
 for i in range(3):
  for field,value in [('sha256','0'*64),('size',manifest['modules'][i]['size']+1)]:
   mutant=copy.deepcopy(manifest);mutant['modules'][i][field]=value
   negatives.append(rejected(lambda:module.validate_module_binding(mutant),'module'+str(i)+'-'+field))
 for order in ([1,0,2],[0,0,2]):
  mutant=copy.deepcopy(manifest);mutant['modules']=[mutant['modules'][i] for i in order]
  negatives.append(rejected(lambda:module.validate_module_binding(mutant),'module-order-'+str(order)))
 mutant=copy.deepcopy(manifest);mutant['artifacts']['mcexec']['sha256']='0'*64
 negatives.append(rejected(lambda:module.validate_module_binding(mutant),'launcher-identity'))
 mutant=copy.deepcopy(manifest['artifacts']['mckernel_image']);mutant['sha256']='0'*64
 negatives.append(rejected(lambda:image.validate(binding,mutant),'image-identity'))
 mutant=copy.deepcopy(binding);mutant['canonical205_facts_review']['sha256']='0'*64
 negatives.append(rejected(lambda:image.validate(mutant,manifest['artifacts']['mckernel_image']),'inherited-source-authority'))
 legacy=load('legacy_composite_authority',D/'legacy-source/composite_module_binding.py')
 negatives.append(rejected(lambda:legacy.validate_module_binding(manifest),'legacy-composite64-refuses-current68'))
 print(json.dumps({'status':'PASS_PRIVATE_SDK5_CURRENT68_REAL_AUTHORITY_POSITIVES_AND_MUTATIONS','negative_controls':negatives,'native_acceptance':False}))
else:
 native=load('private_current110_native_diagnostic',D/'source/native_diagnostic.py')
 accepted=native.load_manifest(str(MANIFEST))
 assert raw==MANIFEST.read_bytes(),'existing manifest mutated'
 print(json.dumps({'status':'PASS_ACTUAL_CURRENT110_LOAD_MANIFEST_WITH_PRIVATE_GENUINE_SDK5_CURRENT68_AUTHORITY_SUCCESSORS','manifest_sha256':hashlib.sha256(raw).hexdigest(),'case_id':accepted['case_id'],'native_acceptance':False,'archive_rebuilt':False}))
