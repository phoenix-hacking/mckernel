# Functional McKernel OS/apps and Rust/assembly migration ONLY; NO security testing.
# Exact metadata guard for the one existing udev publisher420/b281 and real control
# node; no process/service/package inventory, socket call, signal or SUT mutation.
# Rejected worker01a1c48d/turn01a1ce01 signal/frame/xstate task excluded.
import argparse,hashlib,json,os,pathlib,re,resource,stat,sys,time
HERE=pathlib.Path(__file__).resolve().parent

def shape(st):
 return tuple(getattr(st,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns'))

def metadata(st):
 return {'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid,'gid':st.st_gid,
  'mode':oct(stat.S_IMODE(st.st_mode)),'nlink':st.st_nlink,'bytes':st.st_size,
  'mtime_ns':str(st.st_mtime_ns),'ctime_ns':str(st.st_ctime_ns)}

def read_bounded(path,n):
 with open(path,'rb') as stream:raw=stream.read(n+1)
 assert len(raw)<=n
 return raw

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--expected-sha256',required=True);p.add_argument('--operation-nonce',required=True)
 p.add_argument('--phase',required=True,choices=('before','after'))
 a=p.parse_args()
 assert re.fullmatch('[0-9a-f]{64}',a.expected_sha256) and re.fullmatch('[0-9a-f]{64}',a.operation_nonce)
 assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==0
 assert os.sched_getaffinity(0)=={7} and sys.version_info[:2]==(3,8)
 resource.setrlimit(resource.RLIMIT_AS,(134217728,134217728))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(4194304,4194304))
 resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
 path=HERE/'EXPECTED-CONTEXT.json';st=path.lstat()
 assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and st.st_nlink==1 and stat.S_IMODE(st.st_mode)==0o600
 raw=read_bounded(str(path),131072)
 assert hashlib.sha256(raw).hexdigest()==a.expected_sha256 and shape(st)==shape(path.lstat())
 expect=json.loads(raw);target=expect['observed_tuple']
 assert expect['schema']=='mckernel.m15.f08.closed-static-genuine-context.v1'
 assert target['publisher_process']['pid']==420 and target['publisher_process']['birth']=='281'
 boot=read_bounded('/proc/sys/kernel/random/boot_id',128).decode().strip()
 proc=pathlib.Path('/proc/420')
 before=read_bounded(str(proc/'stat'),8192).decode().rsplit(') ',1)[1].split()
 assert before[19]==target['publisher_process']['birth']
 process={'pid':420,'birth':before[19],'PPid':int(before[1])}
 status={}
 for line in read_bounded(str(proc/'status'),32768).decode().splitlines():
  name,sep,value=line.partition(':')
  if sep and name in ('Uid','Gid'):status[name]=[int(x) for x in value.split()]
 assert status=={'Uid':[0,0,0,0],'Gid':[0,0,0,0]}, 'current publisher ordinary IDs changed'
 root=os.stat('/');service_root=os.stat(str(proc/'root'))
 root_value={'device':root.st_dev,'inode':root.st_ino}
 assert (service_root.st_dev,service_root.st_ino)==(root.st_dev,root.st_ino)
 exepath=os.readlink(str(proc/'exe'));fd=os.open(str(proc/'exe'),os.O_RDONLY|os.O_CLOEXEC|os.O_NONBLOCK)
 try:
  bs=os.fstat(fd);assert stat.S_ISREG(bs.st_mode) and bs.st_size==760392
  digest=hashlib.sha256();count=0
  while True:
   b=os.read(fd,1048576)
   if not b:break
   count+=len(b);assert count<=760392;digest.update(b)
  assert count==bs.st_size and shape(bs)==shape(os.fstat(fd))==shape(os.stat(str(proc/'exe')))
  exe=metadata(bs);exe.update(status='OBSERVED',sha256=digest.hexdigest())
 finally:os.close(fd)
 namespaces={}
 for name in ('mnt','net','user','pid'):
  path=proc/'ns'/name;ns=os.stat(str(path))
  namespaces[name]={'device':ns.st_dev,'inode':ns.st_ino,'link':os.readlink(str(path))}
 cs=os.lstat('/run/udev/control')
 assert stat.S_ISSOCK(cs.st_mode)
 control=metadata(cs);control.update(status='OBSERVED',path='/run/udev/control',kind='SOCKET')
 inside=os.lstat('/proc/420/root/run/udev/control')
 assert shape(inside)==shape(cs), 'service root control node differs'
 after=read_bounded(str(proc/'stat'),8192).decode().rsplit(') ',1)[1].split()
 assert before[19]==after[19] and int(after[1])==process['PPid']
 observed={'boot_id':boot,'publisher_process':process,'publisher_root':root_value,
  'publisher_exe_path':exepath,'publisher_executable':exe,'publisher_namespaces':namespaces,'publisher_uid_gid':status,'control_node':control}
 assert observed==target, 'current exact provider lifetime/input tuple differs'
 assert os.sched_getaffinity(0)=={7}
 assert pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().strip()==''
 proof={'schema':'mckernel.m15.f08.actual-selected-publisher-lifetime-guard.v1','phase':a.phase,
  'operation_nonce':a.operation_nonce,'expected_context_sha256':a.expected_sha256,
  'actor_source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
  'actor_uid':os.getuid(),'actor_gid':os.getgid(),'observed_utc_ns':time.time_ns(),'observed_mono_ns':time.monotonic_ns(),
  'observed':observed,'input_and_executable_FDs_closed':True,'direct_children_empty':True,
  'service_package_queries_or_socket_send_or_signal_or_namespace_change':False}
 sys.stdout.write(json.dumps(proof,sort_keys=True)+'\n');sys.stdout.flush()
 return 0

if __name__=='__main__':sys.exit(main())
