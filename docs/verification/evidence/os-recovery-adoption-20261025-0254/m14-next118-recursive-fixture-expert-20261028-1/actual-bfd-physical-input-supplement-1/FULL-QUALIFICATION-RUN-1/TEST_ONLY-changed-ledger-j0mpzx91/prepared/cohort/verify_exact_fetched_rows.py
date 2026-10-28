"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root existing fetched-blob publication method, exact prewritten finite row list.
Runs Git READS only after actual Root commit/push/fetch; before resource clocks.
"""
from pathlib import Path
import argparse,json,hashlib,re,subprocess
root=Path('/home/holden/mckernel')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared-rows',required=True);p.add_argument('--fetched-commit',required=True);a=p.parse_args();assert re.fullmatch('[0-9a-f]{40}',a.fetched_commit)
 plan=json.loads(Path(a.prepared_rows).read_bytes());A=Path(a.prepared_rows).parent
 for row in plan['rows']:
  token=a.fetched_commit+':'+row['fetched_equivalent_path']
  child=subprocess.run(['/usr/bin/git','cat-file','blob',token],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
  assert child.returncode==0 and not child.stderr,(token,child.stderr)
  assert len(child.stdout)==row['actual']['bytes'] and hashlib.sha256(child.stdout).hexdigest()==row['actual']['sha256'],token
 value=dict(scope=plan['scope'],status='PASS_FETCHED_CURRENT118_F03SEVEN_SHM_STATIC_SOURCE_AND_BOUNDARY_CONTRACT',runtime_authority=None,commit=a.fetched_commit,rows=plan['rows'],retained_eight_objects='Exactaccepted114readonlyrefs; no newGitblobs/rebuild',unchanged_accepted_SDK=True,passed_compiler_prefix_replayed=False,publication_scope='Exact121Rust cachedrefs +8postimages/neworigin +reviewedA4finite/currentboundaryhelpers andactualRootstaticmetadata; all fetchedblobs. No source-export traversal replay or retainedobjectrebuild.')
 f=A/'ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json'
 with f.open('x') as o:json.dump(value,o,indent=2);o.write('\n')
 print(json.dumps(dict(status=value['status'],reference=ref(f),rows=len(plan['rows']))))
if __name__=='__main__':main()
