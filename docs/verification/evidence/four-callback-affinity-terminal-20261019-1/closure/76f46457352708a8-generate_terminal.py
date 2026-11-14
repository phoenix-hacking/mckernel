"""Bind existing engines to genuine late902 facts; no execution effects."""
from pathlib import Path
import argparse,ast,hashlib,json,sys,types
T=Path(__file__).resolve().parent;A=T.parent
sys.path.insert(0,str(T))
from case_contract import checked_bytes,need,bind_engine_config
BASE_CONFIG=Path('/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/configure_fourleaf_terminal.py')
PREDECESSOR=Path('/home/holden/mckernel-work/host-preparation/future-four-callback-compiler-preparation-20261019-1/terminal-preparation-1/remaining-only-late-binding-1')
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,raw):
 with p.open('x') as f:f.write(raw)
def generate(known,late,config):
 bind_engine_config(known,late)
 for k in ('physical','pairs','selected_provenance','canonical_report','canonical_gate','canonical_binding'):checked_bytes(config[k],128<<20)
 need(config['canonical_report']==late['artifact_report'],'same actual independent artifact report')
 need(config['canonical_gate']['path']==str(T/'canonical_gate.py'),'fresh205 canonical gate')
 rolemap=json.loads(checked_bytes(known['role_source']))['roles'];count=len(rolemap)
 pairs=late['pairs'];authorities=[]
 for role in rolemap:
  pair=next(p for p in pairs if p['original']['path']==role['original_path'] and p['retained']['path']==role['retained_path'])
  authorities.append(dict(kind=role['role'],original=pair['original'],retained=pair['retained']['path']))
 write(T/'actual-role-retention-authorities.json',json.dumps(authorities,sort_keys=True,indent=2)+'\n')
 process_role=next(r for r in rolemap if r['role']=='process.c.o');process_pair=next(p for p in pairs if p['original']['path']==process_role['original_path']);write(T/'actual-fourleaf-image-object-authority.json',json.dumps(dict(source=process_pair['original'],retained_destination=process_pair['retained']),sort_keys=True,indent=2)+'\n')
 source=checked_bytes(known['configurator']).decode();tree=ast.parse(source);m=types.ModuleType('_accepted_205_configurator');m.__file__=str(BASE_CONFIG);exec(compile(source,str(BASE_CONFIG),'exec'),m.__dict__);m.T=T;m.R=A;m.BASE=Path(known['engines']['observer']['path'])
 for name in ('configure','configure_cleanup'):
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name);fn=ast.get_source_segment(source,node)
  fn=fn.replace("T/'actual21-retention-authorities.json'","T/'actual-role-retention-authorities.json'").replace('==21','==len(paths)' if name=='configure' else '==21')
  if name=='configure':
   # Counts before paths are initialized use the one bound role list; generated
   # pair consumers derive cardinality from their bound roles argument.
   fn=fn.replace('len(pairs)==len(paths) and len({',f'len(pairs)=={count} and len({{',1).replace("for r in pairs})==len(paths)",f"for r in pairs}})=={count}",1)
   fn=fn.replace('len(pairs)==len(paths)', 'len(pairs)==len(roles)').replace('len(set(actual))==len(paths)','len(set(actual))==len(roles)').replace('assert len(paths)==len(paths)', 'assert len(paths)=='+str(count))
   fn=fn.replace('Finite21','BoundRoles').replace('finite21','bound-role')
   fn=fn.replace("'mckernel.independent-rust-four-leaf-image-actual-review.v1'","'mckernel.independent-four-callback-affinity-image-actual-review.v1'").replace("'PASS_ACTUAL_PRODUCTION_IMAGE_ARTIFACT_AND_GUARD_RETIREMENT'","'PASS_ACTUAL_NEW205_PRODUCTION_IMAGE_ARTIFACT_AND_GUARD_RETIREMENT'")
  else:
   old="Path('/home/holden/mckernel/scripts/native_rust_cutover_image_terminal_cleanup.py').read_text()";need(fn.count(old)==1,'accepted cleanup boundary');fn=fn.replace(old,'Path('+repr(known['engines']['cleanup']['path'])+').read_text()')
   line=next(l for l in fn.splitlines() if "old_guard='native-rust-" in l)
   fn=fn.replace(line," old_guard="+repr(known['predecessor_guard_name'])+";current_guard=Path(physical['guard']['path']).parent.name;assert source.count(old_guard)==2;source=source.replace(old_guard,current_guard)")
  exec(compile(fn,str(BASE_CONFIG),'exec'),m.__dict__)
 cleanup=m.configure_cleanup(config);request=json.loads(checked_bytes(known['request'],64<<20));ct=ast.parse(cleanup);lines=cleanup.splitlines(keepends=True)
 values=dict(IMAGE_CANDIDATE=request['candidate_sha'],PREFIX='four-callback-affinity-terminal-20261019-1',PUBLISHED_SCRIPT='docs/verification/evidence/four-callback-affinity-terminal-20261019-1/cleanup_fourleaf.py')
 for n in sorted(ct.body,key=lambda n:n.lineno,reverse=True):
  if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:lines[n.lineno-1:n.end_lineno]=[n.targets[0].id+' = '+repr(values[n.targets[0].id])+'\n']
 cleanup=''.join(lines);old=next(n for n in ast.parse(cleanup).body if isinstance(n,ast.FunctionDef) and n.name=='image_layout');segment=ast.get_source_segment(cleanup,old)
 wrapper="def image_layout(request):\n    import types\n    ref="+repr(known['producer_layout'])+"\n    raw=read_bounded(Path(ref['path']))\n    if digest(raw)!=ref['sha256']:raise Refusal('fresh205-layout-source')\n    layout=types.ModuleType('_fresh205_producer_layout');layout.__file__=ref['path'];exec(compile(raw,layout.__file__,'exec'),layout.__dict__)\n    return layout.authenticated_layout(request)"
 cleanup=cleanup.replace(segment,wrapper,1);compile(cleanup,str(T/'cleanup_fourleaf.py'),'exec');write(T/'cleanup_fourleaf.py',cleanup)
 observer=m.configure(config);observer=observer.replace("NONCE = 'four-leaf-observation-actual-1'","NONCE = 'four-callback-affinity-observation-1'");compile(observer,str(T/'observe_four_leaf_image_retirement.py'),'exec');write(T/'observe_four_leaf_image_retirement.py',observer)
 output=T/'root-observation-four-callback-affinity-observation-1';pins={}
 for name in ('readback_observer.py','read_original_five_metadata.py','export_raw_five.py','postjoin_readback.py'):
  raw=(PREDECESSOR/name).read_text();lines=raw.splitlines(keepends=True);values=dict(OUTPUT=output,NONCE='four-callback-affinity-observation-1',ENGINE=T/'cleanup_fourleaf.py',ENGINE_SHA=ref(T/'cleanup_fourleaf.py')['sha256'],OBSERVER=T/'observe_four_leaf_image_retirement.py',OBSERVER_SHA=ref(T/'observe_four_leaf_image_retirement.py')['sha256'])
  if name!='readback_observer.py':values['SUMMARY_SHA']=ref(T/'readback_observer.py')['sha256']
  for n in sorted(ast.parse(raw).body,key=lambda n:n.lineno,reverse=True):
   if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:
    k=n.targets[0].id;v=values[k];lines[n.lineno-1:n.end_lineno]=[k+' = '+('Path('+repr(str(v))+')' if isinstance(v,Path) else repr(v))+'\n']
  raw=''.join(lines);compile(raw,str(T/name),'exec');write(T/name,raw);pins[name]=ref(T/name)
 pins.update({p.name:ref(p) for p in [T/'cleanup_fourleaf.py',T/'observe_four_leaf_image_retirement.py']});write(T/'generated-helper-pins.json',json.dumps(pins,sort_keys=True,indent=2)+'\n');return dict(status='PREPARED_SIX_SOURCES_NO_EXECUTION',roles=count,metadata_rows=2*count,pins=pins)
def main():
 p=argparse.ArgumentParser()
 for n in ('known','late','config'):p.add_argument('--'+n,required=True);p.add_argument('--'+n+'-sha256',required=True)
 a=p.parse_args();v={n:json.loads(checked_bytes(dict(path=getattr(a,n),sha256=getattr(a,n+'_sha256')),128<<20)) for n in ('known','late','config')};result=generate(**v);print(json.dumps(dict(status=result['status'],roles=result['roles'],metadata_rows=result['metadata_rows'])))
if __name__=='__main__':main()
