"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare exact source/profile/argv only; never execute root admission, guard or native.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
E=Path(__file__).resolve().parent
N=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1');P=N/'fork-v3-matched-process-successor-1/case-235/final-runtime-ready-1/root-live-admission-1';F=N/'zombie-sdk-native-successor-1';C=F/'case-235';A=C/'root-live-admission-zombie-1';A.mkdir(mode=0o700,exist_ok=False)
R=Path('/home/holden/mckernel');D=R/'docs/verification/evidence/native235-zombie-reaper-20261023-1';SDK=D/'sdk-build-release';ACCEPT=SDK/'INDEPENDENT-ACTUAL-SDK-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.json'
def load(p):return json.loads(p.read_text())
def ref(p):p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n')
assert ref(ACCEPT)['sha256']=='5df70b4414fe418e73b3e01650380ecf58d7a085642cce95b94c611a1a0d9189'
assert load(ACCEPT)['status']=='PASS'
oldsource=P/'read_only_native235_admission.py';assert ref(oldsource)['sha256']=='3dd230d35c41011e84b13cecef9ab303586c02ada9b0259fa50487d16d79b05b';old=oldsource.read_text();s='"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\nFresh read-only admission for the repaired host SDK tuple; no native authorization.\n"""\n'+old
s=s.replace('v3-native235-current-live-admission-20261023-1','zombie-sdk-native235-current-live-admission-20261023-1')
s=s.replace('8646cb69db21440ca31573ab1b3d0691','58b3c4c49a9143e1b32cd97ae38870d1').replace('/scratch/n235v1','/scratch/n235z1')
postflight=load(SDK/'actual-build/postflight-proof.json');cid=postflight['absence']['container_id'];assert postflight['all_clients_reaped']is True and postflight['container_absent']is True
s=s.replace("cid='6959890602bd9c84ba3741b4aa37fc9ea29cb24a86ac93637315b852169074af'",'cid='+repr(cid))
oldref="{'path': '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/INDEPENDENT-ACTUAL-SDK68-V3-ARTIFACT-AND-PHYSICAL-ACCEPTANCE-1.json', 'sha256': '6a6a47b9899e8de45ab650023419b5a1af0596fb34865241cae263e0b19cac2f', 'bytes': 2703}"
assert oldref in s;s=s.replace(oldref,repr(ref(ACCEPT)))
# Keep 110GiB/inode47468427/UUID/mutex27:4/PROC59ef/budgets/cgroup predicates exact.
ast.parse(s);source=A/'read_only_native235_admission.py';source.write_text(s);(E/'READONLY-ADMISSION-SOURCE-DELTA.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile=str(oldsource),tofile=str(source))))
op=load(P/'ROOT-EXACT-READONLY-ADMISSION-OPERATION-1.json');op.update(scope=__doc__.splitlines()[0],source=ref(source),base_source_sha256=ref(oldsource)['sha256'],changes='Exact new235nonce/shortroot + latest accepted9850SDK container/postjoin/artifact ref and functional-scope docstring only; accepted PROC59ef/110GiB/UUID/mutex27:4/capacity/cgroup/read-only bodies unchanged.',mutation=False);op['argv'][-1]=str(source);save(A/'ROOT-EXACT-READONLY-ADMISSION-OPERATION.json',op);save(E/'ROOT-EXACT-READONLY-ADMISSION-OPERATION.json',op)
print(json.dumps({'source':ref(source),'operation':ref(E/'ROOT-EXACT-READONLY-ADMISSION-OPERATION.json'),'argv':op['argv']},indent=2))
