from pathlib import Path
import hashlib,json,os,stat,types
P=Path(__file__).resolve().parent
blob=(P/'seed_remaining_image_work.py').read_bytes();m=types.ModuleType('exact_seed');exec(compile(blob,str(P/'seed_remaining_image_work.py'),'exec'),m.__dict__)
source=m.SOURCE;before=m.metadata(source.stat());rows=[];total=0
for base,dirs,files in os.walk(source,followlinks=False):
 for name in dirs+files:
  p=Path(base)/name;rel=str(p.relative_to(source));m.relative(rel);st=p.lstat();r={'relative':rel,'metadata':m.metadata(st)}
  if stat.S_ISREG(st.st_mode):
   if st.st_nlink!=1:raise RuntimeError('unreviewed hardlink')
   fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW);h=hashlib.sha256();count=0
   try:
    if m.metadata(os.fstat(fd))!=r['metadata']:raise RuntimeError('opened seed input changed')
    while True:
     chunk=os.read(fd,1024*1024)
     if not chunk:break
     h.update(chunk);count+=len(chunk)
    if count!=st.st_size or m.metadata(os.fstat(fd))!=r['metadata']:raise RuntimeError('seed input changed during read')
   finally:os.close(fd)
   r['sha256']=h.hexdigest();total+=count
  elif stat.S_ISLNK(st.st_mode):r['target']=os.readlink(p)
  elif not stat.S_ISDIR(st.st_mode):raise RuntimeError('unsupported seed specialentry')
  rows.append(r)
after={}
for base,dirs,files in os.walk(source,followlinks=False):
 for name in dirs+files:
  p=Path(base)/name;after[str(p.relative_to(source))]=m.metadata(p.lstat())
if after!={r['relative']:r['metadata'] for r in rows} or m.metadata(source.stat())!=before:raise RuntimeError('full seed inventory changed')
d={'schema':'mckernel.future-four-callback-nine-phase-seed.v1','request_sha256':m.REQUEST_SHA,'source_root':str(source),'source_root_metadata':before,'entries':sorted(rows,key=lambda x:x['relative']),'source_helper_sha256':hashlib.sha256(blob).hexdigest(),'ordinary_read_only_snapshot':True}
out=P/'actual-partial-tree-preimage.json'
with out.open('x') as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'status':'FROZEN_ACTUAL_PARTIAL_BUILD_PREIMAGE_ONLY','entries':len(rows),'regular_bytes':total,'manifest':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'actual_seed':False}))
