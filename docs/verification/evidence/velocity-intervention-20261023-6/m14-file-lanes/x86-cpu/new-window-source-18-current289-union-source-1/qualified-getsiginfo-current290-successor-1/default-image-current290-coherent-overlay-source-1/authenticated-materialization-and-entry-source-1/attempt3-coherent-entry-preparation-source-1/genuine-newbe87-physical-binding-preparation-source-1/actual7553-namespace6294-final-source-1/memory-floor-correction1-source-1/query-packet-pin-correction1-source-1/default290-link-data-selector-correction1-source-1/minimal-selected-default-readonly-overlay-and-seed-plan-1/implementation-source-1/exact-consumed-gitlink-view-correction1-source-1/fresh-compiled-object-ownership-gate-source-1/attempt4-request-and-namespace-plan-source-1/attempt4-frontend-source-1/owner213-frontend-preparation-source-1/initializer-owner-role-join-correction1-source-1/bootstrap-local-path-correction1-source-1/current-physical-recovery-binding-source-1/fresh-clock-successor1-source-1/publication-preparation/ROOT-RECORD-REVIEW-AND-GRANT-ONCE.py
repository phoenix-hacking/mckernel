#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root records one independently supplied exact actual-payload review and grant.
Does not launch an owner, query, cleanup or extend a clock.
"""
import json, hashlib, time, os
from pathlib import Path
P=Path(__file__).resolve().parent.parent
cfg=json.loads((P/'FROZEN-CURRENT290-IMAGE-ENTRY-INPUTS.ATTEMPT4.READONLY-SEED.json').read_bytes())
root=P/'actual-entry-1'
ready=json.loads((root/'INDEPENDENT-EXECUTION-REVIEW-READY.json').read_bytes())
review=json.loads(__import__('sys').stdin.read())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def publish(p,v):
 b=(json.dumps(v,indent=2,sort_keys=True)+'\n').encode();fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 try:os.write(fd,b);os.fsync(fd)
 finally:os.close(fd)
assert review['decision']=='PASS_EXECUTION' and review['implementation_ownership'] is False and review['reviewer'] not in ('/root','',None)
assert review['caller_sha256']==ready['caller']['sha256'] and review['config_sha256']==ready['config']['sha256']
assert review['metadata_fill_sha256']==cfg['fill']['sha256'] and review['operation_scope']==cfg['operation_scope']
assert review['reviewed_release_payload_sha256']==ready['canonical_payload_sha256']
assert review['existing_cleanup_source']==ref(P/'native_rust_cutover_image_terminal_cleanup.CURRENT290.ATTEMPT4.READONLY-SEED.py')
assert 0<=time.time()-ready['five_end_epoch']<120 and time.time()<cfg['deadline_epoch']-30
holder=ready['holder'];fields=Path('/proc/%d/stat'%holder['pid']).read_text().rsplit(')',1)[1].split();assert fields[19]==str(holder['starttime'])
s=os.stat('/proc/%d/fd/%d'%(holder['pid'],holder['fd']));assert(s.st_dev,s.st_ino)==(27,4)
rows=[l.split()[1:] for l in Path('/proc/locks').read_text().splitlines() if l.split()[5]=='00:1b:4'];assert rows==[['FLOCK','ADVISORY','WRITE',str(holder['pid']),'00:1b:4','0','EOF']]
assert not Path('/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock').exists()
rp=root/'INDEPENDENT-ACTUAL-PAYLOAD-EXECUTION-REVIEW.json';publish(rp,review)
g=dict(author='/root',decision='GRANT_ONE_CURRENT290_IMAGE_OWNER',caller_sha256=ready['caller']['sha256'],payload=ready['payload'],owner_argv=cfg['commands']['owner_entry_unchanged']['argv'],holder=holder,actual_no_other_heavy=True,no_heavy_since_latest_physical=True,operation_scope=cfg['operation_scope'],independent_review=ref(rp),scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.')
publish(root/'ROOT-EXECUTION-GRANT.json',g)
print(json.dumps(dict(status='ROOT_EXACT_REVIEW_AND_ONE_GRANT_RECORDED',elapsed=time.time()-ready['five_end_epoch'],review=ref(rp))))
