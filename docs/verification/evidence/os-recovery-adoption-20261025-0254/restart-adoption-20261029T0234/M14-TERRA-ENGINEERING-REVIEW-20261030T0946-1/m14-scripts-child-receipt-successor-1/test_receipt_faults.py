#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,importlib.util,json,os,pathlib,tempfile
O=pathlib.Path(__file__).resolve().parent;sp=importlib.util.spec_from_file_location('scripts_child',O/'child.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
w=pathlib.Path(tempfile.mkdtemp(prefix='fault-fixtures-',dir=O));sha=lambda b:hashlib.sha256(b).hexdigest();records=[]
def setup(name):
 d=w/name;d.mkdir();src=d/'src';src.mkdir();src.chmod(0o751);f=src/'base';f.write_bytes(b'old');f.chmod(0o640);out=d/'out';i=d/'inputs';i.mkdir();rec=d/'receipts';rec.mkdir();add=[]
 for n in range(6):
  data=('v'+str(n)).encode();p=i/('candidate'+str(n));p.write_bytes(data);p.chmod(0o644);add.append({'path':'new'+str(n),'type':'file','mode':'0644','bytes':len(data),'sha256':sha(data),'source_candidate':str(p)})
 doc={'base_scripts_candidate':str(src),'base_root_mode':'0751','base_members':[{'path':'base','type':'file','mode':'0640','bytes':3,'sha256':sha(b'old')}],'additions':add};return src,out,rec,doc
for case in ('after_create','partial_write','directory_fsync'):
 src,out,rec,doc=setup(case);manifest=json.dumps(doc,sort_keys=True).encode();c.UNION_SHA=sha(manifest)
 packet={'source_root':str(src),'output_root':str(out),'manifest_sha256':c.UNION_SHA,'body_sha256':c.BODY_SHA,'verifier_sha256':c.VERIFIER_SHA};raw=json.dumps(packet,sort_keys=True).encode();c.FUTURE_DESCRIPTOR_SHA=sha(raw)
 orig_receipt=c._receipt;orig_write=os.write;orig_fsync=os.fsync
 def inject(dirfd,name,record):
  if name!='result.json':return orig_receipt(dirfd,name,record)
  seen=[False]
  def bad_write(fd,data):
   if case=='after_create':raise OSError('synthetic write failure after create')
   if case=='partial_write':
    if not seen[0]:seen[0]=True;return orig_write(fd,data[:max(1,len(data)//3)])
    raise OSError('synthetic write failure after partial write')
   return orig_write(fd,data)
  def bad_fsync(fd):
   if case=='directory_fsync' and fd==dirfd:raise OSError('synthetic directory fsync failure')
   return orig_fsync(fd)
  os.write=bad_write;os.fsync=bad_fsync
  try:return orig_receipt(dirfd,name,record)
  finally:os.write=orig_write;os.fsync=orig_fsync
 c._receipt=inject;fd=os.open(rec,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:result=c._execute(raw,manifest,fd)
 finally:os.close(fd);c._receipt=orig_receipt;os.write=orig_write;os.fsync=orig_fsync
 path=rec/'result.json';assert result['status']=='UNKNOWN_RETAIN_OUTPUT' and path.is_file() and out.exists();data=path.read_bytes();owner=c.owner_view_of_bare_receipt(data);assert owner['status']=='UNKNOWN_RETAIN_OUTPUT'
 if case=='after_create':assert data==b''
 if case=='partial_write':
  assert data
  try:json.loads(data)
  except (json.JSONDecodeError,UnicodeDecodeError):pass
  else:raise AssertionError('partial receipt unexpectedly valid')
 if case=='directory_fsync':assert json.loads(data)['status']=='SUCCESS_BODY_ONLY'
 records.append({'case':case,'logical':result,'result_bytes':len(data),'result_sha256':sha(data),'valid_looking_success':case=='directory_fsync','bare_receipt_owner_view':owner,'output_retained':out.exists()})
(w/'RESULTS.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS 3 actual result receipt fault phases; all UNKNOWN and outputs retained; fixtures at',w)
