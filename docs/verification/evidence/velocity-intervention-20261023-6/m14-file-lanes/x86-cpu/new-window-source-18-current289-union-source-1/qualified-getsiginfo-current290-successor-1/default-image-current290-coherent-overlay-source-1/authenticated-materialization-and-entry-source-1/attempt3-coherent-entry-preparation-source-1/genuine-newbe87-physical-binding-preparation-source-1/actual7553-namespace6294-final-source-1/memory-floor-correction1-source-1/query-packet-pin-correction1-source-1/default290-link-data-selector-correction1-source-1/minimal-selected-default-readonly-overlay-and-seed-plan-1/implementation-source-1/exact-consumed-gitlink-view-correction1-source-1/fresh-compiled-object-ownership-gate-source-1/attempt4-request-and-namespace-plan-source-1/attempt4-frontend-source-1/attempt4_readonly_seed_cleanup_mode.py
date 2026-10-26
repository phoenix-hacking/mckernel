"""Functional OS only; no security testing. Exact15fe mode/layout/real result consumers; no runtime entry."""
import hashlib,importlib.util,json
from pathlib import Path
OWNER={'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/native_rust_exact_mckernel_image_container_owner.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py', 'sha256': '15fe434d4e3ce8bea8ad280567b05ed35be4a99f590d695772d3917025ee8fe3', 'bytes': 180380}
INPUT={'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/FROZEN-READONLY-THREE-POSTIMAGE-NINE-OBJECT-INPUTS.json', 'sha256': 'c9af4c64ac2b414caf7d78b9a1b467edbf17d0252554d2b4a402a49bfd75a4b8', 'bytes': 41994}
def auth(row):
 raw=Path(row['path']).read_bytes()
 if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise RuntimeError('exact attempt4seedmodebytes')
 return raw
def owner_module():
 auth(OWNER);spec=importlib.util.spec_from_file_location('actual15fe_seedconsumer',OWNER['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def seed_mounts(request):
 if request.get('readonly_reuse_inputs')!=INPUT['path']:raise RuntimeError('exact attempt4readonlyinputpath')
 auth(INPUT);m=owner_module();m._reuse_layout(json.loads(auth(INPUT)));return [(target,str(source),'bind',not readonly) for source,target,readonly in m._reuse_mounts(INPUT['path'])]
def runtime_paths(request,receipt):
 if receipt['status']!='PASS':return []
 e=Path(request['evidence_root']);o=Path(request['output_root']);result=json.loads((e/'receipt.json').read_bytes());paths={e/'receipt.json',e/'fresh-compiled-rust-ownership-proof.json'}
 for relative in result['inventory']:
  p=Path(relative)
  if p.is_absolute() or '..' in p.parts or str(p)!=relative:raise RuntimeError('seed runtime inventory escapes')
  paths.add(e/p)
 fixed=json.loads(auth(INPUT))
 for row in fixed['objects']:paths.add(o/'build'/row['build_relative'])
 return sorted(str(p) for p in paths)
def validate_receipt(request,receipt,selected,selected_bytes):
 seed_mounts(request)
 if receipt['status']!='PASS':return True
 for path in runtime_paths(request,receipt):selected_bytes(path,selected)
 e=Path(request['evidence_root']);o=Path(request['output_root']);result=json.loads(selected_bytes(str(e/'receipt.json'),selected));owner_module()._validate_driver_result(e,o,result,request)
 return True
