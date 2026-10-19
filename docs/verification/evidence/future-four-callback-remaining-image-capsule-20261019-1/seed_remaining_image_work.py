"""One case: seed this failed nine-phase build into a fresh /work mapping.

No CLI. Called only after the existing owner's shared/common/lease acquisition.
The independent release must bind the complete manifest and this source hash.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,os,stat
SOURCE=Path('/home/holden/mckernel-work/host-preparation/future-four-callback-compiler-preparation-20261019-1/owner-work')
REQUEST_SHA='e9497da4204aed95708bb0f2ceb062a88c45517c13e3c69e65510fb59334cec0'
def metadata(st):
 return dict(device=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=stat.S_IMODE(st.st_mode),file_type=stat.S_IFMT(st.st_mode),size=st.st_size,mtime_ns=st.st_mtime_ns,nlink=st.st_nlink)
def relative(raw):
 p=PurePosixPath(raw)
 if str(p)!=raw or not raw or p.is_absolute() or any(x in ('','..','.') for x in p.parts):raise RuntimeError('confined seed relative path required')
 if p.parts[0] not in ('output','evidence'):raise RuntimeError('only completed build/evidence may seed')
 return p

def seed_remaining_image_work(work,manifest_path,manifest_sha,proof_path,proof_sha):
 raw=Path(manifest_path).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=manifest_sha:raise RuntimeError('exact full seed manifest required')
 m=json.loads(raw);work=Path(work)
 if m['schema']!='mckernel.future-four-callback-nine-phase-seed.v1' or m['request_sha256']!=REQUEST_SHA or m['source_root']!=str(SOURCE):raise RuntimeError('different seed operation')
 if metadata(SOURCE.stat())!=m['source_root_metadata']:raise RuntimeError('source directory identity differs')
 if work.is_symlink() or not work.is_dir() or any(work.iterdir()):raise RuntimeError('fresh empty work required before seed')
 if work==SOURCE or SOURCE in work.parents or work in SOURCE.parents:raise RuntimeError('seed roots overlap')
 rows=m['entries'];by={str(relative(r['relative'])):r for r in rows}
 if len(by)!=len(rows):raise RuntimeError('duplicate seed entry')
 # No unknown entries. A changed inventory refuses before destination creation.
 actual={}
 for root,dirs,files in os.walk(SOURCE,followlinks=False):
  for name in dirs+files:
   p=Path(root)/name;rel=str(p.relative_to(SOURCE))
   if rel.split('/')[0] not in ('output','evidence'):raise RuntimeError('unknown source work entry')
   actual[rel]=metadata(p.lstat())
 if set(actual)!=set(by) or any(actual[r]!=by[r]['metadata'] for r in by):raise RuntimeError('complete source preimage differs')
 proof_bytes=Path(proof_path).read_bytes()
 if hashlib.sha256(proof_bytes).hexdigest()!=proof_sha:raise RuntimeError('exact retained phase proof required')
 proof_snapshot=json.loads(proof_bytes)
 journal=os.open(work/'remaining-seed-journal.jsonl',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 def note(value):
  raw=(json.dumps(value,sort_keys=True)+'\n').encode();view=memoryview(raw)
  while view:
   count=os.write(journal,view)
   if count<=0:raise RuntimeError('partial seed journal write failed')
   view=view[count:]
  os.fsync(journal)
 note(dict(state='BEGIN',manifest_sha256=manifest_sha,retained_phase_sha256=proof_sha,source=str(SOURCE)))
 rootfd=os.open(SOURCE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 copied=0
 try:
  for rel,row in sorted(by.items(),key=lambda x:(len(PurePosixPath(x[0]).parts),x[0])):
   rp=relative(rel);parts=rp.parts;dest=work/('prior-evidence' if parts[0]=='evidence' else 'output')
   for component in parts[1:]:dest=dest/component
   note(dict(state='ENTRY_STARTED',source_relative=rel,destination=str(dest)))
   fd=os.dup(rootfd)
   try:
    for component in parts[:-1]:
     nxt=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
    source=SOURCE/rel;st=os.stat(parts[-1],dir_fd=fd,follow_symlinks=False)
    if metadata(st)!=row['metadata']:raise RuntimeError('source entry changed')
    if stat.S_ISDIR(st.st_mode):
     dest.mkdir(mode=stat.S_IMODE(st.st_mode));os.chmod(dest,stat.S_IMODE(st.st_mode))
    elif stat.S_ISLNK(st.st_mode):
     target=os.readlink(parts[-1],dir_fd=fd)
     if target!=row['target']:raise RuntimeError('source symlink changed')
     os.symlink(target,dest);os.utime(dest,ns=(st.st_atime_ns,st.st_mtime_ns),follow_symlinks=False)
    elif stat.S_ISREG(st.st_mode):
     if st.st_nlink!=1:raise RuntimeError('unreviewed seed hardlink')
     sf=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd);df=os.open(dest,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,stat.S_IMODE(st.st_mode));h=hashlib.sha256();size=0
     try:
      if metadata(os.fstat(sf))!=row['metadata']:raise RuntimeError('opened source identity differs')
      while True:
       chunk=os.read(sf,1024*1024)
       if not chunk:break
       size+=len(chunk)
       if size>row['metadata']['size']:raise RuntimeError('seed source exceeds declared size before write')
       h.update(chunk);view=memoryview(chunk)
       while view:
        n=os.write(df,view)
        if n<=0:raise RuntimeError('seed short write')
        view=view[n:]
      if h.hexdigest()!=row['sha256'] or size!=st.st_size or metadata(os.fstat(sf))!=row['metadata']:raise RuntimeError('seed source bytes changed')
      os.fchmod(df,stat.S_IMODE(st.st_mode));os.utime(df,ns=(st.st_atime_ns,st.st_mtime_ns));os.fsync(df)
      dstmeta=os.fstat(df)
      if (dstmeta.st_uid,dstmeta.st_gid,stat.S_IMODE(dstmeta.st_mode),dstmeta.st_size,dstmeta.st_mtime_ns,dstmeta.st_nlink)!=(st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode),st.st_size,st.st_mtime_ns,1):raise RuntimeError('destination metadata differs')
      os.lseek(df,0,os.SEEK_SET);dh=hashlib.sha256()
      while True:
       part=os.read(df,1024*1024)
       if not part:break
       dh.update(part)
      if dh.hexdigest()!=row['sha256'] or metadata(os.fstat(df))!=metadata(dstmeta):raise RuntimeError('held destination bytes/identity differ')
     finally:os.close(sf);os.close(df)
     copied+=1
    else:raise RuntimeError('unsupported seed special entry')
   finally:os.close(fd)
   note(dict(state='ENTRY_COMMITTED',source_relative=rel,destination=str(dest)))
  # Directory timestamps must follow children, keeping CMake incremental inputs.
  for rel,row in sorted(by.items(),key=lambda x:len(PurePosixPath(x[0]).parts),reverse=True):
   st=row['metadata'];parts=PurePosixPath(rel).parts;dest=work/('prior-evidence' if parts[0]=='evidence' else 'output')/Path(*parts[1:])
   if st['file_type']==stat.S_IFDIR:os.utime(dest,ns=(st['mtime_ns'],st['mtime_ns']),follow_symlinks=False)
  after={}
  for root,dirs,files in os.walk(SOURCE,followlinks=False):
   for name in dirs+files:
    p=Path(root)/name;after[str(p.relative_to(SOURCE))]=metadata(p.lstat())
  if after!=actual:raise RuntimeError('source full preimage changed during seed')
  adopted=proof_snapshot
  adopted['origin_proof_sha256']=proof_sha
  adopted['seed_manifest_sha256']=manifest_sha
  adopted['source_root']='/src'
  adopted['output_root']='/work/output'
  adopted['build_root']='/work/output/build'
  def directory_identity(path):
   st=path.stat();return dict(device=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=stat.S_IMODE(st.st_mode))
  adopted['output_identity']=directory_identity(work/'output');adopted['build_identity']=directory_identity(work/'output/build')
  def mapped(raw):
   rp=Path(raw).relative_to(SOURCE);parts=rp.parts
   return str(Path('/work')/('prior-evidence' if parts[0]=='evidence' else 'output')/Path(*parts[1:]))
  for row in adopted['retained_files']:row['path']=mapped(row['path'])
  adopted['failure_receipt']['path']=mapped(adopted['failure_receipt']['path'])
  proofbytes=(json.dumps(adopted,sort_keys=True,indent=2)+'\n').encode();proofdest=work/'remaining-phase-proof.json'
  with proofdest.open('xb') as out:out.write(proofbytes);out.flush();os.fsync(out.fileno())
  note(dict(state='COMPLETE',regular_files=copied,adopted_proof_sha256=hashlib.sha256(proofbytes).hexdigest()))
  return dict(status='SEEDED_EXACT_RETAINED_NINE_PHASES',manifest_sha256=manifest_sha,origin_proof_sha256=proof_sha,proof_sha256=hashlib.sha256(proofbytes).hexdigest(),regular_files=copied,original_work_unchanged=True,container_build='/work/output/build',output_identity=adopted['output_identity'],build_identity=adopted['build_identity'])
 finally:
  os.close(rootfd);os.fsync(journal);os.close(journal)
