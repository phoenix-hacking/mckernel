"""Exact finite original raw-five export; no cleanup, write, or observer replay."""
import argparse,hashlib,importlib.util,json,os,resource,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
SUMMARY=HERE/'readback_observer.py'
SUMMARY_SHA = 'eacc1578acc806f2163006eee1c7d7b98e37e6196a50e10ce8daba90d0806153'
OUTPUT = Path('/home/holden/mckernel-work/host-preparation/native-exec-delivery-transfer-rust-repair-20261021-1/launcher-error-propagation-1/target-build-preparation-1/postbuild-terminal-preparation-1/actual-current-binding-1/generated-source-1/root-observation-current-c9-launcher-observation-1')
NAMES=('observer-result.json','observation.json','cleanup-release-draft.json','new-object-metadata.json','ownership.json')
CAP=33554432
COMMAND=['/usr/bin/tar','--format=ustar','--no-recursion','-cf','-','-C',str(OUTPUT),'--']+list(NAMES)
def need(ok,why):
 if not ok:raise RuntimeError(why)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()+b'\n'
def validate_release(r):
 need(r.get('status')=='PASS_EXECUTION_RELEASE' and r.get('schema')=='mckernel.reset-image.raw-five-export-release.v1','raw-five export unreleased')
 need(r.get('author') and r.get('helper_sha256')==sha(Path(__file__).read_bytes()) and r.get('summary_sha256')==SUMMARY_SHA and r.get('output')==str(OUTPUT) and r.get('argv')==COMMAND,'exact helper/output/argv binding')
 need(r.get('names')==list(NAMES) and r.get('max_archive_bytes')==CAP and isinstance(r.get('file_sha256'),dict) and set(r['file_sha256'])==set(NAMES) and all(isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v) for v in r['file_sha256'].values()),'exact finite raw-five file authority')
 for key in ('observer_status','summary_status'):
  ref=r.get(key);need(isinstance(ref,dict) and set(ref)=={'path','sha256'},'positive exact prior direct join status required')
  path=Path(ref['path']);need(path.stat().st_size<=1048576,'bounded direct join status required');raw=path.read_bytes();need(sha(raw)==ref['sha256'],'direct join status hash differs');status=json.loads(raw)
  need(status.get('returncode')==0 and status.get('direct_child_joined') is True,'positive direct observer/summary join required')
 for role in ('source_review','execution_review'):
  review=r.get(role) or {};need(review.get('status')=='PASS' and review.get('reviewer') and review['reviewer']!=r['author'] and review.get('implementation_ownership') is False and review.get('helper_sha256')==r['helper_sha256'] and review.get('summary_sha256')==SUMMARY_SHA,'independent exact raw-five review')
  if role=='execution_review':need(review.get('reviewed_payload_sha256')==sha(canonical({k:v for k,v in r.items() if k!='execution_review'})),'exact reviewed export payload')
 return r

def main():
 args=argparse.ArgumentParser();args.add_argument('--release',required=True);args.add_argument('--release-sha256',required=True);a=args.parse_args()
 raw=Path(a.release).read_bytes();need(len(raw)<=1048576 and sha(raw)==a.release_sha256,'bounded exact release');r=validate_release(json.loads(raw))
 need(os.getuid()==os.geteuid()==0,'released root export required');resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(CAP,CAP))
 need(sha(SUMMARY.read_bytes())==SUMMARY_SHA,'summary source changed')
 spec=importlib.util.spec_from_file_location('finite_summary',SUMMARY);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 before=m.read_all();need({n:sha(before[n][0]) for n in NAMES}==r['file_sha256'],'original five file hashes changed');m.summarize(before)
 need(sum(len(before[n][0])+1024 for n in NAMES)+10240<=CAP,'finite archive bound')
 cp=subprocess.run(COMMAND,stdin=subprocess.DEVNULL,stdout=sys.stdout.buffer,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},timeout=30,check=False)
 need(cp.returncode==0 and not cp.stderr,'exact finite tar failed');after=m.read_all();need(before==after,'original five bytes changed during export')
if __name__=='__main__':main()
