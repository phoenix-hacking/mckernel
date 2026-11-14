import fcntl,hashlib,json,os,select,signal,struct,sys,time,types
EXPECTED='7a6ecfc875758a60dd3c6641b87a53cf9780af1a6473f9826d38b0b0509e76da'
if len(sys.argv)!=17:raise ValueError('exact waiting-installer argv required')
source_fd,ready_fd,go_fd,root_fd,package_fd,code_fd,lease_fd,closure_fd,controls_fd,capacity_fd,host_fd,owner_fd=map(int,sys.argv[1:13])
nonce,deadline,installer_path,boot_id=sys.argv[13:17];deadline=int(deadline)
os.lseek(source_fd,0,os.SEEK_SET);before=os.fstat(source_fd);raw=b''
while len(raw)<=2097152:
 part=os.read(source_fd,min(65536,2097153-len(raw)))
 if not part:break
 raw+=part
after=os.fstat(source_fd)
if ((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(raw)!=before.st_size or hashlib.sha256(raw).hexdigest()!=EXPECTED):raise ValueError('installer source changed')
mod=types.ModuleType('install_source_closure');mod.__file__=installer_path;mod._BOOTSTRAP_INSTALLER_HASH=EXPECTED;sys.modules[mod.__name__]=mod
exec(compile(raw,installer_path,'exec'),mod.__dict__)
fields=open('/proc/self/stat').read(65536).rsplit(')',1)[1].split()
actual_boot=open('/proc/sys/kernel/random/boot_id').read(128).strip()
if actual_boot!=boot_id:raise ValueError('boot identity changed')
ready={'pid':os.getpid(),'birth':fields[19],'parent_pid':os.getppid(),'pgrp':os.getpgrp(),'boot_id':actual_boot,'nonce':nonce}
msg=json.dumps(ready,sort_keys=True,separators=(',',':')).encode();frame=struct.pack('!I',len(msg))+msg
if len(frame)>4096 or os.write(ready_fd,frame)!=len(frame):raise OSError('READY short write')
poll=select.poll();poll.register(go_fd,select.POLLIN|select.POLLHUP|select.POLLERR);go=b''
while len(go)<65:
 now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
 if now>=deadline:raise TimeoutError('waiting installer GO expired')
 if not poll.poll(min(100,max(1,(deadline-now)//1000000))):continue
 part=os.read(go_fd,65-len(go))
 if not part:raise EOFError('GO lost')
 go+=part
if go[:1]!=b'G':raise ValueError('GO absent')
release_sha=go[1:].decode('ascii')
if not mod.hex64(release_sha):raise ValueError('GO digest')
rfd=os.open('INSTALL-RELEASE-'+nonce+'.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd)
release=mod.verify_release(rfd,release_sha);mod.verify_base_runtime(release['interpreter']);mod.verify_host_receipt(host_fd,release)
fcntl.flock(lease_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
if os.write(ready_fd,b'L')!=1:raise OSError('lease acknowledgement short write')
mod.install(rfd,release_sha,package_fd,root_fd,code_fd,lease_fd,closure_fd,controls_fd,capacity_fd,host_fd,owner_fd)
