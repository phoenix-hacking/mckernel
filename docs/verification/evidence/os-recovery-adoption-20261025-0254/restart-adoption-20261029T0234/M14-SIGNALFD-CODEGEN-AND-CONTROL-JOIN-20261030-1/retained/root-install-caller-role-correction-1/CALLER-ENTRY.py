import hashlib,os,stat,sys
PATH='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-caller-role-correction-1/prepare_and_exec.py'
EXPECTED='aca962cdc97cf710688424aaa922d02a472a52dec138ba43e65639dcead6a807'
fd=os.open(PATH,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
before=os.fstat(fd)
if not stat.S_ISREG(before.st_mode) or before.st_size>2097152:raise ValueError('caller source bounds')
parts=[];size=0
while size<=2097152:
 chunk=os.read(fd,min(65536,2097153-size))
 if not chunk:break
 parts.append(chunk);size+=len(chunk)
after=os.fstat(fd);raw=b''.join(parts)
if size!=before.st_size or size>2097152 or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or hashlib.sha256(raw).hexdigest()!=EXPECTED:raise ValueError('caller source changed')
sys.argv[0]=PATH
scope={'__name__':'__main__','__file__':PATH,'_VERIFIED_CALLER_SOURCE_FD':fd}
exec(compile(raw,PATH,'exec'),scope)
