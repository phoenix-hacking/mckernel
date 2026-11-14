"""Functional OS/apps/Rust migration only; no security testing.
Additive source-only renderer; no observer/query/guard/runtime. Preserves original file.
"""
from pathlib import Path
import argparse,ast,hashlib
D=Path(__file__).resolve().parent
COMPARATOR={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/known-cid-mount-order-correction-source-1/known_cid_inspect_compare.py', 'bytes': 2056, 'sha256': 'fb2dbf184ee6c4c3bd861963b72918cda3c781e1bbd47c278b993ccecf6a02a1'}
OLD="  assert (q.returncode,q.stdout,q.stderr)==(expected['returncode'],expected['stdout'],expected['stderr'])"
NEW="  comparator=load(COMPARE_SOURCE,'exact_known_CID_mount_order_comparator');comparator.compare(expected,q.returncode,q.stdout,q.stderr)"
def main():
 a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--source-sha256',required=True);a.add_argument('--output',required=True);x=a.parse_args()
 p=Path(x.source);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==x.source_sha256
 q=Path(x.output);assert q.is_absolute() and q!=p and not q.exists()
 text=raw.decode();assert text.count(OLD)==1 and 'def load(' in text
 text=text.replace(OLD,NEW,1);at=text.index('def ref(');text=text[:at]+'COMPARE_SOURCE='+repr(COMPARATOR)+'\n'+text[at:];ast.parse(text)
 with q.open('x') as f:f.write(text)
 print(str(q),hashlib.sha256(q.read_bytes()).hexdigest(),q.stat().st_size)
if __name__=='__main__':main()
