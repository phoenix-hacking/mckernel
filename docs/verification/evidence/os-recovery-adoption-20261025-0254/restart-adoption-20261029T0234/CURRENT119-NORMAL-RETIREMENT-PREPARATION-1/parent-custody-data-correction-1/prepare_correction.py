"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixed source/DATA correction; no live process/Docker/guard/native operation.
"""
from pathlib import Path
import json,hashlib,re,copy
D=Path(__file__).resolve().parent;OLD=D.parent
FREE=OLD.parent/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/LIVE-REVALIDATION-CAP-CORRECTION-1/actual-postjoin-acceptance-1/CURRENT-FREE.ACTUAL.json'
FREE_SHA='8104e4fc9bbb7decb5f977c80965d9de3c18b29a94b47f3c5f4e130b1546619b'
def ref(p):
 b=Path(p).read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def authenticated(r):
 if type(r)is not dict or set(r)!={'path','bytes','sha256'}or ref(Path(r['path']))!=r:raise ValueError('exact immutable byte proof required')
 return json.loads(Path(r['path']).read_text())
def validate_parent_proof(free_ref,parent_ref):
 if free_ref!=ref(FREE)or free_ref['sha256']!=FREE_SHA:raise ValueError('exact accepted free8104 required')
 f=authenticated(free_ref)
 if f['capture_positive_join']!=parent_ref:raise ValueError('parent reference does not match accepted free')
 raw=authenticated(parent_ref);declared=f['capture_outer_parent'];parent=raw['parent']
 if not (declared['pid']==parent['pid']==raw['parent_pid']==2540830 and declared['birth']==parent['birth']==raw['parent_birth']==110130087 and declared['group']is None):raise ValueError('exact recorded outer parent birth; no inherited-group claim')
 if not (raw['author']=='/root'and raw['returncode']==0 and raw['positive_direct_parent_wait']is True and raw['positive_wait4_join']is True and raw['parent_streams_closed']is True):raise ValueError('genuine parent receipt closure required')
 return dict(pid=declared['pid'],start=declared['birth'],role='accepted_CURRENT118_capture_outer_parent',group=None,fd=None)
def write(name,value):(D/name).write_text(json.dumps(value,indent=2)+'\n')
def main():
 assert not (D/'BINDINGS.json').exists();free_ref=ref(FREE);f=authenticated(free_ref);parent_ref=f['capture_positive_join'];parent=validate_parent_proof(free_ref,parent_ref)
 b=json.loads((OLD/'BINDINGS.json').read_text());oldactors=copy.deepcopy(b['prior_actors']);assert len(oldactors)==167 and not any(x['pid']==parent['pid']for x in oldactors);b['prior_actors']=oldactors+[parent]
 if parent_ref not in b['actor_evidence']:b['actor_evidence'].append(parent_ref)
 packet=authenticated(b['packet']);packet['source_refs']['accepted_capture_current_free']=free_ref;packet['source_refs']['accepted_capture_outer_parent_join']=parent_ref;write('NORMAL-RETIREMENT-PACKET.json',packet)
 protected=authenticated(b['protected'])
 for r in [free_ref,parent_ref]:
  if not any(x.get('path')==r['path']for x in protected['records']):protected['records'].append(dict(kind='file',**r))
 write('PROTECTED-ORIGINALS.json',protected)
 b['packet']=ref(D/'NORMAL-RETIREMENT-PACKET.json');b['protected']=ref(D/'PROTECTED-ORIGINALS.json');b['output_root_parent']=str(D);write('BINDINGS.json',b)
 s=(OLD/'retire_exact_current119_stopped_container.py').read_text();oldsha=ref(OLD/'BINDINGS.json')['sha256'];assert s.count("BINDINGS_SHA='"+oldsha+"'")==1;s=s.replace("BINDINGS_SHA='"+oldsha+"'","BINDINGS_SHA='"+ref(D/'BINDINGS.json')['sha256']+"'");(D/'retire_exact_current119_stopped_container.py').write_text(s)
 files=json.loads((OLD/'RUNTIME-FILES.json').read_text())
 for k,n in [('executor','retire_exact_current119_stopped_container.py'),('bindings','BINDINGS.json'),('packet','NORMAL-RETIREMENT-PACKET.json'),('protected','PROTECTED-ORIGINALS.json')]:files[k]=ref(D/n)
 write('RUNTIME-FILES.json',files)
 release=json.loads((OLD/'RELEASE.TEMPLATE.NOT-AUTHORITY.json').read_text());release.update(bindings=files['bindings'],files=files,output=str(D/'actual-retirement-current119-root1'));write('RELEASE.TEMPLATE.NOT-AUTHORITY.json',release)
 write('PARENT-PROOF-BINDING.json',dict(accepted_free=free_ref,raw_parent_join=parent_ref,appended_actor=parent,prior167_retained_exact=True,new_prior_frontier_count=168,unchanged_current119_actors=b['new_known_actors']))
 print(json.dumps(dict(status='SOURCE_DATA_CORRECTION_ONLY',frontier_count=len(b['prior_actors']),parent=parent)))
if __name__=='__main__':main()
