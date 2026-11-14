import errno,fcntl,json,os
from pathlib import Path
def need(v,m):
 if not v:raise RuntimeError(m)
def require_absence(paths):
 for path in paths:
  try:
   os.lstat(path)
  except FileNotFoundError as exc:
   if exc.errno != errno.ENOENT:
    raise
  else:
   raise RuntimeError('ownership path present: '+os.fspath(path))
need(os.geteuid()==0,'authenticated root read-only observation')
lock=Path('/run/lock/mckernel-development.lock').stat();need((lock.st_dev,lock.st_ino,lock.st_uid,lock.st_gid,lock.st_nlink)==(27,4,0,0,1),'permanent mutex')
key=f'{os.major(lock.st_dev):02x}:{os.minor(lock.st_dev):02x}:{lock.st_ino}'
locks=[l for l in Path('/proc/locks').read_text().splitlines() if key in l.split()];need(not locks,'permanent mutex currently held')
mutex_fd=os.open('/run/lock/mckernel-development.lock',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW);need((os.fstat(mutex_fd).st_dev,os.fstat(mutex_fd).st_ino)==(27,4),'stable27:4FD');fcntl.flock(mutex_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
paths=['/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json', '/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json', '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json'];require_absence(paths)
fcntl.flock(mutex_fd,fcntl.LOCK_UN);os.close(mutex_fd)
print(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_CURRENT_RETIRED_LONG_27_4_AND_8_PATH_ABSENCE',lock=[lock.st_dev,lock.st_ino],paths=paths),sort_keys=True))
