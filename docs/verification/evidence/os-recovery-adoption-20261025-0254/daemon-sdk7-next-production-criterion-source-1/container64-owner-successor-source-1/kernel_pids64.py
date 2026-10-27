"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One finite kernel-controller proof before the existing mock compilers; no mutation.
"""
from pathlib import Path,PurePosixPath
import hashlib,os,stat

def need(ok,message):
 if not ok:raise ValueError(message)
def read(path,maximum):
 path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd);raw=b''
  while len(raw)<=maximum:
   block=os.read(fd,maximum+1-len(raw))
   if not block:break
   raw+=block
  after=os.fstat(fd);linked=path.lstat()
  need(len(raw)<=maximum and raw.endswith(b'\n'),'bounded complete kernel record')
  need((before.st_dev,before.st_ino,before.st_mode)==(after.st_dev,after.st_ino,after.st_mode)==(linked.st_dev,linked.st_ino,linked.st_mode),'kernel file identity changed')
  return raw,dict(path=str(path),device=before.st_dev,inode=before.st_ino,mode=before.st_mode,uid=before.st_uid,gid=before.st_gid,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 finally:os.close(fd)

def path_token(value):
 need(value.startswith('/') and '\\' not in value and '..' not in value.split('/') and '//' not in value,'canonical controller path')
 return PurePosixPath(value)

def locate(cgroup,mountinfo):
 legacy=[];unified=[]
 for line in cgroup.splitlines():
  fields=line.split(':',2);need(len(fields)==3,'complete cgroup membership')
  if fields[0]=='0' and fields[1]=='':unified.append(('cgroup2',path_token(fields[2])))
  elif 'pids' in fields[1].split(','):legacy.append(('cgroup',path_token(fields[2])))
 members=legacy if legacy else unified
 need(len(members)==1,'one effective pids controller membership required');kind,member=members[0];matches=[]
 for line in mountinfo.splitlines():
  sides=line.split(' - ');need(len(sides)==2,'complete mountinfo record');left=sides[0].split();right=sides[1].split();need(len(left)>=6 and len(right)>=3,'complete mount fields')
  if right[0]!=kind or (kind=='cgroup' and 'pids' not in right[2].split(',')):continue
  root=path_token(left[3]);target=path_token(left[4])
  try:relative=member.relative_to(root)
  except ValueError:continue
  matches.append((str(target/relative),dict(raw=line,fstype=kind,root=str(root),mountpoint=str(target),membership=str(member))))
 need(len(matches)==1,'one matching pids controller mount required');return matches[0]

def validate_proof(proof):
 need(proof.get('schema')=='mckernel.daemon-mock.kernel-pids64.v1' and proof.get('maximum_raw')=='64\n','actual kernel pids.max64 required')
 current=proof.get('current_raw');need(isinstance(current,str) and current.endswith('\n') and current.strip().isdecimal() and 1<=int(current)<=64,'actual bounded current tasks required')
 path,mount=locate(proof['proc_self_cgroup'],proof['proc_self_mountinfo']);need(path==proof['controller_directory'] and mount==proof['selected_mount'],'actual membership/controller binding')
 need(proof['maximum_identity']['path']==path+'/pids.max' and proof['current_identity']['path']==path+'/pids.current','exact controller file identities')
 need(proof['maximum_identity']['sha256']==hashlib.sha256(proof['maximum_raw'].encode()).hexdigest() and proof['current_identity']['sha256']==hashlib.sha256(current.encode()).hexdigest(),'kernel raw hashes differ')
 return proof

def observe():
 cgroup,_=read('/proc/self/cgroup',65536);mountinfo,_=read('/proc/self/mountinfo',2**20);directory,mount=locate(cgroup.decode('ascii'),mountinfo.decode('ascii'))
 maximum,mi=read(directory+'/pids.max',128);current,ci=read(directory+'/pids.current',128)
 after,_=read('/proc/self/cgroup',65536);need(after==cgroup,'controller membership moved during proof')
 need(Path(directory).resolve(strict=True)==Path(directory),'controller directory symlink');s=Path(directory).stat();need(stat.S_ISDIR(s.st_mode),'controller directory required')
 proof=dict(schema='mckernel.daemon-mock.kernel-pids64.v1',pid=os.getpid(),proc_self_cgroup=cgroup.decode('ascii'),proc_self_mountinfo=mountinfo.decode('ascii'),controller_directory=directory,controller_identity=dict(device=s.st_dev,inode=s.st_ino),selected_mount=mount,maximum_raw=maximum.decode('ascii'),current_raw=current.decode('ascii'),maximum_identity=mi,current_identity=ci)
 return validate_proof(proof)
