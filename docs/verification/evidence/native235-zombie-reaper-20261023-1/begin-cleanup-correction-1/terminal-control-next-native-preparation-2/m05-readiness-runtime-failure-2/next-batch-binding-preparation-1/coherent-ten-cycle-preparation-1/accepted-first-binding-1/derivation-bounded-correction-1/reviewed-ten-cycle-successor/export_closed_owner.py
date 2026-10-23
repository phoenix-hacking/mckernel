"""Exact released owner-directory export; parameterization of accepted42eb recipe.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import argparse,base64,hashlib,json,os,stat

def export(parent,nonce,owner_sha):
 assert len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce)
 parent=Path(parent);assert parent.is_absolute() and '..' not in parent.parts
 root=parent.with_name(parent.name+'.owner-'+nonce)
 s=root.lstat();assert stat.S_ISDIR(s.st_mode) and not root.is_symlink() and s.st_uid==s.st_gid==0 and stat.S_IMODE(s.st_mode)==0o700
 names=sorted(os.listdir(root));assert len(names)<=4096
 rows=[];total=0
 for name in names:
  assert name not in('.','..') and '/' not in name
  fd=os.open(str(root/name),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  with os.fdopen(fd,'rb') as f:
   before=os.fstat(f.fileno());assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=8*2**20
   total+=before.st_size;assert total<=8*2**20
   raw=f.read(before.st_size+1);after=os.fstat(f.fileno());named=(root/name).lstat()
   keys=('st_dev','st_ino','st_uid','st_gid','st_mode','st_size','st_nlink','st_mtime_ns','st_ctime_ns')
   assert len(raw)==before.st_size and all(getattr(before,k)==getattr(after,k)==getattr(named,k)for k in keys)
  rows.append(dict(name=name,source_path=str(root/name),identity={k:getattr(after,k)for k in keys},sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode()))
 assert sorted(os.listdir(root))==names
 files={r['name']:base64.b64decode(r['base64']) for r in rows};owner=json.loads(files['owner.json']);terminal=json.loads(files['result.json'])
 assert owner['nonce']==nonce and owner['owner_sha256']==owner_sha and owner['attempt']==str(parent/('attempt-'+nonce))
 assert terminal['absence_verified'] is True and terminal['lease_retained'] is False
 result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='READONLY_EXACT_CLOSED_OWNER_EVIDENCE_EXPORT',root=str(root),root_identity=dict(dev=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode)),files=rows,total_source_bytes=total,root_mutations=0)
 encoded=json.dumps(result,sort_keys=True,separators=(',',':'));assert len(encoded.encode())+1<=16*2**20;return encoded
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--parent',required=True);p.add_argument('--nonce',required=True);p.add_argument('--owner-sha256',required=True);a=p.parse_args();print(export(a.parent,a.nonce,a.owner_sha256))
