"""Existing machine assembly with explicit native-failure predecessor semantics."""
from pathlib import Path
import hashlib,json,sys,time
SCOPE='M03_NATIVE_FAILURE_PHYSICAL_RETIREMENT_ONLY'
def predecessor_contract(ref):
 return dict(status='PASS_PHYSICAL_RETIREMENT_ONLY',scope=SCOPE,new_native_persistent_ownership_record_files=0,ref=ref)
def assemble(base,snapshot,now,snapshot_ref):
 assert snapshot['status']=='PASS_LIVE_PREEXECUTION_SNAPSHOT' and 0<=now-snapshot['time_epoch']<=60 and snapshot['parent_identity']==base['parent_identity']
 assert base['execution_count']==1 and base['runtime_release'] is False and base['fresh_live_preflight'] is None
 assert base['terminal_cleanup_and_common_shared_release']==predecessor_contract(base['exclusive_queue_predecessor'])
 assert snapshot['terminal_acceptance']==base['exclusive_queue_predecessor']
 result=dict(base);result.update(status='PASS_EXECUTION_RELEASE',runtime_release=True,fresh_live_preflight=snapshot_ref)
 return result
def main():
 basepath,baseSHA,snappath,outpath,snapSHA=sys.argv[1:]
 raw=Path(basepath).read_bytes();assert hashlib.sha256(raw).hexdigest()==baseSHA;base=json.loads(raw)
 raw=Path(snappath).read_bytes();assert hashlib.sha256(raw).hexdigest()==snapSHA;snapshot=json.loads(raw)
 ref=dict(path=snappath,sha256=snapSHA,bytes=len(raw));result=assemble(base,snapshot,time.time(),ref)
 raw=(json.dumps(result,indent=2)+'\n').encode()
 with Path(outpath).open('xb') as output:output.write(raw)
 print(json.dumps(dict(path=outpath,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))),flush=True)
if __name__=='__main__':main()
