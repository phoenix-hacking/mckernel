"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import difflib,hashlib,json
D=Path(__file__).resolve().parent
P=Path('/home/holden/mckernel-work/host-preparation/scratch-growth-20261023-1/USER-AUTHORIZED-GROWTH-PROPOSAL.json')
p=json.loads(P.read_text());assert p['proposal']['new_bytes']==142*2**30 and not p['runtime_mutations_performed']
A=D/'long_transport.accounting-proposal.py';B=D/'long_transport.accounting-142GiB-proposal.py'
a=A.read_text();assert a.count('info.st_size == 110 * 2**30')==1
b=a.replace('info.st_size == 110 * 2**30','info.st_size == 142 * 2**30').replace('unchanged110GiB host sparse backing','exact142GiB host sparse backing')
B.write_text(b)
(D/'accounting-142GiB-proposal.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=A.name,tofile=B.name)))
def ref(q):
    r=q.read_bytes();return dict(path=str(q.resolve()),bytes=len(r),sha256=hashlib.sha256(r).hexdigest())
r=dict(scope=__doc__,status='PRIVATE_142GIB_SOURCE_SUCCESSOR_NOT_INSTALLED_NOT_RELEASED',authorization=ref(P),predecessor_110GiB=ref(A),successor_142GiB=ref(B),expected_bytes=142*2**30,pending_pins=['Parent-owned daemon/source successor must use this geometry together with its logging repair; do not install this earlier logging96MiB profile over a newer daemon profile.','New nine-file source cohort/install map must pin the final merged long_transport.py and owner after independent review.','Final LONG profile/release/source_sha256, source-copy/stage manifest and execution templates remain unbound; EXTERNAL_CAPTURE_BINDING remains null.','Only dispatcher may mutate scratch after independent operation review and fresh identity/capacity/quiescence checks.'],native_credit=0,runtime_mutations=0)
(D/'142GiB-SOURCE-SUCCESSOR.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
