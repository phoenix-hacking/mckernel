"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One fixed 157-file Rust source observation; no source/nightly tree rehash or walk.
"""
import hashlib,json,os,stat,sys,traceback
from pathlib import Path,PurePosixPath
D=Path(__file__).resolve().parent;OUT=D/'receipt-run';B=D.parent.parent
MAP=D.parent/'SDK13-DATA32-SOURCE-MAP.PROPOSED.json';PROFILE=B/'sdk21-nonheld13-data32-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json';ADM=B/'f06-debug-constants-align32-host-1/ADMISSION.ACTUAL.json'
EXPECTED={MAP:'4172db42e65b1e30ccfbb86a86c0df1746eb9605ee3497e5a968db0fe16cdd1e',PROFILE:'e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3',ADM:'17553d05dc5df02be0d33489a10b736f6e5ea8b1e2131d749de720167e8aa349'}
def load(p):
 b=p.read_bytes()
 if hashlib.sha256(b).hexdigest()!=EXPECTED[p]:raise ValueError('bound input changed: '+str(p))
 return json.loads(b)
def ident(s):return {'device':s.st_dev,'inode':s.st_ino,'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'nlink':s.st_nlink,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
def save(name, obj):
 with (OUT/name).open('x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 state={'scope':__doc__.splitlines()[0],'status':'FAIL','files':0,'file_bytes':0,'first_failure':None,'source6153_rehashed':False,'nightly_rehashed':False};current=None;progress=None
 try:
  m=load(MAP);p=load(PROFILE);a=load(ADM); tree=m['trees']['/src/kernel/rust']; root=Path(tree['root'])
  mounts=[x for x in p['readonly_shared_inputs'] if x['container']=='/src/kernel/rust']
  if len(mounts)!=1 or mounts[0]['host']!=str(root):raise ValueError('profile root mismatch')
  rows=[x for x in tree['entries'] if x['kind']=='file']; expected={x['relative']:x for x in rows}
  if len(rows)!=157 or len(expected)!=157 or any(x['kind'] not in ('file','dir') for x in tree['entries']):raise ValueError('map cardinality or kind')
  closure={}
  for row in a['source_closure']:
   try:rel=Path(row['path']).relative_to(root).as_posix()
   except ValueError:continue
   if rel in closure:raise ValueError('duplicate admitted path')
   closure[rel]={'relative':rel,'kind':'file','bytes':row['bytes'],'sha256':row['sha256']}
  if closure!=expected:raise ValueError('map and admitted closure differ')
  rb=os.lstat(root)
  if not stat.S_ISDIR(rb.st_mode):raise ValueError('Rust root is not a directory')
  records=[];progress=(OUT/'progress.jsonl').open('x')
  for rel in sorted(expected):
   current=str(root/rel);rp=PurePosixPath(rel)
   if not rel or rp.is_absolute() or str(rp)!=rel or '..' in rp.parts:raise ValueError('invalid source-relative path')
   before=os.lstat(current);fd=os.open(current,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
   try:
    first=os.fstat(fd)
    if not stat.S_ISREG(first.st_mode) or ident(first)!=ident(before):raise ValueError('identity before read differs')
    h=hashlib.sha256();count=0
    while True:
     chunk=os.read(fd,1048576)
     if not chunk:break
     h.update(chunk);count+=len(chunk)
    after=os.fstat(fd); named=os.lstat(current)
    if ident(first)!=ident(after) or ident(first)!=ident(named):raise ValueError('identity changed during read')
    if count!=expected[rel]['bytes'] or h.hexdigest()!=expected[rel]['sha256']:raise ValueError('bytes or SHA256 differ from admitted closure')
    record={'kind':'file','physical':current,'path':current,'target':'/src/kernel/rust/'+rel,'bytes':count,'sha256':h.hexdigest(),'identity':ident(first)}
   finally:os.close(fd)
   records.append(record);state['files']+=1;state['file_bytes']+=count;progress.write(json.dumps(record,sort_keys=True)+'\n');progress.flush()
  if ident(rb)!=ident(os.lstat(root)):raise ValueError('Rust root changed during read')
  progress.flush();os.fsync(progress.fileno());progress.close();progress=None
  receipt={'schema':'mckernel.sdk13.data32.rust157-joint-observation.v1','root':str(root),'root_identity':ident(rb),'entries':records}
  save('RUST157-JOINT-RECEIPT.ACTUAL.json',receipt)
  state.update(status='PASS_FIXED_RUST157_BYTE_IDENTITY_OBSERVATION',root=str(root),root_identity=ident(rb),bindings={str(k):v for k,v in EXPECTED.items()},scope_limits='No directory enumeration, lease, quiescence, independent review, SDK or native acceptance.')
 except BaseException as exc:
  state['first_failure']={'path':current,'type':type(exc).__name__,'errno':getattr(exc,'errno',None),'error':str(exc),'traceback':traceback.format_exc()}
  if progress is not None:
   try:progress.flush();os.fsync(progress.fileno());progress.close()
   except OSError as e:state['progress_close_error']=repr(e)
 save('worker-result.json',state)
 return 0 if state['status']=='PASS_FIXED_RUST157_BYTE_IDENTITY_OBSERVATION' else 1
if __name__=='__main__':sys.exit(main())
