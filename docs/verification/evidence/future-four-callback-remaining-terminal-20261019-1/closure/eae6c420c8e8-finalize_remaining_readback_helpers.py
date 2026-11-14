"""Exact case-global binding of accepted finite readback helpers; no execution."""
from pathlib import Path
import argparse,ast,hashlib,json
L=Path(__file__).resolve().parent;F=L.parent/'failure-preparation-1'
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def main():
 a=argparse.ArgumentParser();a.add_argument('--known',required=True);a.add_argument('--known-sha256',required=True);x=a.parse_args();p=Path(x.known);assert ref(p)['sha256']==x.known_sha256;known=json.loads(p.read_bytes());assert known['request']['sha256']=='9f04f3a318594cb6eeceab55b63aa6b1ca4cb0aa95caf7371be9507296abd26d'
 cleanup=L/'cleanup_fourleaf.py';observer=L/'observe_four_leaf_image_retirement.py';assert cleanup.is_file() and observer.is_file()
 nonce='future-four-callback-remaining-observation-1';output=L/('root-observation-'+nonce)
 for name in ('readback_observer.py','read_original_five_metadata.py','export_raw_five.py','postjoin_readback.py'):
  source=(F/name).read_text();values=dict(OUTPUT=output,NONCE=nonce,ENGINE=cleanup,ENGINE_SHA=ref(cleanup)['sha256'],OBSERVER=observer,OBSERVER_SHA=ref(observer)['sha256'])
  if name!='readback_observer.py':values['SUMMARY_SHA']=ref(L/'readback_observer.py')['sha256']
  rows=source.splitlines(keepends=True)
  for node in sorted(ast.parse(source).body,key=lambda n:n.lineno,reverse=True):
   if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in values:
    key=node.targets[0].id;v=values[key];rows[node.lineno-1:node.end_lineno]=[key+' = '+('Path('+repr(str(v))+')' if isinstance(v,Path) else repr(v))+'\n']
  path=L/name;source=''.join(rows);compile(source,str(path),'exec')
  with path.open('x') as f:f.write(source)
 for key,name in [('summary','readback_observer.py'),('metadata','read_original_five_metadata.py'),('raw_export','export_raw_five.py'),('postjoin','postjoin_readback.py')]:
  known['engines'][key]=ref(L/name);known['full_import_closure'][str(L/name)]=known['engines'][key]['sha256']
 out=L/'remaining-known-inputs-terminal-generated.json'
 with out.open('x') as f:json.dump(known,f,sort_keys=True,indent=2);f.write('\n')
 pins=L/'generated-terminal-helper-pins.json'
 with pins.open('x') as f:json.dump({p.name:ref(p) for p in [cleanup,observer,*[L/n for n in ('readback_observer.py','read_original_five_metadata.py','export_raw_five.py','postjoin_readback.py')]]},f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps(dict(status='PREPARED_SIX_BOUND_TERMINAL_SOURCES_NO_EXECUTION',known=ref(out),pins=ref(pins),metadata_rows_rule='2*len(validated_actual21_pairs)',cleanup_canonical='JSON_SORTED_COMPACT_NO_NEWLINE')))
if __name__=='__main__':main()
