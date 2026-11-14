"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,json,os,sys
D=Path(__file__).resolve().parent
publication_code="from pathlib import Path; import hashlib,os,sys; src=Path(sys.argv[1]); root=Path(sys.argv[2]); digest=sys.argv[3]; raw=src.read_bytes(); assert hashlib.sha256(raw).hexdigest()==digest; assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000; root.mkdir(mode=0o700); (root/'p').mkdir(mode=0o700); f=(root/'m.json').open('xb'); f.write(raw); f.flush(); os.fsync(f.fileno()); f.close(); os.chmod(root/'m.json',0o600); assert hashlib.sha256((root/'m.json').read_bytes()).hexdigest()==digest"
publication_args=['/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-readiness-runtime-failure-2/coherent-successor-preparation-1/actual-stage-successor-1/manifest.json', '/home/holden/mckernel-work/scratch/nm05h2a1', '1fb66e1f61d92723b7191ff1464a07df2d3b131f04081a8cd9ca3fc1fc0c3c2d']
original_argv=sys.argv[:]
try:
 sys.argv=[__file__,*publication_args];exec(compile(publication_code,'<accepted-exclusive-publication>','exec'),{})
finally:sys.argv=original_argv
host=Path('/home/holden/mckernel-work/native-runs/m05h2');assert host.parent.resolve(strict=True)==host.parent and not any(p.is_symlink()for p in(host.parent,*host.parent.parents));host.mkdir(mode=0o700);(host/'p').mkdir(mode=0o700)
def identity(p):
 s=p.lstat();return dict(path=str(p),dev=s.st_dev,inode=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid,size=s.st_size,blocks=s.st_blocks)
(D/'actual-metadata-identities.json').write_text(json.dumps([identity(p)for p in(Path(publication_args[1]),Path(publication_args[1])/'p',Path(publication_args[1])/'m.json',host,host/'p')],indent=2)+'\n')
exec(compile((D/'check_coherent_inner_binding.py').read_bytes(),str(D/'check_coherent_inner_binding.py'),'exec'),dict(__file__=str(D/'check_coherent_inner_binding.py'),__name__='__main__'))
