"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact six-file selective adoption, preserving originals. No compiler/configure/runtime.
SOURCE PROPOSAL ONLY until Root supplies real bindings and invokes it once.
"""
from pathlib import Path
import argparse,hashlib,json,os,re
D=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
WRITESET={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next114-debug32-perf3-coherent-source-1/root-selective-adoption-materialization-proposal-source-1/EXACT-SIX-FILE-WRITE-SET.NOT-AUTHORITY.json', 'bytes': 6188, 'sha256': 'bfefe73e210da60d242ccb6f9816214e15bfffdd296c83121d1451b7ca8e2e3f'}
REVIEW={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next114-debug32-perf3-coherent-source-1/outer-perf-line-restore-source-1/independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json', 'bytes': 8472, 'sha256': '941b98394b1600300165d97527059822f78860da5dba03eded90abf89940a801'}

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def fresh_json(p,x):
 with p.open('x') as f:f.write(json.dumps(x,indent=2)+'\n')
def adopt(bindings_path):
 b=read(bindings_path)
 assert b['author']=='/root' and b['decision']=='ADOPT_EXACT_NEXT114_GLOBAL32_PERF3_SIX_SOURCES_ONLY'
 assert b['maximum_invocations']==1 and b['root_attests_exclusive_six_file_integration'] is True and b['root_attests_no_live_source_reader_conflict'] is True
 assert b['write_set']==WRITESET and b['source_review']==REVIEW
 descriptor=read(auth(WRITESET));auth(REVIEW)
 ledger=read(auth(b['current_nonce_ledger']));free=read(auth(b['current_positive_free']))
 match=re.fullmatch(r'ROOT-CURRENT-NONCE-LEDGER(\d+)\.json',Path(b['current_nonce_ledger']['path']).name)
 assert match and int(match[1])>=41
 assert ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert ledger['latest_accepted_free_boundary']==b['current_positive_free'] and free['current_free'] is True and free['normal_owned_retirement'] is True
 output=D/'ROOT-ACTUAL-SELECTIVE-SOURCE-ADOPTION-1';assert not output.exists()
 checked=[]
 for row in descriptor['files']:
  target=ROOT/row['relative'];assert str(target)==row['canonical_path'] and target.parent.resolve()==target.parent and not target.is_symlink()
  source=auth(row['candidate']);data=source.read_bytes()
  if row['preimage'] is None:assert not os.path.lexists(target);old=None
  else:
   old=target.read_bytes();assert len(old)==row['preimage']['bytes'] and hashlib.sha256(old).hexdigest()==row['preimage']['sha256']
  checked.append((row,target,data,old))
 assert len(checked)==6
 output.mkdir(mode=0o700);(output/'preimages').mkdir(mode=0o700)
 for row,target,data,old in checked:
  if old is not None:
   prior=output/'preimages'/row['relative'];prior.parent.mkdir(mode=0o700,parents=True,exist_ok=True);prior.write_bytes(old)
 fresh_json(output/'STARTED.json',dict(scope=descriptor['scope'],author='/root',runtime_authority=None,Root_bindings=ref(bindings_path),write_set=WRITESET,current_nonce_ledger=b['current_nonce_ledger'],current_positive_free=b['current_positive_free']))
 results=[]
 for row,target,data,old in checked:
  flags=os.O_WRONLY|os.O_NOFOLLOW|os.O_CLOEXEC|(os.O_EXCL|os.O_CREAT if old is None else os.O_TRUNC)
  fd=os.open(target,flags,row['mode_if_new'])
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  actual=ref(target);assert actual['bytes']==row['candidate']['bytes'] and actual['sha256']==row['candidate']['sha256']
  results.append(dict(canonical=actual,private_source=row['candidate'],prior=row['preimage']))
 receipt=output/'ROOT-SOURCE-ADOPTION.json'
 fresh_json(receipt,dict(scope=descriptor['scope'],author='/root',status='ROOT_SOURCE_ADOPTED_NEXT114_GLOBAL32_PERF3_SIX_FILES_NOT_BUILT',runtime_authority=None,source_review=REVIEW,write_set=WRITESET,Root_bindings=ref(bindings_path),files=results,current_nonce_ledger=b['current_nonce_ledger'],current_positive_free=b['current_positive_free'],actual_compilers=0,actual_native_apps=0,whole_file_retirement=False))
 print(json.dumps(dict(status='ROOT_SELECTIVE_SIX_SOURCE_ADOPTION_ONLY',receipt=ref(receipt))))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root-bindings',required=True);a=p.parse_args();adopt(Path(a.root_bindings))
