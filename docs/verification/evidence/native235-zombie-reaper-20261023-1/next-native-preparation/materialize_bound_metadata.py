#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-dispatcher ordinary metadata copy under existing RO-mounted N only; no runtime stage.
Preview makes no files. --execute consumes the reserved fresh metadata directory once.
"""
from pathlib import Path
import argparse,hashlib,json,os,stat
E=Path(__file__).resolve().parent
INVENTORY=E/'METADATA-INVENTORY.ACCEPTED.json';INVENTORY_SHA='ad5942b280f59220dae43a9b49445e19a2542c326002a4b483bd2477aeef2142'
ACCEPTANCE=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/sdk-build-release/INDEPENDENT-ACTUAL-SDK-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.json');ACCEPTANCE_SHA='5df70b4414fe418e73b3e01650380ecf58d7a085642cce95b94c611a1a0d9189'
F=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/zombie-sdk-native-successor-1')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def plain(p):assert all(not x.is_symlink()for x in [p,*p.parents])and stat.S_ISREG(p.stat().st_mode);return p

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');a=parser.parse_args();assert sha(plain(INVENTORY))==INVENTORY_SHA and sha(plain(ACCEPTANCE))==ACCEPTANCE_SHA;assert json.loads(ACCEPTANCE.read_text())['status']=='PASS';D=json.loads(INVENTORY.read_text());assert D['future_root']==str(F)and not os.path.lexists(F);assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
 assert F.parent.is_dir()and all(not p.is_symlink()for p in [F.parent,*F.parent.parents]);rows=D['files'];assert len(rows)==30
 for r in rows:
  p=plain(Path(r['source']['path']));relative=Path(r['relative']);assert not relative.is_absolute()and '..'not in relative.parts;assert r['future_path']==str(F/relative)and sha(p)==r['source']['sha256']and p.stat().st_size==r['source']['bytes']
 assert sum(r['source']['bytes']for r in rows)==81298
 statv=os.statvfs(F.parent);assert statv.f_bavail*statv.f_frsize>16*1024**3+81298+1024**2
 result=dict(scope=__doc__.split('\n')[0],status='VALIDATED_PREVIEW_NO_METADATA_MATERIALIZATION',files=len(rows),bytes=81298,future_root=str(F),snapshots=0,stage_operations=0,root_operations=0,Docker_operations=0,guest_runs=0,native_acceptance=False)
 if not a.execute:print(json.dumps(result));return
 F.mkdir(mode=0o700);(F/'runtime-inputs').mkdir(mode=0o700)
 for r in rows:
  dest=F/r['relative'];dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  with dest.open('xb')as f:f.write(Path(r['source']['path']).read_bytes());f.flush();os.fsync(f.fileno())
  dest.chmod(0o600);assert sha(plain(dest))==r['source']['sha256']
 result.update(status='PASS_EXACT_PENDING_METADATA_MATERIALIZATION_ONLY',metadata_files_created=len(rows));
 with(F/'ACTUAL-METADATA-MATERIALIZATION.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result))
if __name__=='__main__':main()
