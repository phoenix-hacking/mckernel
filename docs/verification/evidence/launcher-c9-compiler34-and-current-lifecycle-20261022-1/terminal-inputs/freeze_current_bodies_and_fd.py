"""Freeze nine unchanged machinery bodies and complete generated-file FD identity.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite source/data operation only; no execution or physical-release authority.
"""
from pathlib import Path
import argparse,ast,hashlib,json,os,stat
HERE=Path(__file__).resolve().parent
PAIRS=(('engine','cleanup_launcher.py'),('observer','observe_current_launcher_retirement.py'),
 ('fresh','check_launcher_fresh_preflight.py'),('postjoin','postjoin_launcher.py'),
 ('readback_observer.py','readback_observer.py'),('read_original_five_metadata.py','read_original_five_metadata.py'),
 ('export_raw_five.py','export_raw_five.py'),('capture_first_four.py','capture_first_four.py'),
 ('capture_critical_two.py','capture_critical_two.py'))
def bodies(raw):
 return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def fdrow(path):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1
  h=hashlib.sha256();size=0
  while True:
   b=os.read(fd,1<<20)
   if not b:break
   size+=len(b);h.update(b)
  after=os.fstat(fd)
  fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  assert all(getattr(before,k)==getattr(after,k) for k in fields) and size==before.st_size
  assert os.stat(path,follow_symlinks=False)==after
  return dict(path=str(path),device=before.st_dev,inode=before.st_ino,uid=before.st_uid,gid=before.st_gid,
    mode=before.st_mode,nlink=before.st_nlink,size=size,mtime_ns=before.st_mtime_ns,ctime_ns=before.st_ctime_ns,sha256=h.hexdigest())
 finally:os.close(fd)
def main():
 p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--preparation-only',action='store_true');a=p.parse_args()
 output=Path(a.directory);assert output.is_absolute() and output.resolve()==output and HERE in output.parents
 pins=json.loads((output.parent/'BINDER-INPUT-PINS-CURRENT.json').read_bytes());checks={}
 for template,name in PAIRS:
  row=pins['templates'][template];raw=Path(row['path']).read_bytes()
  assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
  generated=(output/name).read_bytes();assert bodies(raw)==bodies(generated),name
  checks[name]=dict(template=row,function_class_AST_unchanged=True,
    function_class_AST_sha256=hashlib.sha256(json.dumps(bodies(generated),sort_keys=True).encode()).hexdigest())
 rows=[fdrow(f) for f in sorted(output.iterdir()) if f.is_file()]
 assert len(checks)==9 and all(any(r['path']==str(output/name) for r in rows)for _,name in PAIRS)
 result=dict(status='NINE_FUNCTION_CLASS_BODIES_UNCHANGED_FULL_GENERATED_FD_MATRIX',
  preparation_only_not_root_record=a.preparation_only,body_checks=checks,generated_file_FD_rows=rows,
  observer_executed=False,physical_release=None,cleanup_release=None,runtime_release=None)
 with (output/'FINAL-FROZEN-FUNCTION-AND-FD-MATRIX.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps(dict(status=result['status'],body_count=len(checks),fd_rows=len(rows),preparation_only=a.preparation_only)))
if __name__=='__main__':main()
