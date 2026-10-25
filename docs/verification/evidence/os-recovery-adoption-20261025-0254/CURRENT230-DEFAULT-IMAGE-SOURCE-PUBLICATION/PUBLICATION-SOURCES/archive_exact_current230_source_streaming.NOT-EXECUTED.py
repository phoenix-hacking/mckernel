#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing finite source-retention operation, streamed into bounded deterministic
shards. No compiler, owner import, query, root, Docker, guest or Git write.
"""
from pathlib import Path
import gzip,hashlib,json,math,os,stat,tarfile,time
D=Path(__file__).parent
PLAN=D/'FULL-SOURCE-AND-METADATA.PUBLICATION-MEMBERS.NOT-EXECUTED.json'
PLAN_SHA='86a3ed1638d5067d4f587638f10a5d85f405ff7eaf227b07c9aea4c79204e9e5'
FIELDS=('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(c,m):
 if not c:raise RuntimeError(m)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def ref(p):return dict(path=str(p),sha256=digest(p),bytes=p.stat().st_size)
def identity(p):
 s=p.lstat();return dict(path=str(p),dev=s.st_dev,inode=s.st_ino,file_type=stat.S_IFMT(s.st_mode),mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
class StableReader:
 def __init__(self,row):
  self.row=row;self.path=Path(row['path']);need(self.path.resolve()==self.path,'exact regular canonical input path')
  self.fd=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK);self.before=os.fstat(self.fd)
  need(stat.S_ISREG(self.before.st_mode) and self.before.st_nlink==1 and self.before.st_size==row['bytes'],'exact stable regular source extent')
  need('mode' not in row or stat.S_IMODE(self.before.st_mode)==row['mode'],'exact selected regular source mode')
  self.total=0;self.h=hashlib.sha256()
 def read(self,n=-1):
  need(n>=0,'bounded streaming reads only');raw=os.read(self.fd,n);self.total+=len(raw);self.h.update(raw);need(self.total<=self.row['bytes'],'source grew');return raw
 def finish(self):
  after=os.fstat(self.fd);named=self.path.lstat()
  need(all(getattr(self.before,k)==getattr(after,k)==getattr(named,k) for k in FIELDS),'stable FD and named input identity')
  need(self.total==self.row['bytes'] and self.h.hexdigest()==self.row['sha256'],'exact complete input bytes')
 def close(self):os.close(self.fd)
def info(row):
 t=tarfile.TarInfo(row['name']);t.mode=row['mode'];t.uid=t.gid=t.mtime=0
 if row['kind']=='symlink':t.type=tarfile.SYMTYPE;t.linkname=row['target'];t.size=0
 elif row['kind']=='directory':t.type=tarfile.DIRTYPE;t.size=0
 else:t.size=row['bytes']
 return t
def output(path):
 return os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb')
def check_output(path):
 row=ref(path);need(row['bytes']<32<<20,'per-file F32 output cap');return row
def write_json(path,value):
 raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode();need(len(raw)<32<<20,'bounded receipt')
 with output(path) as f:f.write(raw);f.flush();os.fsync(f.fileno())
 return ref(path)
def main():
 begin=time.monotonic();need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6},'ordinary root-granted CPU6 slot only')
 need(digest(PLAN)==PLAN_SHA,'exact finite publication plan');p=json.loads(PLAN.read_bytes());out=Path(p['output_root']);source=Path(p['source_root'])
 need(identity(source)==p['source_identity'],'actual copied source root identity')
 need(not os.path.lexists(out),'fresh publication output root')
 need(p['source_entries']==6153 and p['source_bytes']==105658344 and len(p['source_parts'])==7 and len(p['metadata'])==34,'reviewed finite publication vector')
 need(p['raw_part_cap']==16<<20 and p['per_output_file_cap']==32<<20 and p['gzip_compresslevel']==6,'fixed bounded codec profile')
 host=os.statvfs(D);scratch=os.statvfs('/home/holden/mckernel-work/scratch')
 need(host.f_bavail*host.f_frsize>=16*2**30+p['total_raw_publication_bytes']+(16<<20),'HOST floor plus complete worst-case publication and capture')
 need(scratch.f_bavail*scratch.f_frsize>=14091616256,'existing greater scratch floor; readonly scratch')
 out.mkdir(mode=0o700);records=[]
 for part in p['source_parts']:
  target=out/part['name'];need(part['tar_raw_bytes']<=16<<20,'fixed raw tar shard cap')
  with output(target) as stream:
   with gzip.GzipFile(fileobj=stream,filename='',mode='wb',compresslevel=6,mtime=0) as g:
    with tarfile.open(fileobj=g,mode='w|',format=tarfile.GNU_FORMAT) as tar:
     for row in part['entries']:
      path=Path(row['path']);t=info(row)
      if row['kind']=='file':
       reader=StableReader(row)
       try:tar.addfile(t,reader);reader.finish()
       finally:reader.close()
      elif row['kind']=='symlink':
       before=path.lstat();targetlink=os.readlink(path);after=path.lstat()
       need(stat.S_ISLNK(before.st_mode) and all(getattr(before,k)==getattr(after,k) for k in FIELDS),'stable source symlink')
       need(targetlink==row['target']==Path(targetlink).name and hashlib.sha256(os.fsencode(targetlink)).hexdigest()==row['sha256'],'exact finite symlink bytes')
       tar.addfile(t)
      else:
       st=path.lstat();need(stat.S_ISDIR(st.st_mode) and not path.is_symlink() and not any(path.iterdir()),'exact empty separately mounted gitlink directory');tar.addfile(t)
   stream.flush();os.fsync(stream.fileno())
  record=check_output(target);record.update(kind='source_tar_gzip',member_count=len(part['entries']),tar_raw_bytes=part['tar_raw_bytes'])
  # Independent reopened decompression checks the exact planned member vector.
  with tarfile.open(target,'r:gz') as tar:
   members=tar.getmembers();need(len(members)==len(part['entries']),'exact archive member cardinality')
   for ti,row in zip(members,part['entries']):
    expected=info(row);need((ti.name,ti.mode,ti.uid,ti.gid,ti.mtime,ti.type,ti.size,ti.linkname)==(expected.name,expected.mode,0,0,0,expected.type,expected.size,expected.linkname),'exact archive header/type/owner/mode')
    if row['kind']=='file':
     h=hashlib.sha256();size=0
     with tar.extractfile(ti) as f:
      for raw in iter(lambda:f.read(1<<20),b''):h.update(raw);size+=len(raw)
     need(size==row['bytes'] and h.hexdigest()==row['sha256'],'reopened exact archive file bytes')
  records.append(record)
 for row in p['metadata']:
  reader=StableReader(row)
  try:
   for part in row['chunks']:
    target=out/part['name'];h=hashlib.sha256();size=0
    need(part['offset']==reader.total and part['bytes']<=16<<20,'finite exact metadata chunk extent')
    with output(target) as stream:
     with gzip.GzipFile(fileobj=stream,filename='',mode='wb',compresslevel=6,mtime=0) as g:
      while size<part['bytes']:
       raw=reader.read(min(1<<20,part['bytes']-size));need(raw,'metadata ended early');g.write(raw);h.update(raw);size+=len(raw)
     stream.flush();os.fsync(stream.fileno())
    need(size==part['bytes'] and h.hexdigest()==part['sha256'],'exact metadata raw chunk')
    record=check_output(target);record.update(kind='metadata_gzip_chunk',source=row['path'],offset=part['offset'],raw_bytes=part['bytes'],raw_sha256=part['sha256'])
    reopened=hashlib.sha256();count=0
    with gzip.open(target,'rb') as f:
     for raw in iter(lambda:f.read(1<<20),b''):reopened.update(raw);count+=len(raw)
    need(count==part['bytes'] and reopened.hexdigest()==part['sha256'],'reopened exact metadata chunk bytes');records.append(record)
   reader.finish()
  finally:reader.close()
 need(identity(source)==p['source_identity'],'source root stable through publication')
 need(len(records)==45 and len(list(out.iterdir()))==45,'exact finite output closure before receipt')
 result=dict(scope=SCOPE,status='PASS_EXACT_CURRENT230_FULL_SOURCE_AND_METADATA_RETENTION_ONLY',plan=ref(PLAN),source_root_identity=p['source_identity'],source_manifest=p['source_manifest'],full_owner_request=p['full_owner_request'],source_entries=6153,tracked_symlinks=49,empty_separately_mounted_gitlink_directories=3,source_bytes=105658344,outputs=records,output_files=45,seconds=time.monotonic()-begin,all_reopened_content_verified=True,all_per_file_outputs_below_F32=True,source_or_canonical_written=False,builds=0,containers=0,native_apps=0,publication_commit_or_fetch=None)
 receipt=write_json(out/'SOURCE-RETENTION.json',result);print(json.dumps(dict(status=result['status'],receipt=receipt,outputs=45,seconds=result['seconds']),sort_keys=True))
if __name__=='__main__':main()
