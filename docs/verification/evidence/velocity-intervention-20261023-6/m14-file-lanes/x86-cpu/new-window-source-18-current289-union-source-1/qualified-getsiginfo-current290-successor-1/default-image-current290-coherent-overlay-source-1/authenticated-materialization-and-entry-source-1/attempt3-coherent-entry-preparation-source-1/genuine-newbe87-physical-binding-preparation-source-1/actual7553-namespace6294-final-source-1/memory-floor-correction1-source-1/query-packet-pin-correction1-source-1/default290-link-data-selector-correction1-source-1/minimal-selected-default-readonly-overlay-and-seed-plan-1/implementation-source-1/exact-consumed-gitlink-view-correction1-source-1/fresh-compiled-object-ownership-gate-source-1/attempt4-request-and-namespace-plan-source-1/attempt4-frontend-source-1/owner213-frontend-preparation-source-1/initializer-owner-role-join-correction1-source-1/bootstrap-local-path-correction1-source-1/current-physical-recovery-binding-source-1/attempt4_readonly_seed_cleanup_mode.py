"""Functional OS only; no security testing. Exact15fe mode/layout/real result consumers; no runtime entry."""
import ast,builtins,hashlib,json,os,stat,symtable,types
from pathlib import Path
OWNER = {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/owner-namespace-constant-reconciliation-source-1/native_rust_exact_mckernel_image_container_owner.CURRENT290.NAMESPACE4-COMMON-BOUND.py', 'sha256': '21378c973de1f12a75978e38056bb2078d933ae28e841e0c1a75e34d818e1a80', 'bytes': 180822}
INPUT={'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/FROZEN-READONLY-THREE-POSTIMAGE-NINE-OBJECT-INPUTS.json', 'sha256': 'c9af4c64ac2b414caf7d78b9a1b467edbf17d0252554d2b4a402a49bfd75a4b8', 'bytes': 41994}
def auth(row):
 raw=Path(row['path']).read_bytes()
 if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise RuntimeError('exact attempt4seedmodebytes')
 return raw
def owner_module():
 raw=auth(OWNER);tree=ast.parse(raw,OWNER['path'])
 functions={'_fail','_sha256','_no_symlink_parents','_safe_regular','_safe_directory','_reuse_require','_reuse_file','_reuse_layout','_reuse_mounts','_validate_driver_result'}
 assignments={'_REUSE_FIXED','_REUSE_INPUT_SHA256','_REUSE_INPUT_BYTES','_REUSE_IDENTITY_BASELINE','_REUSE_FRESH_VALIDATE_RESULT'}
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.ClassDef) and n.name=='OwnerError' or isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id in assignments for v in n.targets)]
 if {n.name for n in nodes if isinstance(n,ast.FunctionDef)}!=functions or sum(isinstance(n,ast.FunctionDef) and n.name=='_validate_driver_result' for n in nodes)!=2:raise RuntimeError('complete exact15fe pure function set')
 if {v.id for n in nodes if isinstance(n,ast.Assign) for v in n.targets if isinstance(v,ast.Name)}!=assignments:raise RuntimeError('complete exact15fe pure constants/alias')
 # Preserve selected definitions and alias in their original source order.
 code=ast.Module(body=nodes,type_ignores=[]);ns=dict(__name__='authenticated15fe_pure_validation_only',__file__=OWNER['path'],Path=Path,hashlib=hashlib,json=json,os=os,stat=stat)
 exec(compile(code,OWNER['path'],'exec'),ns)
 # Compiler symbol tables distinguish true globals from local/comprehension names.
 table=symtable.symtable('\n'.join(ast.get_source_segment(raw.decode('utf-8'),node) for node in nodes),OWNER['path'],'exec');todo=list(table.get_children());dependencies=set()
 while todo:
  child=todo.pop();todo.extend(child.get_children());dependencies.update(symbol.get_name() for symbol in child.get_symbols() if symbol.is_referenced() and symbol.is_global())
 missing=dependencies-set(ns)-set(vars(builtins))
 if missing:raise RuntimeError('unresolved pure15fe dependencies: '+repr(sorted(missing)))
 if any(name in ns for name in ('ImageOwner','CommonExclusion','main','_validate_request','subprocess','fcntl','_SHARED_HEAVY_ENTRY_CONTRACT')):raise RuntimeError('owner/transport code forbidden in pure validation closure')
 module=types.ModuleType(ns['__name__']);module.__dict__.update(ns);module.__dict__['PURE_VALIDATOR_GLOBAL_DEPENDENCIES']=sorted(dependencies);return module

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
