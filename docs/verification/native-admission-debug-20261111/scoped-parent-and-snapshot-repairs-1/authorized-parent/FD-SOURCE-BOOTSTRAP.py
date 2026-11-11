import hashlib,os,stat,sys
p,h=sys.argv[1:];f=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
try:
 b=os.fstat(f);assert stat.S_ISREG(b.st_mode) and b.st_nlink==1 and b.st_size<=65536
 r=b''
 while len(r)<b.st_size:
  x=os.read(f,min(65536,b.st_size-len(r)));assert x;r+=x
 a=os.fstat(f);assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_mode)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_mode)
 assert hashlib.sha256(r).hexdigest()==h
finally:os.close(f)
sys.argv=[p];exec(compile(r,p,'exec'),{'__name__':'__main__','__file__':p,'__source_sha256__':h})
