"""Root-owned exact finite publication; reuses reviewed stable_bytes and publish bodies."""
import argparse,hashlib,json,os,types
from pathlib import Path
B=Path(__file__).resolve().parent
REPO=Path('/home/holden/mckernel')
PREFIX='docs/verification/evidence/phase5-current-pass-image-terminal-20261020-1/'
def load(path,expected):
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
 m=types.ModuleType('_publication_'+path.stem);m.__file__=str(path);exec(compile(raw,str(path),'exec'),m.__dict__);return m
def main():
 a=argparse.ArgumentParser();a.add_argument('--allowlist',required=True);a.add_argument('--sha256',required=True);a.add_argument('--execute-copy',action='store_true');v=a.parse_args()
 observer=load(B/'observe_current_pass_image_retirement.py','48e3c313ec376b13918266340879c3fea2bf61d1013b468bf77e2dbf8e212399')
 core=load(REPO/'scripts/native_exact_scratch22_authority1_quarantine_recovery.py','3fdb4dde4dbbd5d07d85d68c02e68d4aee3acca45dce12be3479f3252765abd6')
 path=Path(v.allowlist);raw=observer.stable_bytes(path,v.sha256,1<<20);packet=json.loads(raw)
 rows=list(packet['rows'])+[dict(source=str(path),repository_path=packet['self_extra_blob'],sha256=v.sha256,bytes=len(raw))]
 assert len({r['repository_path'] for r in rows})==len(rows)
 copied=reused=total=0
 for r in rows:
  relative=Path(r['repository_path']);assert not relative.is_absolute() and '..' not in relative.parts and str(relative).startswith(PREFIX)
  data=observer.stable_bytes(Path(r['source']),r['sha256'],128<<20);assert len(data)==r['bytes'];target=REPO/relative;total+=len(data)
  if os.path.lexists(target):observer.stable_bytes(target,r['sha256'],128<<20);reused+=1;continue
  if v.execute_copy:
   target.parent.mkdir(parents=True,exist_ok=True);fd=core.directory(target.parent);os.close(fd);core.publish(target,data);observer.stable_bytes(target,r['sha256'],128<<20)
  copied+=1
 print(json.dumps(dict(status='EXACT_FINITE_COPY_COMPLETE' if v.execute_copy else 'VALIDATED_NO_COPY',rows=len(rows),copied=copied,reused=reused,bytes=total,git_actions=False)))
if __name__=='__main__':main()
