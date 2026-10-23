#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Dispatcher-run ordinary source staging only. No container/compiler/root operation.
Preview is read-only. --execute materializes one fresh reserved nonce, without retry.
"""
from pathlib import Path
import argparse,hashlib,json,os,stat,time
H=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/service-ebusy-sdk-preparation-8/prepared-sdk')
PREP_SHA='57fce4d1aa9080016eea352a8a48725ef26a46ffca2c457318f95038081fe497'
NONCE='30717e2c0ee840ffa441d577bed3a427'
ROOT=Path('/home/holden/mckernel-work/scratch')
OUTPUT=Path('/home/holden/mckernel-work/host-preparation/native-running-modules-host-output')
BASIS=ROOT/'mckernel-exact-candidate-scratch-22-authority3-output'
BACKING=ROOT.parent/'scratch.ext4'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def plain(p,private=True):
 assert all(not a.is_symlink() for a in (p,*p.parents)),str(p)
 assert stat.S_ISREG(p.stat().st_mode) and (not private or p.stat().st_nlink==1),str(p)
 return p

def node(p):
 m=p.stat();return dict(path=str(p),device=m.st_dev,inode=m.st_ino,mode=stat.S_IMODE(m.st_mode),uid=m.st_uid,gid=m.st_gid)
def save(p,value):
 with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n')

def main():
 args=argparse.ArgumentParser(description=__doc__);args.add_argument('--execute',action='store_true');a=args.parse_args()
 prep=H/'preparation.json';assert digest(plain(prep))==PREP_SHA;manifest=json.loads(prep.read_text())
 assert digest(plain(H/'REQUEST.TEMPLATE.PENDING-LIVE-IDENTITIES.json'))=='f06eaf0c38ee55e2948e83394a4b0ae144c84c5707b1aa7194099f14bde43081'
 request=json.loads((H/'REQUEST.TEMPLATE.PENDING-LIVE-IDENTITIES.json').read_text());assert request['nonce']==NONCE
 candidate=Path(request['candidate_root']);inputs=Path(request['input_root']);evidence=Path(request['owner_evidence_root'])
 assert candidate==OUTPUT/('native-running-modules-candidate-'+NONCE)
 assert inputs==ROOT/('native-running-modules-inputs-'+NONCE)
 assert evidence==OUTPUT/('native-running-modules-owner-'+NONCE)
 assert request['request_path']==str(H/'request.json')
 assert not any(os.path.lexists(x)for x in [candidate,inputs,evidence,H/'request.json',H/'staging-once'])
 sources=[];refs=[]
 for row in manifest['closure']:
  source=H/'source-modules'/row['path'];assert digest(plain(source))==row['sha256'] and source.stat().st_size==row['bytes'];sources.append((source,row))
 expected_inputs={'preparation.json':{'sha256':PREP_SHA,'bytes':prep.stat().st_size}}
 expected_inputs.update({Path(row['retained_copy']).name:row for row in manifest['references'].values()})
 assert len(expected_inputs)==15 and {p.name for p in(H/'prepared-inputs').iterdir()}==set(expected_inputs)
 for name,row in expected_inputs.items():
  source=H/'prepared-inputs'/name;assert digest(plain(source))==row['sha256'] and source.stat().st_size==row['bytes'];refs.append((source,row))
 for name,row in json.loads((H/'RUNTIME-COHORT.json').read_text()).items():assert digest(plain(Path(row['path']),private=False))==row['sha256']
 fresh={'host_free':os.statvfs(OUTPUT).f_bavail*os.statvfs(OUTPUT).f_frsize,'scratch_free':os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize,'at':time.time()}
 source_bytes=sum(row['bytes']for _,row in sources);input_bytes=sum(row['bytes']for _,row in refs)
 assert fresh['host_free']>16*1024**3+source_bytes+1024**2
 assert fresh['scratch_free']>12*1024**3+input_bytes+1024**2
 assert os.getuid()==os.getgid()==1000
 output=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='VALIDATED_PREVIEW_NO_STAGING',source_files=len(sources),source_bytes=source_bytes,input_files=len(refs),input_bytes=input_bytes,nonce=NONCE,fresh_space=fresh,request_path=request['request_path'],candidate_root=str(candidate),input_root=str(inputs),execution_release=False,compiler_runs=0,Docker_operations=0,root_operations=0)
 if not a.execute:print(json.dumps(output,indent=2));return
 # This once-only marker and all partial source copies are retained after failure.
 marker=H/'staging-once';marker.mkdir(mode=0o700);save(marker/'intent.json',output)
 candidate.mkdir(mode=0o700);(candidate/'modules').mkdir(mode=0o700);(candidate/'home').mkdir(mode=0o700);(candidate/'tmp').mkdir(mode=0o700);inputs.mkdir(mode=0o700)
 for source,row in sources:
  dest=candidate/'modules'/row['path'];dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  with dest.open('xb')as f:f.write(source.read_bytes())
  dest.chmod(0o600);assert digest(plain(dest))==row['sha256']
 for source,row in refs:
  dest=inputs/source.name
  with dest.open('xb')as f:f.write(source.read_bytes())
  dest.chmod(0o600);assert digest(plain(dest))==row['sha256']
 request['basis_identity']=node(BASIS);request['candidate_identity']=node(candidate);request['input_identity']=node(inputs);request['output_parent_identity']=node(OUTPUT);request['backing_identity']=dict(node(BACKING),size=BACKING.stat().st_size,nlink=BACKING.stat().st_nlink);request['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 save(H/'request.json',request);output.update(status='SOURCE_INPUTS_STAGED_EXACT_REQUEST_NO_EXECUTION_RELEASE',request_sha256=digest(H/'request.json'),candidate_identity=request['candidate_identity'],input_identity=request['input_identity'],fresh_backing_identity=request['backing_identity'])
 save(marker/'result.json',output);print(json.dumps(output,indent=2))
if __name__=='__main__':main()
