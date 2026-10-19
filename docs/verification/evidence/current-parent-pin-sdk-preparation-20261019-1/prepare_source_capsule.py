"""Finite source/data preparation for current parent-slot pin SDK build. No compiler/owner/container."""
from pathlib import Path
import hashlib,json,uuid
N=Path(__file__).resolve().parent
OLD=Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-sdk-20261019-1')
COMMIT='766805fa5c8674c514a96c55f99398f250aa8af8'
OLD_COMMIT='257ba169b58eebd066281020999ec760bfc2f4e0'
OLD_HASH='127829f3dd35b3d44c2b098279b7439dccb31a53508055e3cdd1fd9e450682e2'
NEW_HASH='fd375f11a43dbd205c08decdff10d94c2bb82935ae2ddfeaf1ea7142a5c70146'
NEW_SOURCE=Path('/home/holden/mckernel/host-kernel/native-rust/smp_application.rs')
PREP_NAME='current-parent-pin-sdk-preparation-20261019-1.json'
NONCE='69ca1588db9e4cd89536e677f0130f36'
ROOT=Path('/home/holden/mckernel-work/scratch')
CANDIDATE=ROOT/('nsd-c-'+NONCE);INPUTS=ROOT/('nsd-i-'+NONCE);EVIDENCE=ROOT/('nsd-o-'+NONCE)
LEASE=ROOT/'native-current-parent-pin-sdk-external-modules.lease.json'
COMMON=ROOT/'native-current-parent-pin-sdk-external-modules-operational-exclusion.json'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def raw(ref):
 b=Path(ref['path']).read_bytes();assert digest(b)==ref['sha256'] and len(b)==ref['bytes'];return b
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=digest(b),bytes=len(b))
def put(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
def copy(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
 assert p.read_bytes()==b

def main():
 # This producer itself requires ordinary admission. No scratch namespace is created here.
 assert not (N/'capsule').exists() and not (N/'source-modules').exists()
 assert not any(p.exists() for p in (CANDIDATE,INPUTS,EVIDENCE,LEASE,COMMON,N/'request.json'))
 oldindex=json.loads((OLD/'CAPSULE-AND-MATERIALIZATION-INDEX.json').read_bytes())
 binding=json.loads((N/'SOURCE-BINDING.json').read_bytes())
 for r in binding['accepted_reports'].values():raw(r)
 oldprep=json.loads(raw(oldindex['preparation']));oldrows=json.loads(raw(oldindex['materialization_files']));oldmap=json.loads(raw(oldindex['source_map']))
 assert len(oldprep['closure'])==60 and len(oldrows)==75 and len(oldmap)==11
 newbody=NEW_SOURCE.read_bytes();assert digest(newbody)==NEW_HASH and len(newbody)==48311
 # The only host Rust source delta. Read/hash/write the same snapshot for every row.
 for row in oldrows[:60]:
  name=Path(row['destination']).relative_to(Path(json.loads((OLD/'request-TEMPLATE.json').read_bytes())['candidate_root'])/'modules')
  b=newbody if str(name)=='smp_application.rs' else raw(row['source'])
  if str(name)=='smp_application.rs':assert row['source']['sha256']==OLD_HASH
  copy(N/'source-modules'/name,b)
 oldq=json.loads((OLD/'request-TEMPLATE.json').read_bytes());oldc=oldq['candidate_root'];oldi=oldq['input_root'];oldo=oldq['owner_evidence_root']
 def rebind(x):
  if isinstance(x,str):return x.replace(oldc,str(CANDIDATE)).replace(oldi,str(INPUTS)).replace(oldo,str(EVIDENCE))
  if isinstance(x,list):return [rebind(y) for y in x]
  if isinstance(x,dict):return {k:rebind(v) for k,v in x.items()}
  return x
 prep=rebind(oldprep)
 for row in prep['closure']:
  if row['path']=='smp_application.rs':row.update(sha256=NEW_HASH,bytes=48311,reviewed_replacement=True,parent_source_sha256=OLD_HASH)
 prep.update(task_id='current-parent-pin-sdk-preparation-20261019-1',source_candidate_sha=COMMIT,parent_source_candidate_sha=OLD_COMMIT,closure_bytes=sum(r['bytes'] for r in prep['closure']),source_commit_binding=dict(commit=COMMIT,pending=False,verification=binding['shipped_source_proof']),only_delta=[binding['only_delta']],source_copy_method='60 pinned source snapshots; only smp_application parent-slot pin differs from accepted current host pair; no compiled object reuse',source_closure_reused_without_recopy_or_rehash=False,source_review=binding['parent_pin_source_review'],execution_authorized=False,execution_demonstrated=False,production_acceptance=False,acceptance=False,blocker='Actual ordinary materialization/independent exact compiler release/publication/live admission pending')
 prep['provenance_closure_sha256']=digest(json.dumps(prep['closure'],sort_keys=True,separators=(',',':')).encode())
 assert prep['closure_bytes']==1214162
 pp=N/'capsule/docs/verification/evidence'/PREP_NAME;put(pp,prep);ph=ref(pp)['sha256']
 # Reuse all accepted engines, adjusting only source-binding literals.
 oldph=oldindex['preparation']['sha256'];newmap={}
 for name,h in oldmap.items():
  b=(OLD/'capsule'/name).read_bytes();assert digest(b)==h
  if name.endswith('native_running_external_modules_offline.py'):
   text=b.decode().replace(OLD_COMMIT,COMMIT).replace(oldph,ph).replace('1212003','1214162').replace(OLD_HASH,NEW_HASH);b=text.encode()
  elif name.endswith('native_running_external_modules_owner.py'):
   text=b.decode().replace(OLD_COMMIT,COMMIT).replace(oldph,ph).replace('current-host-rust-pair-sdk-preparation-20261019-1.json',PREP_NAME).replace('native-current-host-rust-pair-external-modules','native-current-parent-pin-sdk-external-modules');b=text.encode()
  copy(N/'capsule'/name,b);newmap[name]=digest(b)
 put(N/'source-sha256.json',newmap)
 q=dict(oldq);q.update(nonce=NONCE,candidate_root=str(CANDIDATE),input_root=str(INPUTS),owner_evidence_root=str(EVIDENCE),lease_path=str(LEASE),common_exclusion_path=str(COMMON),request_path=str(N/'request.json'),candidate_identity=None,input_identity=None)
 driver=N/'capsule/scripts/native_running_external_modules_offline.py';owner=N/'capsule/scripts/native_running_external_modules_owner.py';q['driver']={k:v for k,v in ref(driver).items() if k!='bytes'};q['preparation']={k:v for k,v in ref(pp).items() if k!='bytes'}
 put(N/'request-TEMPLATE.json',q)
 rows=[]
 for row in oldrows:
  destination=rebind(row['destination'])
  if destination.startswith(str(CANDIDATE)+'/modules/'):
   source=N/'source-modules'/Path(destination).relative_to(CANDIDATE/'modules')
  elif destination==str(INPUTS/'preparation.json'):source=pp
  else:
   source=N/'prepared-inputs'/Path(destination).name;copy(source,raw(row['source']))
  rows.append(dict(destination=destination,source=ref(source)))
 assert len(rows)==75 and len([r for r in rows if str(CANDIDATE)+'/modules/' in r['destination']])==60
 put(N/'materialization-files.json',rows)
 index=dict(oldindex);index.update(nonce=NONCE,driver=ref(driver),owner=ref(owner),preparation=ref(pp),request_template=ref(N/'request-TEMPLATE.json'),materialization_files=ref(N/'materialization-files.json'),source_map=ref(N/'source-sha256.json'),proof=ref(N/'prepared-inputs/make-pipe-proof.json'),status='PROPOSAL_ONLY_NO_EXECUTION_AUTHORITY',target_namespaces_absent=True)
 put(N/'CAPSULE-AND-MATERIALIZATION-INDEX.json',index)
 print(json.dumps(dict(status='PREPARED_FINITE_SOURCE_CAPSULE_ONLY',source_files=60,copy_rows=75,catalog=11,source_bytes=1214162,scratch_namespaces_created=0)))
if __name__=='__main__':main()
