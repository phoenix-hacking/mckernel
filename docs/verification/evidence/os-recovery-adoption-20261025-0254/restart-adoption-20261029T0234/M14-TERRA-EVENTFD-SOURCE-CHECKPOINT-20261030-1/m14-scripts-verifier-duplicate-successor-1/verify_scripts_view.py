#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Verify a future private scripts directory against a hash-bound union manifest.
The caller must independently authenticate and supply the expected manifest digest.
Not an authentication, ownership, ACL, mount, namespace, global snapshot, or release validator.
"""
import argparse, hashlib, json, os, pathlib, re, stat, sys
class Reject(Exception): pass
def ensure(ok,message):
 if not ok: raise Reject(message)
def reject_duplicate_json_keys(pairs):
 d={}
 for key,value in pairs:
  ensure(key not in d,'duplicate JSON key: '+key)
  d[key]=value
 return d
def stable(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def mode(s):return format(stat.S_IMODE(s.st_mode),'04o')
def index_manifest(raw):
 ensure(isinstance(raw,dict) and isinstance(raw.get('base_members'),list) and isinstance(raw.get('additions'),list),'manifest schema')
 rootmode=raw.get('base_root_mode');ensure(isinstance(rootmode,str) and re.fullmatch('[0-7]{4}',rootmode),'root mode')
 indexed={}
 for x in raw['base_members']+raw['additions']:
  ensure(isinstance(x,dict),'entry type');p=x.get('path');kind=x.get('type');m=x.get('mode')
  ensure(isinstance(p,str) and p!='' and not p.startswith('/') and all(y not in ('','.','..') for y in p.split('/')),'invalid path')
  ensure(p not in indexed,'duplicate path');ensure(kind in ('file','directory'),'symlink or unsupported manifest type')
  ensure(isinstance(m,str) and re.fullmatch('[0-7]{4}',m),'invalid mode')
  if kind=='file':ensure(type(x.get('bytes')) is int and x['bytes']>=0 and isinstance(x.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',x['sha256']),'invalid file metadata')
  indexed[p]=x
 for p in indexed:
  parent=p.rpartition('/')[0]
  if parent:ensure(parent in indexed and indexed[parent]['type']=='directory','missing directory parent')
 return rootmode,indexed
def check(root,rootmode,expected):
 ensure(os.path.isabs(root) and os.path.normpath(root)==root and root!='/','root must be absolute and normalized')
 flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
 try:rootfd=os.open(root,flags)
 except OSError as e:raise Reject('cannot open root directory without following final symlink: '+str(e))
 seen=set();inodes=set()
 try:
  rs=os.fstat(rootfd);ensure(stat.S_ISDIR(rs.st_mode) and mode(rs)==rootmode,'root type or mode');device=rs.st_dev
  def visit(fd,prefix):
   before=os.fstat(fd);ensure(stat.S_ISDIR(before.st_mode) and before.st_dev==device,'directory type/device')
   names=sorted(os.listdir(fd));ensure(len(names)==len(set(names)),'duplicate directory name')
   for name in names:
    rel=prefix+name;entry=expected.get(rel);ensure(entry is not None,'unexpected path '+rel)
    try:s=os.stat(name,dir_fd=fd,follow_symlinks=False)
    except OSError as e:raise Reject('stat '+rel+': '+str(e))
    ensure(s.st_dev==device,'cross-device entry '+rel)
    ensure(not stat.S_ISLNK(s.st_mode),'symlink rejected '+rel)
    ensure(mode(s)==entry['mode'],'mode mismatch '+rel)
    if stat.S_ISDIR(s.st_mode):
     ensure(entry['type']=='directory','type mismatch '+rel)
     try:child=os.open(name,flags,dir_fd=fd)
     except OSError as e:raise Reject('directory open '+rel+': '+str(e))
     try:
      ensure(stable(os.fstat(child))==stable(s),'directory changed '+rel);seen.add(rel);visit(child,rel+'/');ensure(stable(os.fstat(child))==stable(s),'directory changed '+rel)
     finally:os.close(child)
    elif stat.S_ISREG(s.st_mode):
     ensure(entry['type']=='file' and s.st_nlink==1,'type or hardlink '+rel)
     inode=(s.st_dev,s.st_ino);ensure(inode not in inodes,'duplicate inode '+rel);inodes.add(inode)
     try:child=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
     except OSError as e:raise Reject('file open '+rel+': '+str(e))
     try:
      actual=os.fstat(child);ensure(stable(actual)==stable(s),'file changed before read '+rel);ensure(actual.st_size==entry['bytes'],'size mismatch '+rel)
      h=hashlib.sha256()
      while chunk:=os.read(child,1024*1024):h.update(chunk)
      ensure(stable(os.fstat(child))==stable(actual),'file changed during read '+rel)
      ensure(h.hexdigest()==entry['sha256'],'hash mismatch '+rel);seen.add(rel)
     finally:os.close(child)
    else:raise Reject('unsupported type '+rel)
    try:after=os.stat(name,dir_fd=fd,follow_symlinks=False)
    except OSError as e:raise Reject('re-stat '+rel+': '+str(e))
    ensure(stable(after)==stable(s),'entry changed '+rel)
   ensure(stable(os.fstat(fd))==stable(before),'directory changed during walk '+(prefix or '.'))
  visit(rootfd,'');ensure(seen==set(expected),'missing paths '+repr(sorted(set(expected)-seen)[:5]));ensure(stable(os.fstat(rootfd))==stable(rs),'root changed')
 finally:os.close(rootfd)
 return len(seen)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--manifest-sha256',required=True);ap.add_argument('--root',required=True);a=ap.parse_args()
 ensure(re.fullmatch('[0-9a-f]{64}',a.manifest_sha256),'manifest digest format')
 data=pathlib.Path(a.manifest).read_bytes();ensure(hashlib.sha256(data).hexdigest()==a.manifest_sha256,'manifest digest mismatch')
 rootmode,entries=index_manifest(json.loads(data,object_pairs_hook=reject_duplicate_json_keys));n=check(a.root,rootmode,entries)
 print(f'PASS {n} paths match supplied manifest SHA256 {a.manifest_sha256}; no symlinks, hardlinks or cross-device entries')
 print('External authentication of manifest digest, root identity, ownership, UID/GID, ACL, mount, aliases, containment and global quiescence remains required.')
if __name__=='__main__':
 try:main()
 except (Reject,OSError,ValueError,TypeError,json.JSONDecodeError) as e:print('REJECT:',e,file=sys.stderr);sys.exit(1)
