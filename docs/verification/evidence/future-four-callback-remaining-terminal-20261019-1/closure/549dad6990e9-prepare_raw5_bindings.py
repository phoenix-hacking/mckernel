"""Specialize accepted finite raw5 helpers; no observer/export/cleanup execution."""
from pathlib import Path
import ast,hashlib,json
T=Path(__file__).resolve().parent;B=Path('/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1/populated-source-preparation-1');OUT=T/'root-observation-four-leaf-observation-actual-1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def change(source,values):
 lines=source.splitlines(keepends=True)
 for n in reversed(ast.parse(source).body):
  if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:
   k=n.targets[0].id;v=values[k];lines[n.lineno-1:n.end_lineno]=[k+' = '+('Path('+repr(str(v))+')' if isinstance(v,Path) else repr(v))+'\n']
 return ''.join(lines)
def put(n,s):
 with (T/n).open('x') as f:f.write(s)
put('readback_observer.py',change((B/'readback_observer.py').read_text(),dict(OUTPUT=OUT,NONCE='four-leaf-observation-actual-1')))
put('export_raw_five.py',change((B/'export_raw_five.py').read_text(),dict(SUMMARY_SHA=sha(T/'readback_observer.py'),OUTPUT=OUT)))
s=change((B/'read_original_five_metadata.py').read_text(),dict(SUMMARY_SHA=sha(T/'readback_observer.py'),EXPECTED_HASHES=None));helper='''def load_expected_hashes(path,expected):
 p=Path(path);need(p.is_absolute() and p.resolve()==p,'exact hash-authority path required')
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<1048576,'bounded hash authority required');raw=os.read(fd,1048576);after=os.fstat(fd);named=p.lstat()
  need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in ['st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns']),'hash authority FD changed')
 finally:os.close(fd)
 need(digest(raw)==expected,'exact hash authority digest differs');value=json.loads(raw)
 need(isinstance(value,dict) and set(value)==set(NAMES) and all(isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h) for h in value.values()),'exactfive SHA256 scalars required')
 return value

''';s=s.replace('def main():',helper+'''def main():
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--expected-hashes',required=True);parser.add_argument('--expected-hashes-sha256',required=True);args=parser.parse_args()
 global EXPECTED_HASHES
 EXPECTED_HASHES=load_expected_hashes(args.expected_hashes,args.expected_hashes_sha256)''');put('read_original_five_metadata.py',s)
put('postjoin_readback.py',change((B/'postjoin_readback.py').read_text(),dict(ENGINE=T/'cleanup_fourleaf.py',ENGINE_SHA=sha(T/'cleanup_fourleaf.py'),OBSERVER=T/'observe_four_leaf_image_retirement.py',OBSERVER_SHA=sha(T/'observe_four_leaf_image_retirement.py'))).replace('len(actual)==58','len(actual)==42').replace('actual fifty-eight fd-stable','actual forty-two fd-stable'))
print('Prepared4 finite helper sources; numericraw5 cap32MiB; latehashes typedFD input')
