#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Unreleased source-only child adapter. Caller/owner must establish descriptor
provenance, directory FD identity, source quiescence, custody and release.
"""
import hashlib,json,os,pathlib,stat,sys
A=pathlib.Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002')
BODY=A/'m14-scripts-materializer-parent-expert-1/materializer.py'
BODY_SHA='c3115c13a29dde74f6d316b64d26a6266c5a5cfeed877ef19de088844e09ba37'
VERIFIER_SHA='34bd9802c507b3408b685c6233f0a2f711edbdf7a6f31c5dcd3eaba70128ba8f'
UNION_SHA='48b2c25266784641b28100c08c7c7baa4559d0aaffe670223ee71936f3deaffa'
FUTURE_DESCRIPTOR_SHA=None # Must remain unbound until a separately reviewed live authority.
class Refusal(Exception):pass
def need(value,message):
 if not value:raise Refusal(message)
def _unique(pairs):
 d={}
 for k,v in pairs:
  need(k not in d,'duplicate JSON key: '+k);d[k]=v
 return d
def _canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def _read_body():
 fd=os.open(BODY,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_size<=1<<20,'body type or size');data=b''
  while True:
   b=os.read(fd,65536)
   if not b:break
   data+=b
  after=os.fstat(fd);keys=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  need(all(getattr(before,k)==getattr(after,k) for k in keys) and hashlib.sha256(data).hexdigest()==BODY_SHA,'body hash or stability')
 finally:os.close(fd)
 ns={'__name__':'bound_scripts_materializer','__file__':str(BODY)};exec(compile(data,str(BODY),'exec'),ns)
 need(callable(ns.get('copy_scripts_body')),'body interface');return ns['copy_scripts_body']
def _receipt(dirfd,name,record):
 fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=dirfd)
 try:
  data=_canonical(record);offset=0
  while offset<len(data):
   n=os.write(fd,data[offset:]);need(n>0,'receipt short write');offset+=n
  os.fsync(fd)
 finally:os.close(fd)
 os.fsync(dirfd)
def _execute(descriptor_bytes,manifest_bytes,receipt_dirfd):
 # Hash equality is not authentication: descriptor digest must come from the
 # independently authenticated owner, and stays None in this source candidate.
 need(FUTURE_DESCRIPTOR_SHA is not None,'future descriptor authority not bound')
 need(hashlib.sha256(descriptor_bytes).hexdigest()==FUTURE_DESCRIPTOR_SHA,'descriptor digest mismatch')
 d=json.loads(descriptor_bytes,object_pairs_hook=_unique)
 need(type(d) is dict and set(d)=={'source_root','output_root','manifest_sha256','body_sha256','verifier_sha256'},'descriptor schema')
 need(d['manifest_sha256']==UNION_SHA and d['body_sha256']==BODY_SHA and d['verifier_sha256']==VERIFIER_SHA,'descriptor input binding')
 need(hashlib.sha256(manifest_bytes).hexdigest()==UNION_SHA,'manifest digest mismatch')
 doc=json.loads(manifest_bytes,object_pairs_hook=_unique)
 for name in ('source_root','output_root'):
  p=d[name];need(type(p) is str and os.path.isabs(p) and os.path.normpath(p)==p and p!='/','normalized '+name)
 need(d['source_root']==doc['base_scripts_candidate'],'source root binding')
 need(not(d['output_root']==d['source_root'] or d['output_root'].startswith(d['source_root']+'/') or d['source_root'].startswith(d['output_root']+'/')),'source/output lexical separation')
 need(stat.S_ISDIR(os.fstat(receipt_dirfd).st_mode),'receipt directory FD')
 body=_read_body()
 intent={'status':'COPY_INTENT_UNQUALIFIED','descriptor_sha256':FUTURE_DESCRIPTOR_SHA,'manifest_sha256':UNION_SHA,'source_root':d['source_root'],'output_root':d['output_root'],'owner_custody':None,'native_acceptance':False}
 try:_receipt(receipt_dirfd,'intent.json',intent)
 except BaseException as e:return {'status':'UNKNOWN_RETAIN_OUTPUT','reason':'intent receipt: '+type(e).__name__}
 try:
  count=body(d['source_root'],d['output_root'],doc)
  need(type(count) is int and count==len(doc['base_members'])+len(doc['additions']),'copy body result count')
  outcome={'status':'SUCCESS_BODY_ONLY','entries':count,'output_root':d['output_root'],'owner_custody':None,'output_tree_durability':None,'native_acceptance':False}
 except Exception as e:
  outcome={'status':'FAILURE_PARTIAL_RETAIN_UNKNOWN','error_type':type(e).__name__,'output_root':d['output_root'],'owner_custody':None,'native_acceptance':False}
 except BaseException as e:
  outcome={'status':'UNKNOWN_RETAIN_OUTPUT','error_type':type(e).__name__,'output_root':d['output_root'],'owner_custody':None,'native_acceptance':False}
 try:_receipt(receipt_dirfd,'result.json',outcome)
 except BaseException as e:return {'status':'UNKNOWN_RETAIN_OUTPUT','reason':'result receipt: '+type(e).__name__}
 return outcome
def owner_view_of_bare_receipt(receipt_bytes):
 # No bare receipt, even valid-looking success, can prove direct wait, fsync,
 # owner identity or partial-output custody. No acceptance path exists here.
 return {'status':'UNKNOWN_RETAIN_OUTPUT','reason':'bare receipt lacks independently reviewed terminal, durability and custody evidence'}

def main():
 raise Refusal('UNRELEASED SCRIPTS CHILD: descriptor authority and custody not bound')
if __name__=='__main__':
 try:main()
 except Refusal as e:print(str(e),file=sys.stderr);sys.exit(1)
