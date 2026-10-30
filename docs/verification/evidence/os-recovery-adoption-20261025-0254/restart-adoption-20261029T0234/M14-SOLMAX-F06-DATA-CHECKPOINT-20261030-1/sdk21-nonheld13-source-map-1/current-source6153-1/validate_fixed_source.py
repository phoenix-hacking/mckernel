#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One fixed retained-journal source-file pass. No enumeration, native or SDK action.
"""
import hashlib,json,os,stat,sys,traceback
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent; RESULTS=HERE/'results'
MAP=HERE.parent/'SDK13-SOURCE-MAP.PROPOSED.json'; POINT=HERE.parent/'POINT-IN-TIME-IDENTITIES.json'
JOURNAL=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialization-journal.jsonl')
MANIFEST=JOURNAL.parent.parent/'source-inputs.CURRENT290-QUALIFIED-IHK3114.json'

def identity(s): return {'device':s.st_dev,'inode':s.st_ino,'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'nlink':s.st_nlink,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
def digest(data):return hashlib.sha256(data).hexdigest()
def output(name,value):
 with (RESULTS/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def load(path,expected):
 b=path.read_bytes()
 if digest(b)!=expected:raise ValueError('input hash differs: '+str(path))
 return b

def main():
 state={'scope':__doc__.splitlines()[0],'status':'FAIL','files':0,'symlinks':0,'file_bytes':0,'first_failure':None,'nightly_rehashed':False}
 stream=None; current=None
 try:
  mbytes=load(MAP,'3ab7abb82522c42f00c301f2d246c4918ec85bc789c20d4fb48f56468ac46e07');mapping=json.loads(mbytes)
  jbytes=load(JOURNAL,'f4a3f06d337d64e35cc7fff8b9957b9429ad5d468aa1e7d5e92f603dd5f7709d')
  auth=json.loads(load(MANIFEST,'3a0653623cc1cdb7ebb0e217274ded31ea8fea5068140af4884c273b493b5018'))
  root=Path(mapping['trees']['/src']['root']); rootstat=os.lstat(root)
  if not stat.S_ISDIR(rootstat.st_mode):raise ValueError('source root is not a directory')
  indexed={r['relative']:r for r in mapping['trees']['/src']['entries'] if r['kind']!='dir'}
  if len(indexed)!=6153:raise ValueError('map file/symlink cardinality')
  rows=[json.loads(x) for x in jbytes.splitlines()]
  if len(rows)!=6153 or len({x['path'] for x in rows})!=6153:raise ValueError('journal cardinality/duplicate')
  stream=(RESULTS/'SOURCE6153-IDENTITIES.jsonl').open('x')
  for n,row in enumerate(rows,1):
   rel=row['path']; current=str(root/rel);r=PurePosixPath(rel)
   if r.is_absolute() or str(r)!=rel or '..' in r.parts:raise ValueError('invalid relative path')
   path=root/rel; before=os.lstat(path)
   if row['kind']=='file':
    expectation=auth['materialized_repository_files'].get(rel) or auth['retained_ihk_git_metadata'].get(rel,{}).get('sha256')
    if expectation!=row['sha256'] or indexed.get(rel)!={'relative':rel,'kind':'file','bytes':row['size'],'sha256':row['sha256']}:raise ValueError('journal/manifest/map mismatch')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
     first=os.fstat(fd)
     if not stat.S_ISREG(first.st_mode) or identity(first)!=identity(before):raise ValueError('file identity differs before read')
     h=hashlib.sha256(); count=0
     while True:
      chunk=os.read(fd,1048576)
      if not chunk:break
      h.update(chunk);count+=len(chunk)
     after=os.fstat(fd);named=os.lstat(path)
     if identity(first)!=identity(after) or identity(first)!=identity(named):raise ValueError('file changed during read')
     if count!=row['size'] or h.hexdigest()!=row['sha256']:raise ValueError('content bytes/hash differ')
     record={'relative':rel,'physical':str(path),'container':'/src/'+rel,'kind':'file','bytes':count,'sha256':h.hexdigest(),'identity':identity(first)}
    finally:os.close(fd)
    state['files']+=1;state['file_bytes']+=count
   elif row['kind']=='symlink':
    if not stat.S_ISLNK(before.st_mode):raise ValueError('expected symlink')
    target=os.readlink(path)
    if target!=row['target'] or auth['materialized_symlinks'].get(rel,{}).get('target')!=target or indexed.get(rel)!={'relative':rel,'kind':'symlink','target':target}:raise ValueError('symlink target differs')
    resolved=path.resolve(strict=True)
    if resolved!=root and root not in resolved.parents:raise ValueError('symlink escapes root')
    if identity(before)!=identity(os.lstat(path)):raise ValueError('symlink changed')
    record={'relative':rel,'physical':str(path),'container':'/src/'+rel,'kind':'symlink','target':target,'identity':identity(before)};state['symlinks']+=1
   else:raise ValueError('unknown retained kind')
   stream.write(json.dumps(record,sort_keys=True)+'\n')
   if n%128==0:stream.flush();os.fsync(stream.fileno())
  if state['files']!=6104 or state['symlinks']!=49:raise ValueError('final cardinality mismatch')
  if identity(rootstat)!=identity(os.lstat(root)):raise ValueError('source root changed during pass')
  stream.flush();os.fsync(stream.fileno());stream.close();stream=None
  state['status']='PASS_FIXED_RETAINED_ENTRIES_ONLY'
  state['source_root']=str(root);state['source_root_identity']=identity(rootstat)
  state['map_sha256']=digest(mbytes);state['journal_sha256']=digest(jbytes)
  state['nightly_identity_ledger_sha256']=digest(POINT.read_bytes())
  state['limits']='Fixed entries only: no new path inventory, no validator, no SDK/native/custody conclusion.'
 except BaseException as exc:
  state['first_failure']={'path':current,'type':type(exc).__name__,'error':str(exc),'errno':getattr(exc,'errno',None),'traceback':traceback.format_exc()}
  if stream is not None:
   try:stream.flush();os.fsync(stream.fileno());stream.close()
   except OSError as close_error:state['stream_close_error']=repr(close_error)
 output('SOURCE-CURRENT-RESULT.json',state)
 return 0 if state['status']=='PASS_FIXED_RETAINED_ENTRIES_ONLY' else 1
if __name__=='__main__':sys.exit(main())
