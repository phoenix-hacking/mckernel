# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Prepared for dispatcher /root. Worker runs only --check; canonical writes require
# the dispatcher's explicit --apply-root-canonical invocation. No Git/worklist/build.
from pathlib import Path
import hashlib,json,os,stat,sys
P=Path('/home/holden/mckernel-work/host-preparation/compute-process-next-body-cutover-20261023-1')
R=Path('/home/holden/mckernel'); E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1'
B=P/'SOURCE-BINDINGS.json'
ALLOWED=('kernel/process.c','kernel/rust/sched_helpers.rs','kernel/rust/tests/run_equivalence.sh')
PRE=('7203019d2ba8143f9240a03d11bc8c5cfcd495d89183aa7ab643c6159a6bd02d','449df570965855f992a0fe024fca7cd6527b20622b4b8e3b33af04900b02e923','fce1f3b9a5606eedb245996d4b88b5e93022ae56145729592c9d675ecb267386')
POST=('55872d7235a06364565ec7732b7a67c918ed7c006b1e55ababa88dbe42e2a93a','700a9e20349df5ae18ceea8c9195e38078a6bb05b81c79f7368fbdf6fc14abcc','5df92eff793c7ff0358567340a35b3d9e36188b142186c4fe962a40370490822')
def digest(b):return hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=digest(b),bytes=len(b))
def exclusive(path,v):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
assert sys.argv[1:] in [[],['--check'],['--apply-root-canonical']]
apply=sys.argv[1:]==['--apply-root-canonical']
assert os.getuid()==os.geteuid()==1000,'dispatcher runs ordinary integration without sudo'
assert pin(B)['sha256']=='ef584ac0f1a96f819591da0bb97e7625ebf32a287ce7d90d2bf4e7125076188e'
bind=json.loads(B.read_text());assert tuple(bind['source_inputs'])==ALLOWED and tuple(bind['outputs'])==ALLOWED
review=E/'INDEPENDENT-SOURCE-ABI-ACCEPTANCE.ROOT-RECORD.json'
assert pin(review)['sha256']=='7b4382c28686032125b466595e73a2ed38643f8c2532488ede7c1790510c722f'
reviewdata=json.loads(review.read_text());assert reviewdata['verdict']=='PASS_PRIVATE_SET_TIMER_SOURCE_ABI_AND_ACTUAL_RUST_OBJECT_CONSUMER_ONLY'
assert {row['sha256'] for row in reviewdata['inputs']}=={'420092fe681cfb587b49fe362aff1c42db72abbc5a56a954e6c05487aef571a8','1b1d55a3bc57d3122607dc026b29c446a244977130597c5480f2541ab93241d7','7f2e8d83fe83067e64cdd6628cfb6dcc704d3ff99ef2c5d763faef9afe5969d3'}
assert pin(P/'INTEGRATION-PREPARATION-CHECK.json')['sha256']=='e88ea481eac10c55a4645c605af511d8b275e3493cebababef3fbc5dbd099e57'
intent=E/'CANONICAL-INTEGRATION-INTENT.ROOT-RECORD.json';receipt=E/'CANONICAL-INTEGRATION.ROOT-RECEIPT.json'
assert not intent.exists() and not receipt.exists(),'fresh one-shot integration receipts required'
fds=[];before={};after={};payloads={}
try:
 for i,rel in enumerate(ALLOWED):
  path=R/rel; expected=bind['source_inputs'][rel]; out=bind['outputs'][rel]
  assert expected['path']==str(path) and expected['sha256']==PRE[i] and out['sha256']==POST[i]
  payload=Path(out['path']).read_bytes();assert len(payload)==out['bytes'] and digest(payload)==POST[i]
  fd=os.open(path,(os.O_RDWR if apply else os.O_RDONLY)|os.O_NOFOLLOW);fds.append((rel,path,fd));s=os.fstat(fd)
  assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and (s.st_dev,s.st_ino)==(path.stat().st_dev,path.stat().st_ino)
  raw=os.read(fd,6<<20);assert len(raw)==expected['bytes'] and digest(raw)==PRE[i],rel
  before[rel]=dict(path=str(path),sha256=digest(raw),bytes=len(raw),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode));payloads[rel]=payload
 # Recheck all preimages through owned descriptors immediately before first mutation.
 for rel,path,fd in fds:
  os.lseek(fd,0,os.SEEK_SET);assert digest(os.read(fd,6<<20))==before[rel]['sha256'];s=os.fstat(fd)
  assert (s.st_dev,s.st_ino)==(path.stat().st_dev,path.stat().st_ino)
 if apply:
  exclusive(intent,dict(scope=bind['scope'],status='PREIMAGE_VERIFIED_ROOT_INTEGRATION_INTENT',script=pin(Path(__file__)),source_bindings=pin(B),independent_review=pin(review),canonical_preimages=before,expected_postimages={rel:dict(sha256=POST[i],bytes=len(payloads[rel])) for i,rel in enumerate(ALLOWED)},rollback='No automatic rollback or replay; preserve partial state/intent for dispatcher if any write/postcheck fails.'))
  for rel,path,fd in fds:
   os.lseek(fd,0,os.SEEK_SET);raw=payloads[rel];view=memoryview(raw)
   while view:
    n=os.write(fd,view);assert n>0;view=view[n:]
   os.ftruncate(fd,len(raw));os.fsync(fd)
  for i,(rel,path,fd) in enumerate(fds):
   os.lseek(fd,0,os.SEEK_SET);raw=os.read(fd,6<<20);s=os.fstat(fd);named=path.stat()
   assert len(raw)==len(payloads[rel]) and digest(raw)==POST[i]
   assert (s.st_dev,s.st_ino)==(named.st_dev,named.st_ino)==(before[rel]['device'],before[rel]['inode'])
   assert stat.S_IMODE(s.st_mode)==before[rel]['mode']
   after[rel]=pin(path)
  exclusive(receipt,dict(scope=bind['scope'],status='PASS_EXACT_THREE_FILE_CANONICAL_SOURCE_INTEGRATION_ONLY',execution_owner='/root',script=pin(Path(__file__)),source_bindings=pin(B),independent_review=pin(review),intent=pin(intent),actual_preimages=before,actual_postimages=after,canonical_files_written=list(ALLOWED),worklist_updated=False,whole_C_TU_default_link_native='OPEN',retirement_credit=False))
 print(json.dumps(dict(scope=bind['scope'],status='PASS_ROOT_INTEGRATION' if apply else 'PASS_READONLY_INTEGRATION_PREFLIGHT',canonical_writes=3 if apply else 0,preimages=before,postimages=after,receipt=pin(receipt) if apply else None)))
finally:
 for rel,path,fd in fds:os.close(fd)
