#!/usr/bin/env python3
"""Read-only validation and one-shot execution release for scratch18 retry2."""
import argparse, hashlib, json, os, re, stat, subprocess, types
from pathlib import Path

REPO=Path('/home/holden/mckernel'); ROOT=Path('/home/holden/mckernel-work/scratch')
RELEASE_COMMIT='d97fd046f76ffff10b2d98eb1130969d77bbba5b'; RELEASE_REF='refs/remotes/origin/codex/local-native-staging-repair'
PREFIX='docs/verification/evidence/'; PACKET=PREFIX+'native-exact-scratch18-retry2-execution-20261001.py'; TEST='scripts/tests/test_native_exact_scratch18_retry2_execution_20261001.py'
TEMPLATE=PREFIX+'native-exact-scratch18-retry2-request-20261001.json'; WRAPPER='scripts/native_rust_exact_disk_build_wrapper.py'; CLEANUP=PREFIX+'native-exact-scratch18-interrupt-cleanup-terminal-20261001.json'
TEMPLATE_SHA256='eed75f5db927bd3eb0f1af7c16bc71952581578843eead2630ecf37d7162f106'; CANONICAL_TEMPLATE_SHA256='42cbf1b2b76ca445bbbf39ca69739032ca5b972da7da01ea5f1bcaea9ec026d9'; WRAPPER_SHA256='ccfbd404ff2428c4eb8841948b761118a42bd25ed8875c583755e6a97d8f0393'
EXECUTION_REQUEST=ROOT/'native-exact-build-request-scratch-18-retry2-20261001.execution.json'; PREP_REQUEST=ROOT/'native-exact-build-request-scratch-18-retry2-20261001.json'; PREP_PLAN=ROOT/'native-exact-scratch18-retry2-preparation.plan.json'; PREP_JOURNAL=ROOT/'native-exact-scratch18-retry2-preparation.journal.jsonl'; PREP_MUTEX=ROOT/'native-exact-scratch18-retry2-preparation.mutex'
ATTEMPT=ROOT/'native-exact-candidate-operational-exclusion-scratch18.json'; SHARED=ROOT/'mckernel-heavy-operation.lock'; LEASE=ROOT/'native-exact-build-lease-scratch18-retry2-20261001.json'; OUTPUT=ROOT/'mckernel-exact-candidate-scratch-18-retry2-20261001-output'; EVIDENCE=ROOT/'mckernel-exact-candidate-scratch-18-retry2-20261001-evidence'; OWNER=ROOT/'native-exact-scratch18-retry2-20261001-owner-evidence'
CONTRACT={'schema':'scratch18.publisher-contract.v1','coordination':'sole-campaign-coordinator-no-concurrent-build-or-cleanup','publishers':'project-owned-regular-file-O_CREAT|O_EXCL-only','census':'privileged-full-process-and-active-container-before-transaction-and-every-rmdir','excluded':'arbitrary-same-UID-directory-substitution-after-final-check'}
class Refusal(ValueError): pass
def sha(x): return hashlib.sha256(x).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def strict(raw):
 def pairs(xs):
  d={}
  for k,v in xs:
   if k in d: raise Refusal('duplicate-json-key')
   d[k]=v
  return d
 return json.loads(raw,object_pairs_hook=pairs)
def directory(path):
 path=Path(path)
 if not path.is_absolute() or '..' in path.parts: raise Refusal('noncanonical-path')
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  for part in path.parts[1:]:
   n=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd); os.close(fd); fd=n
  return fd
 except BaseException: os.close(fd); raise
def ident(st): return (st.st_dev,st.st_ino,st.st_nlink,stat.S_IMODE(st.st_mode),st.st_uid,st.st_gid,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
def read_regular(path):
 path=Path(path); d=directory(path.parent); f=None
 try:
  f=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=d); a=os.fstat(f)
  if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or a.st_size>16<<20: raise Refusal('artifact-shape')
  b=bytearray()
  while len(b)<=a.st_size:
   q=os.read(f,min(65536,a.st_size+1-len(b)))
   if not q: break
   b.extend(q)
  z=os.fstat(f); e=os.stat(path.name,dir_fd=d,follow_symlinks=False)
  if ident(a)!=ident(z) or ident(a)!=ident(e) or len(b)!=a.st_size: raise Refusal('artifact-raced')
  return bytes(b)
 finally:
  if f is not None: os.close(f)
  os.close(d)
def git(args):
 env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','LC_ALL':'C','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_SYSTEM':'/dev/null','GIT_CONFIG_GLOBAL':'/dev/null','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
 r=subprocess.run(['/usr/bin/git','--no-replace-objects','--git-dir',str(REPO/'.git')]+list(args),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
 if r.returncode: raise Refusal('git-check-failed')
 return r.stdout
def bound_sources(commit):
 if not re.fullmatch('[0-9a-f]{40}',commit or ''): raise Refusal('release-commit')
 if git(['rev-parse','--verify',RELEASE_REF+'^{commit}']).decode().strip()!=commit: raise Refusal('release-ref-mismatch')
 retained={}
 for p,h in ((TEMPLATE,TEMPLATE_SHA256),(WRAPPER,WRAPPER_SHA256),(CLEANUP,'0a711653f48d1e29705de818d6297dca34c89e7ed142dfbef8368de2b854cf10')):
  raw=read_regular(REPO/p)
  if sha(raw)!=h or git(['show',commit+':'+p])!=raw: raise Refusal('release-blob:'+p)
  retained[p]=raw
 for p in (PACKET,TEST):
  if git(['show',commit+':'+p])!=read_regular(REPO/p): raise Refusal('release-blob:'+p)
 return retained
def rec(path):
 s=path.stat(); data=b'' if stat.S_ISDIR(s.st_mode) else path.read_bytes()
 return {'path':str(path),'device':s.st_dev,'inode':s.st_ino,'nlink':s.st_nlink,'mode':'%04o'%stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size,'sha256':sha(data)}
def bind(path,row):
 if rec(path)!=row: raise Refusal('identity-binding:'+str(path))
def load_wrapper(data):
 m=types.ModuleType('_wrapper'); m.__file__=str(REPO/WRAPPER); exec(compile(data,m.__file__,'exec'),m.__dict__); return m
def cleanup_ok(raw=None):
 r=strict(read_regular(REPO/CLEANUP) if raw is None else raw)
 if r.get('result')!='PASS_TERMINAL_REPLAY' or r.get('acceptance_credit') is not False or r.get('publisher_contract')!=CONTRACT: raise Refusal('cleanup-terminal')
 for p in (ATTEMPT,SHARED,ROOT/'native-exact-build-lease-scratch-18.json'):
  if os.path.lexists(p): raise Refusal('cleanup-live-path')
 for section in ('archives','transaction_records'):
  rows=r.get(section)
  if not isinstance(rows,dict): raise Refusal('cleanup-records')
  for row in rows.values():
   if not isinstance(row,dict) or set(row)!={'path','device','inode','size','mode','sha256'} and set(row)!={'path','device','inode','size','mode','uid','gid','sha256'}: raise Refusal('cleanup-record-shape')
   path=Path(row['path']); live=rec(path)
   for key in ('path','device','inode','size','mode','sha256'):
    if live[key]!=row[key]: raise Refusal('cleanup-record-binding')
 return r
def prepared():
 raw=read_regular(PREP_REQUEST); q=strict(raw)
 if sha(raw)!=TEMPLATE_SHA256 or sha(canonical(q))!=CANONICAL_TEMPLATE_SHA256: raise Refusal('prepared-request-bytes')
 if q.get('preparation_only') is not False or q.get('execution_released') is not False or q.get('executable') is not True: raise Refusal('prepared-flags')
 plan=strict(read_regular(PREP_PLAN)); journal=read_regular(PREP_JOURNAL).splitlines()
 if plan.get('schema')!='scratch18.retry2.preparation.v1' or plan.get('release_commit')!=RELEASE_COMMIT or plan.get('request_sha256')!=sha(raw) or plan.get('cleanup_publication_sha256')!='0a711653f48d1e29705de818d6297dca34c89e7ed142dfbef8368de2b854cf10': raise Refusal('preparation-plan-binding')
 if plan.get('paths')!=[str(OUTPUT),str(EVIDENCE),str(OWNER),str(PREP_REQUEST)] or len(journal)!=8 or strict(journal[-1]).get('event')!='complete': raise Refusal('preparation-journal-binding')
 read_regular(PREP_MUTEX)
 ids={str(p):rec(p) for p in (PREP_MUTEX,PREP_PLAN,PREP_JOURNAL,PREP_REQUEST)}
 for p in (OUTPUT,EVIDENCE,OWNER):
  f=directory(p)
  try:
   s=os.fstat(f)
   if stat.S_IMODE(s.st_mode)!=0o700 or os.listdir(f): raise Refusal('fresh-directory')
   ids[str(p)]=rec(p)
  finally: os.close(f)
 return q,raw,ids
EXPECTED = {
 str(PREP_REQUEST):(1831,57643,1,'0600',1000,1000,3134,'eed75f5db927bd3eb0f1af7c16bc71952581578843eead2630ecf37d7162f106'),
 str(PREP_PLAN):(1831,57641,1,'0600',1000,1000,706,'3b22b670f7815cc36ac1bd2e6a5dd4562943f0b95e0a48094dd4088195affcd6'),
 str(PREP_JOURNAL):(1831,57642,1,'0600',1000,1000,1037,'41fc8f0b52d47302252de700aacce0bedaf857ca988a29c89416a821e2a6f133'),
 str(PREP_MUTEX):(1831,57640,1,'0600',1000,1000,0,'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
 str(OUTPUT):(1831,5374028,2,'0700',1000,1000,4096,sha(b'')),
 str(EVIDENCE):(1831,5374032,2,'0700',1000,1000,4096,sha(b'')),
 str(OWNER):(1831,5767173,2,'0700',1000,1000,4096,sha(b'')),
}
def fixed_production_bindings(ids):
 if ROOT != Path('/home/holden/mckernel-work/scratch'): return
 for p, expected in EXPECTED.items():
  actual=ids[p]
  if tuple(actual[k] for k in ('device','inode','nlink','mode','uid','gid','size')) != expected[:7] or actual['sha256'] != expected[7]: raise Refusal('prepared-binding:'+p)
def release(commit=RELEASE_COMMIT,execute=False):
 bound=bound_sources(commit); cleanup=cleanup_ok(bound[CLEANUP]); q,raw,ids=prepared(); fixed_production_bindings(ids); m=load_wrapper(bound[WRAPPER])
 m.OPERATIONAL_EXCLUSION_PATH=str(ATTEMPT); m.SHARED_HEAVY_LOCK_PATH=str(SHARED)
 v=m.validate_request(q)
 if v.get('status')!='PASS_COMPATIBILITY_ONLY' or v.get('execution_released') is not False: raise Refusal('wrapper-compatibility')
 census=m.census_request(PREP_REQUEST,sha(raw),q.get('launcher_aggregate_memory_gib','16.2158'))
 if census.get('status')!='PASS_READ_ONLY' or census.get('execution_released') is not False: raise Refusal('fresh-census')
 for p,row in ids.items(): bind(Path(p),row)
 d=dict(q); d['preparation_only']=False; d['execution_released']=True; d['executable']=True; out=canonical(d)+b'\n'
 if execute:
  if os.path.lexists(EXECUTION_REQUEST): raise Refusal('execution-request-present')
  fd=directory(EXECUTION_REQUEST.parent)
  try:
   f=os.open(EXECUTION_REQUEST.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
   try:
    n=os.write(f,out)
    if n!=len(out): raise Refusal('short-publish')
    os.fsync(f)
   finally: os.close(f)
   os.fsync(fd)
  finally: os.close(fd)
  published=read_regular(EXECUTION_REQUEST)
  if published!=out: raise Refusal('execution-request-binding')
  result=m.run_request(d,q.get('launcher_aggregate_memory_gib','16.2158'))
  if not isinstance(result,dict) or result.get('status')!='PASS': raise Refusal('wrapper-terminal-result')
  return {'status':'PASS_EXECUTED','execution_released':True,'executable':True,'prepared_request_sha256':sha(raw),'derived_request_sha256':sha(out),'release_commit':commit,'census':census,'cleanup_result':cleanup['result'],'wrapper_result':result}
 return {'status':'PASS_VALIDATE_ONLY','execution_released':False,'executable':True,'prepared_request_sha256':sha(raw),'derived_request_sha256':sha(out),'release_commit':commit,'census':census,'cleanup_result':cleanup['result']}
def main(argv=None):
 p=argparse.ArgumentParser(allow_abbrev=False); p.add_argument('--release-commit',required=True); p.add_argument('--execute',action='store_true'); a=p.parse_args(argv)
 try: print(json.dumps(release(a.release_commit,a.execute),sort_keys=True)); return 0
 except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as e: print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 1
if __name__=='__main__': raise SystemExit(main())
