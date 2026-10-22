"""Mechanical finalization only; Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import argparse,hashlib,json,os
A=Path(__file__).resolve().parent;E=A.parent;B=E/'bound-matched-image-terminal-source-2'
def sha(v):return hashlib.sha256(v).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(p,v):
 with Path(p).open('xb')as f:os.fchmod(f.fileno(),0o600);f.write(canonical(v))
def load(p):return json.loads(Path(p).read_bytes())
def templates():
 ops=load(E/'EXECUTOR-SIX-OPERATIONS.2.PENDING.json');release=E/'ROOT-CLEANUP-EXECUTION-RELEASE-2.json';old=str(B/'cleanup-execution-release.json');rows={}
 for role in ('cleanup','postjoin'):
  row=next(r for r in ops['ordered_operations']if r['role']==role);row['argv']=[str(release)if v==old else v for v in row['argv']];row['capture_directory']=str(A/('actual-'+role+'-capture-1'));row['source']=ref(B/('cleanup_pass_image.py'if role=='cleanup'else'postjoin_readback.py'))
  if role=='postjoin':row['argv'][-1]=str(A/'actual-cleanup-result.json')
  rows[role]=row
 row=ops['pre_cleanup_readonly_preflight'];row['argv']=[str(release)if v==old else v for v in row['argv']];row.update(role='readonly-preflight',cpu=7,stream_cap_bytes=33554432,capture_directory=str(A/'actual-fresh-preflight-capture-1'),source=ref(B/'check_actual_fresh_preflight.py'),profile=dict(cpu=7,jobs=1,as_soft_hard=[2<<30,2<<30],required_inherited_cpu_limits=[-1,-1],outer_wall_kill=None,outer_grace_kill=None,stream_fsize=33554432));rows['readonly-preflight']=row
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--review-sha256',required=True);a=p.parse_args();raw=Path(a.review).read_bytes();assert len(raw)<=1<<20 and sha(raw)==a.review_sha256;review=json.loads(raw)
 candidate=load(E/'ROOT-CLEANUP-EXECUTION-PAYLOAD-2.json');authority=load(A/'CANONICAL-CLEANUP-PAYLOAD.json');payload_sha=sha(canonical({k:v for k,v in candidate.items()if k!='execution_review'}));assert payload_sha==authority['canonical_without_execution_review_sha256']
 assert review['status']=='PASS' and review['reviewer']and review['reviewer']!=candidate['author'] and review['implementation_ownership']is False and review['reviewed_payload_sha256']==payload_sha
 candidate['execution_review']=dict(review,evidence_sha256=a.review_sha256);release=E/'ROOT-CLEANUP-EXECUTION-RELEASE-2.json';save(release,candidate);r=ref(release);operations={}
 for role,row in templates().items():
  row['argv']=[r['sha256']if v=='BIND_EXACT_CLEANUP_RELEASE_SHA256'else v for v in row['argv']];path=E/('ROOT-'+('FRESH-PREFLIGHT'if role=='readonly-preflight'else role.upper())+'-OPERATION-EXACT-2.json');save(path,row);op=ref(path);wrapper=A/'capture_preflight.REUSED.py'if role=='readonly-preflight'else B/'capture_critical_two.py';operations[role]=dict(operation=op,wrapper=ref(wrapper),argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(wrapper),'--operation',str(path),'--sha256',op['sha256']])
 save(A/'FINAL-RELEASE-AND-EXACT-OPERATIONS.json',dict(status='GENUINE_REVIEW_INSERTED_SAME_PAYLOAD_MECHANICALLY_FINALIZED',release=r,execution_review=dict(path=a.review,sha256=a.review_sha256),operations=operations,copy_after_cleanup_argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(A/'copy_joined_cleanup_result.py')],preflight_required_predicate='rootwhole0 + PASS_ACTUAL_FRESH_PREFLIGHT_READ_ONLY + predicate_passedtrue + mutation_startedfalse + transaction_mutex_openedfalse + transaction_closedtrue + no_cleanup_or_record_releasetrue',cleanup_requires='Run exactly once only after this same release produced actual positive fresh preflight; no other compiler/cleanup publishers.',postjoin_requires='Actual cleanup whole0/directjoin/groupabsent/streamsclosed, exact positive stdout copied via copy_joined_cleanup_result.py; then run once; independent physical acceptance still pending.'))
 print(json.dumps(load(A/'FINAL-RELEASE-AND-EXACT-OPERATIONS.json'),sort_keys=True))
if __name__=='__main__':main()
