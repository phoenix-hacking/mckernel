"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare four private source postimages and one exact unified patch; no live operations.
"""
import ast,datetime,difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent
B=D.parent/'current290-corrected-driver-successor-binding-source-1/frontend-source-1'
S=D/'attempt5-preclock-postimages';S.mkdir(exist_ok=True)
R=B/'initializer-runtime-role-source-1'
refs=json.loads((R/'FRONTEND-INTEGRATION-REFERENCES.NOT-RELEASED.json').read_text())['replacement_references']
oldh,newh=refs[0]['before'],refs[0]['after']
oldd,newd=refs[1]['before'],refs[1]['after']
changed={}
def ref(name,raw):return dict(path=str(B/name),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def emit(name,value):
 raw=value.encode() if isinstance(value,str) else (json.dumps(value,indent=2)+'\n').encode()
 changed[name]=raw;(S/name).write_bytes(raw);return ref(name,raw)
def replace_ref_text(text,before,after):
 # Exact literal triplet, including byte size; no arbitrary flag masking.
 for a,z in ((before['path'],after['path']),(before['sha256'],after['sha256'])):
  assert a in text,a;text=text.replace(a,z)
 text=text.replace("'bytes': "+str(before['bytes']),"'bytes': "+str(after['bytes']))
 return text
ctxname='ROOT-PREPARATION-CONTEXT.ATTEMPT5.READONLY-SEED.PENDING-HOLDER-CLOCK-GRANTS.json'
ctx=json.loads((B/ctxname).read_text());assert ctx['static_source_origin_binding']==oldd
ctx['static_source_origin_binding']=newd
ctxref=emit(ctxname,ctx)
fillname='fill_existing_current290_image_payload.ATTEMPT5.READONLY-SEED.py'
fill=replace_ref_text((B/fillname).read_text(),oldh,newh)
# SOURCES includes original helper and its matching data reference.
fill=fill.replace(oldd['path'],newd['path']).replace('fill_existing_current290_image_payload.ATTEMPT4.READONLY-SEED.py',fillname)
fillref=emit(fillname,fill)
configname='FROZEN-CURRENT290-IMAGE-ENTRY-INPUTS.ATTEMPT5.READONLY-SEED.json'
cfg=json.loads((B/configname).read_text());assert cfg['source_origin_binding']==oldh
cfg['source_origin_binding']=newh
cfg['deadline_epoch']=int(datetime.datetime.fromisoformat('2026-10-27T11:24:50+00:00').timestamp())
# Do not present the consumed old namespace receipt as attempt5 initialization.
assert cfg['commands']['namespace_initialization']['receipt']['sha256'].startswith('1d307')
cfg['commands']['namespace_initialization'].update(receipt=None,status='PENDING_ACTUAL_ATTEMPT5_INITIALIZATION_NOT_RELEASED')
def update_refs(x):
 if isinstance(x,dict):
  if set(x)=={'path','sha256','bytes'}:
   p=Path(x['path'])
   if p.parent==B and p.name in changed:return ref(p.name,changed[p.name])
  return {k:update_refs(v) for k,v in x.items()}
 if isinstance(x,list):return [update_refs(v) for v in x]
 return x
cfg=update_refs(cfg);cfgref=emit(configname,cfg)
callername='run_frozen_current290_image_entry.ATTEMPT5.READONLY-SEED.py'
caller=replace_ref_text((B/callername).read_text(),oldh,newh)
caller=caller.replace('FROZEN-CURRENT290-IMAGE-ENTRY-INPUTS.ATTEMPT4.READONLY-SEED.json',configname)
caller=re.sub(r"CONFIG_SHA = '[a-f0-9]{64}'",'CONFIG_SHA = '+repr(cfgref['sha256']),caller,count=1)
emit(callername,caller)
class Clear(ast.NodeTransformer):
 def visit_Constant(self,n):return ast.copy_location(ast.Constant('SOURCE_CONSTANT'),n)
def funcs(raw):
 t=ast.parse(raw)
 return [ast.dump(Clear().visit(n),include_attributes=False) for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
for name in (fillname,callername):assert funcs((B/name).read_bytes())==funcs(changed[name]),name
assert cfg['deadline_epoch']==1793100290
assert all(cfg[k] is None for k in ('physical','postjoin','namespace_initialization','new_post_shared_physical_consumer'))
assert all(ctx[k] is None for k in ('actual_current_live_postjoin','actual_current_physical','actual_namespace_initialization','actual_devflock_holder','static_source_publication'))
assert cfg['pins']['owner']['sha256'].startswith('735cfd') and cfg['pins']['driver']['sha256'].startswith('9d2d39')
for x in (fill,caller):assert oldh['path'] not in x and oldh['sha256'] not in x
assert oldd['path'] not in fill
patch=''.join(''.join(difflib.unified_diff((B/n).read_text().splitlines(True),raw.decode().splitlines(True),fromfile=str(B/n),tofile=str(B/n))) for n,raw in changed.items())
(D/'attempt5-preclock-bindings.patch').write_text(patch)
result=dict(scope=__doc__.splitlines()[0],status='PASS_FOUR_PRIVATE_SOURCE_POSTIMAGES_NOT_RELEASED',changed=list(changed),callable_shapes_unchanged=True,null_physical_holder_publication_slots_preserved=True,owner='735cfd6e',driver='9d2d39a0',helper='8708018b',deadline_epoch=cfg['deadline_epoch'],deadline='2026-10-27T11:24:50Z',no_compiler_native_root_admission=True,source6153_nineobjects_SDK21_preserved=True,staged_references_target='Original frontend paths after root integration; do not execute staged copies',patch=str(D/'attempt5-preclock-bindings.patch'))
(D/'ATTEMPT5-PATCH-RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
