#!/usr/bin/env python3
"""Draft postflight-only recovery: no retirement, root rename, or lock removal.

Run only after a separately fetched release, through the external sudo boundary.
Original evidence remains immutable. The corrected observer executes in this
process from authenticated bytes; the predecessor baseline is explicitly bound.
"""
import argparse
from decimal import Decimal
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import stat
import struct
import sys
import tarfile
import types

SOURCE=Path('/home/holden/mckernel')
PACKET_REL='docs/verification/evidence/native-exact-candidate-retirement-postflight-76ae20b5-1.py'
TEST_REL='scripts/tests/test_native_exact_candidate_retirement_postflight_76ae20b5.py'
RELEASE_REL='docs/verification/evidence/stability-native-exact-candidate-retirement-postflight-76ae20b5-1.release.json'
RELEASE_SHA256='aba167b8ac6cf3167e6946f30197c079e2d6df534ebb28c06f2c75934096522d'
OLD_COMMIT='99fd0558dfce14c8f53c3fb2c0253129ccb25c60'
SUPPORT_REL='docs/verification/evidence/native-exact-candidate-retirement-76ae20b5-1.py'
SUPPORT_SHA='91ed39cb0ce6c75172c83eb64632ceebab7f0781d1433d18fe173fa7709526e4'
OLD_RELEASE_REL='docs/verification/evidence/stability-native-exact-candidate-retirement-76ae20b5-1.release.json'
OLD_RELEASE_SHA='d725b00db634fe553fc2029ff5c83bf1b03630b80d062520a60a5b688f61c9ce'
OBSERVER_COMMIT='0a795fcb3e5c6527239d08e39b793543a2e86c91'
OBSERVER_REL='docs/verification/evidence/native-exact-candidate-live-reference-observer-76ae20b5-1.py'
OBSERVER_SHA='7ab91bd96a1ff768a3c5704d0cf614602969c340c15ecb54d9914f38f580c27f'
OBSERVER_TEST_REL='scripts/tests/test_native_exact_candidate_live_reference_observer_76ae20b5.py'
OBSERVER_TEST_SHA='fc84ad15fcfbc13114ffee6f7f25cb64d7ba7e9494ce7fa26dea8a3c8f326c1c'
PREDECESSOR_SHA='e81b9a654be747839880585935d3428cbdf084d25eb8a5295682a8371cb2803a'
BOOT='c733d83b-a5ae-4f91-9ce6-9f8ccf119afd'
LAUNCHERS=((4055286,92631630),(4055294,92631636),(4055298,92631642))
OLD_DIR=Path('/dev/shm/.mckernel-retirement-evidence-76ae20b5-1')
OUTPUT=Path('/dev/shm/.mckernel-retirement-postflight-76ae20b5-2')
PRIOR_DIR=Path('/dev/shm/.mckernel-retirement-postflight-76ae20b5-1')
PRIOR_COMMIT='f437992b8e333696e4fc827e9921839ce28ddcf3'
PRIOR_PACKET_SHA='d8b4baed324f160e9074fb8da93bc74ea835ec393a3121b62ba5f43931439677'
PRIOR_RELEASE_SHA='abeb2ec6cfb1c0fbb5153ae6e05b076a7ac687a5ed4002dead398ca388658fe0'
PRIOR_OBSERVER_SHA='23936865f6125e6f9ca4be9ac49eb75a4139cc669646720d016a48d7f98edb11'
PRIOR_ARCHIVE=Path('/home/holden/mckernel-work/scratch/native-exact-candidate-retirement-postflight-76ae20b5-1-failed-evidence-20260930-1.tar')
PRIOR_ARCHIVE_SHA='15309d25f692c444bca202f180490a9d03772c89055b5e912705b556e5e05fd1'
PRIOR_ARCHIVE_BYTES=2375680
PRIOR_COMPARABLE_SHA='2818f95e30e7a56cca7c318b7c447d01ef82fad87cf3d045c5569df215b73606'
PRIOR_IDENTITY_SHA='38cae43e7f9e191726c6fd360f41466bbb67cffbd217763429b56935b07293c2'
PRIOR_SPECIAL={'packet.failure':'6de91efe3d1ae8f0ac7a5a7acdc07230dff397a8e4f589891dfadaf80ba762e0',
 'post-delete-scan-1.json':'b03a1c47cb12eca928fcbd76ff504b73b5505cc478c79bfc3a033fb94312f98f',
 'post-delete-scan-2.json':'e20eb7d88f850088fe520e0349e4861d1912ecdb6952af5537670aac910e5179'}
ARCHIVE=Path('/home/holden/mckernel-work/scratch/native-exact-candidate-retirement-76ae20b5-1-failed-evidence-20260930-1.tar')
ARCHIVE_SHA='9ecab3772c9b8a6e3a4b0257bce3136734e0bac0becf4b79157b35bb78ce9abe'
ARCHIVE_BYTES=10874880
COMPARABLE_SHA='74758565a5c6e4fc18381e23eeba61f7d279a986f4a9014465e30cbc4c0c4b77'
IDENTITY_SHA='e98cf2d252150c5afba4725995b550cca67352a771f7dda67f5995793e386008'
# Historical archive-verification identity is retained above. A subsequent
# read-only admission found identity-only drift; its field delta is unlocalized.
# Comparable content/metadata and archive bytes stayed exact. Admit only the
# independently observed current identity, with identical NOATIME snapshots.
LIVE_IDENTITY_SHA='f00e5da2d9f426477f29f2102426c7a0346b7cf7e9c4a9593f3743c227cdf9cb'
BASELINE_SHA='bc5296ee81956659420df058c5975931bcb836ebe3416ed98214c1167f8a046b'
FAILURE_SHA='e1e629b6f43a9661fcfe255b7b0607be365acb0812b028de6f99075837c36ec1'
FAILED_SCAN_SHA='18c8c505b79307195906e4fc2faf1f521178bf4f3ca0f069e2b89e2ef5c52778'
SPECIAL={'observer.stdout':BASELINE_SHA,'packet.failure':FAILURE_SHA,'post-delete-scan-1.json':FAILED_SCAN_SHA,
 'evidence-76ae20b5-1.json':'fc6b61bf76363df72240f746c087685cb9778b0ccf2c71f602b56bee4ae938b8',
 'journal-76ae20b5-1.jsonl':'de54a05ffaaa8c090e4408d455f3b2ba2e82683de2d1822b6f3d7af67f75a598'}
WORK=Path('/home/holden/mckernel-work/scratch')
LOCKS=(('native-exact-candidate-operational-exclusion-76ae20b5.json',31508,444,'fa8a854775d4387769e44966ddab87943122bc8c35ae8d6577c6f60dbc65c210'),
 ('native-exact-build-lease-76ae20b5-1.json',31509,426,'a68867c85058eac82013575427851b4cc2ec38b310e8572e399fa5107166d8a2'),
 ('native-exact-build-lease-76ae20b5-disk-1.json',31510,431,'b25bd68e9b03249c57b8538e7192ef01b1acc6e0f686c81b79f55076efff31dd'),
 ('native-exact-build-lease-76ae20b5-disk-validation-2.json',31511,442,'027b4db20d377c5b9f7e7c0eb999452e40fa3ef110e191db68713efcdaf83e88'),
 ('native-exact-build-lease-76ae20b5-disk-retirement-1.json',31512,442,'4716843b04b58a4c8004ab4381197b9a78ba2179fdeb11f1a63b52dda3ea4b9f'))
H64=re.compile(r'[0-9a-f]{64}')
CAP=64<<20
TIMEOUT_SECONDS=900

class Error(RuntimeError):pass
def require(value,label):
 if not value:raise Error(label)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def decode(raw):
 def unique(items):
  result={}
  for k,v in items:
   require(k not in result,'duplicate JSON key');result[k]=v
  return result
 try:return json.loads(raw.decode('utf8'),object_pairs_hook=unique)
 except (ValueError,UnicodeError,TypeError):raise Error('invalid JSON') from None
def signature(st):return [st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_gid,st.st_size,st.st_mtime_ns,st.st_ctime_ns,st.st_atime_ns,st.st_nlink]
def noatime(directory=False):return os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NOATIME|(os.O_DIRECTORY if directory else 0)
def open_directory(path):
 path=Path(path);require(path.is_absolute() and '..' not in path.parts,'noncanonical directory')
 fd=os.open('/',noatime(True))
 try:
  for name in path.parts[1:]:
   child=os.open(name,noatime(True),dir_fd=fd)
   try:os.close(fd)
   except BaseException:os.close(child);raise
   fd=child
  return fd
 except BaseException:os.close(fd);raise
def read_fd(fd,cap=CAP):
 before=os.fstat(fd);require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=cap,'regular file shape')
 os.lseek(fd,0,os.SEEK_SET);parts=[];count=0
 while True:
  part=os.read(fd,min(1<<20,cap+1-count))
  if not part:break
  count+=len(part);require(count<=cap,'file exceeds cap');parts.append(part)
 require(count==before.st_size and signature(before)==signature(os.fstat(fd)),'file changed while read')
 return b''.join(parts)

class PinnedFile:
 def __init__(self,path,wanted=None,size=None,identity=None,root_owned=False):
  self.path=Path(path);self.parent=self.fd=None;self.wanted=wanted;self.size=size;self.expected=identity;self.root_owned=root_owned
  try:
   self.parent=open_directory(self.path.parent);self.parent_identity=signature(os.fstat(self.parent))[:5]
   self.fd=os.open(self.path.name,noatime(),dir_fd=self.parent);self.identity=signature(os.fstat(self.fd));self.raw=read_fd(self.fd)
   self.assert_held()
  except BaseException:
   self.close();raise
 def assert_held(self):
  p=os.lstat(self.path.parent);st=os.fstat(self.fd);named=os.stat(self.path.name,dir_fd=self.parent,follow_symlinks=False)
  require(signature(p)[:5]==self.parent_identity==signature(os.fstat(self.parent))[:5],'file parent replaced')
  require(signature(st)==self.identity==signature(named),'file identity changed')
  if self.expected is not None:require((st.st_dev,st.st_ino)==self.expected,'file binding identity')
  if self.root_owned:require((st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode))==(0,0,0o600),'file owner/mode')
  if self.size is not None:require(st.st_size==self.size,'file exact size')
  raw=read_fd(self.fd)
  require(raw==self.raw and (self.wanted is None or digest(raw)==self.wanted),'file digest binding')
 def close(self):
  failed=False
  for key in ('fd','parent'):
   fd=getattr(self,key,None);setattr(self,key,None)
   if fd is not None:
    try:os.close(fd)
    except BaseException:failed=True
  if failed:raise Error('descriptor cleanup failed')

def module_from(pin,name):
 pin.assert_held();fd=os.memfd_create('postflight-authenticated-source',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
 try:
  offset=0
  while offset<len(pin.raw):
   count=os.write(fd,pin.raw[offset:]);require(count>0,'sealed source short write');offset+=count
  flags=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE
  fcntl.fcntl(fd,fcntl.F_ADD_SEALS,flags);require(fcntl.fcntl(fd,fcntl.F_GET_SEALS)&flags==flags,'source seals missing')
  m=types.ModuleType(name);m.__file__='/proc/self/fd/'+str(fd);m.__package__='';m._postflight_source_fd=fd
  exec(compile(pin.raw,m.__file__,'exec'),m.__dict__);return m
 except BaseException:os.close(fd);raise

def source_inventory(fd):
 """Exact reviewer format; O_NOATIME preserves every original timestamp."""
 rows=[];identities=[]
 def visit(directory,rel):
  st=os.fstat(directory);identities.append([rel,signature(st)])
  rows.append({'path':rel,'type':'directory','uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'size':0,'mtime_ns':st.st_mtime_ns,'target':None,'sha256':None,'xattrs':{k:os.getxattr(directory,k).hex() for k in os.listxattr(directory)}})
  for name in sorted(os.listdir(directory)):
   require(name not in ('.','..') and '/' not in name,'unsafe evidence name');path=name if rel=='.' else rel+'/'+name
   before=os.stat(name,dir_fd=directory,follow_symlinks=False);require(stat.S_ISREG(before.st_mode),'unexpected evidence member type')
   child=os.open(name,noatime(),dir_fd=directory)
   try:
    require(signature(before)==signature(os.fstat(child)),'evidence open race');raw=read_fd(child)
    rows.append({'path':path,'type':'file','uid':before.st_uid,'gid':before.st_gid,'mode':stat.S_IMODE(before.st_mode),'size':before.st_size,'mtime_ns':before.st_mtime_ns,'target':None,'sha256':digest(raw),'xattrs':{k:os.getxattr(child,k).hex() for k in os.listxattr(child)}})
    identities.append([path,signature(before)])
    require(signature(before)==signature(os.stat(name,dir_fd=directory,follow_symlinks=False)),'evidence member replaced')
   finally:os.close(child)
  require(signature(st)==signature(os.fstat(directory)),'evidence directory changed')
 visit(fd,'.');return sorted(rows,key=lambda x:x['path']),sorted(identities,key=lambda x:x[0])

def archive_inventory(raw):
 rows=[];seen=set()
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
  for member in archive.getmembers():
   name=member.name
   while name.startswith('./'):name=name[2:]
   name=name.rstrip('/') or '.'
   require(not name.startswith('/') and '..' not in name.split('/') and name not in seen,'archive path');seen.add(name)
   require(member.isdir() or member.isfile(),'archive member type')
   data=None
   if member.isfile():
    stream=archive.extractfile(member)
    with stream:data=stream.read(CAP+1)
    require(len(data)==member.size and len(data)<=CAP,'archive member bound')
   xattrs={k[len('SCHILY.xattr.'):]:v.encode('utf8','surrogateescape').hex() for k,v in member.pax_headers.items() if k.startswith('SCHILY.xattr.')}
   rows.append({'path':name,'type':'directory' if member.isdir() else 'file','uid':member.uid,'gid':member.gid,'mode':member.mode,'size':0 if member.isdir() else member.size,'mtime_ns':int(Decimal(member.pax_headers.get('mtime',str(member.mtime)))*1000000000),'target':None,'sha256':None if data is None else digest(data),'xattrs':xattrs})
 return sorted(rows,key=lambda x:x['path'])

def validate_original_inventory(rows,identities,archived,prior=None):
 require(len(rows)==25 and len([x for x in rows if x['type']=='file'])==24 and sum(x['size'] for x in rows)==10826817,'original evidence counts')
 require(digest(encoded(rows))==COMPARABLE_SHA and digest(encoded(identities))==LIVE_IDENTITY_SHA,'original evidence inventory binding')
 require(rows==archived,'archive/live evidence mismatch')
 if prior is not None:require((rows,identities)==prior,'original evidence changed across NOATIME snapshots')
 bypath={x['path']:x for x in rows}
 for name,wanted in SPECIAL.items():require(bypath.get(name,{}).get('sha256')==wanted,'original special evidence binding')

def validate_prior_inventory(rows,identities,archived,prior=None):
 require(len(rows)==4 and len([x for x in rows if x['type']=='file'])==3 and sum(x['size'] for x in rows)==2362404,'prior postflight evidence counts')
 require(digest(encoded(rows))==PRIOR_COMPARABLE_SHA and digest(encoded(identities))==PRIOR_IDENTITY_SHA,'prior postflight inventory binding')
 require(rows==archived,'prior postflight archive/live mismatch')
 if prior is not None:require((rows,identities)==prior,'prior postflight changed across NOATIME snapshots')
 bypath={x['path']:x for x in rows}
 for name,wanted in PRIOR_SPECIAL.items():require(bypath.get(name,{}).get('sha256')==wanted,'prior postflight special binding')

def prior_release_inputs():
 return {'commit':PRIOR_COMMIT,'packet_sha256':PRIOR_PACKET_SHA,'release_sha256':PRIOR_RELEASE_SHA,'observer_sha256':PRIOR_OBSERVER_SHA,
  'source_evidence':{'path':str(PRIOR_DIR),'device':26,'inode':69537,'uid':0,'gid':0,'mode':0o700,'entries':4,'files':3,'bytes':2362404,'comparable_sha256':PRIOR_COMPARABLE_SHA,'historical_identity_sha256':PRIOR_IDENTITY_SHA,'admission_identity_sha256':PRIOR_IDENTITY_SHA,'stable_noatime_snapshots':True,'special':PRIOR_SPECIAL},
  'archive':{'path':str(PRIOR_ARCHIVE),'size':PRIOR_ARCHIVE_BYTES,'sha256':PRIOR_ARCHIVE_SHA}}

def validate_predecessor(baseline,old_release,observer):
 require((baseline.get('schema'),baseline.get('status'),baseline.get('scan_complete'),baseline.get('boot_id'),baseline.get('observer_sha256'),baseline.get('failure'))==('mckernel.read-only-live-reference-snapshot.v7','PASS',True,BOOT,PREDECESSOR_SHA,None),'predecessor baseline provenance')
 require(old_release.get('observer',{}).get('observer_sha256')==PREDECESSOR_SHA and old_release.get('boot_id')==BOOT,'predecessor release provenance')
 roots=baseline.get('roots');require(isinstance(roots,list) and len(roots)==2,'baseline root pair')
 targets=[];inodes=set()
 for index,(row,released) in enumerate(zip(roots,old_release['roots'])):
  path=observer.QUARANTINE[index];root=released['root'];expected_root=(root['device'],root['inode'],0,0,stat.S_IFDIR,0o700)
  require((row.get('path'),row.get('device_number'),row.get('inode'),row.get('device'),row.get('uid'),row.get('gid'),row.get('mode'),row.get('filesystem_root'))==(str(path),root['device'],root['inode'],'0:26',0,0,'0700','/'+path.name),'baseline mount/root coordinates')
  members={expected_root}
  for item in released['members']:
   members.add((item['device'],item['inode'],item['uid'],item['gid'],{'directory':stat.S_IFDIR,'file':stat.S_IFREG,'symlink':stat.S_IFLNK}[item['kind']],item['mode']))
  require(row.get('tree_root_identity')==list(expected_root) and row.get('tree_member_identities')==[list(x) for x in sorted(members)] and row.get('tree_inode_count')==len(members) and row.get('tree_membership_sha256')==observer.membership_digest(members),'baseline released member coverage')
  inodes.update((x[0],x[1]) for x in members);targets.extend((row,dict(row,path=str(observer.ORIGINAL[index]),filesystem_root='/'+observer.ORIGINAL[index].name)))
 reference=baseline.get('canonical_dev_shm');require(isinstance(reference,dict) and observer.is_canonical(reference,{'device':'0:26'}),'baseline canonical mount')
 require(baseline.get('persistent_tree_revalidation_failures')==[],'predecessor tree failure')
 rounds=baseline.get('rounds');require(isinstance(rounds,list) and 2<=len(rounds)<=5,'predecessor rounds')
 for row in rounds[-2:]:
  require(row.get('clean') is True and row.get('complete_mount_proofs') is True and row.get('closure_nonconvergent') is False,'predecessor closure')
  for key in ('target_references','permission_denials','tree_revalidation_failures','unscanned_final_identities','unresolved_churn'):require(row.get(key)==[],'predecessor incomplete closure')
 return targets,reference,inodes

def validate_round(row,number,inodes):
 require((row.get('schema'),row.get('status'),row.get('round'),row.get('scan_complete'),row.get('observer_sha256'),row.get('baseline_sha256'),row.get('retained_inode_count'))==('mckernel.post-delete-live-reference-round.v1','PASS',number,True,OBSERVER_SHA,BASELINE_SHA,len(inodes)),'postflight round binding')
 for key in ('path_failures_before','path_failures_after','target_references','permission_denials','incomplete','identity_replacements','entry_churn','unscanned_final_identities'):require(row.get(key)==[],'postflight incomplete closure')
 require(row.get('task_churn') is False and row.get('closure_nonconvergent') is False,'postflight churn')
 censuses=row.get('censuses');passes=row.get('closure_passes')
 require(type(passes) is int and 1<=passes<=5 and isinstance(censuses,list) and len(censuses)==passes+1,'postflight census bounds')
 def identity(value):
  require(isinstance(value,(list,tuple)) and len(value)==3 and all(type(x) is int and x>0 for x in value[:2]) and isinstance(value[2],str) and re.fullmatch('[0-9]+',value[2]),'postflight identity shape')
  return tuple(value)
 sets=[];starts={}
 for census in censuses:
  require(isinstance(census,list),'postflight census shape');values=[identity(x) for x in census]
  require(len(set(values))==len(values),'duplicate census identity');sets.append(set(values))
  for who in values:require(starts.setdefault(who[:2],who[2])==who[2],'postflight census identity reuse')
 final=sets[-1];observed=set().union(*sets)
 require(row.get('task_census_changed') is any(x!=sets[0] for x in sets[1:]),'postflight census diagnostic')
 require(row.get('reconciled_exits')==[{'identity':list(who),'resolution':'exited'} for who in sorted(observed-final)],'postflight reconciled exits')
 records=row.get('records');require(isinstance(records,list),'postflight records shape');seen=set();successful=set()
 for record in records:
  require(isinstance(record,dict),'postflight record shape');who=identity(record.get('identity'))
  require(who in observed and who not in seen,'unbound or duplicate postflight identity');seen.add(who)
  require(record.get('references')==[] and record.get('denials')==[] and record.get('incomplete')==[],'postflight process hazards')
  absences=record.get('expected_absences',[]);require(isinstance(absences,list) and all(isinstance(x,dict) and x.get('reason')!='per-entry-procfs-absence' for x in absences),'postflight record entry churn')
  if record.get('successful') is True and record.get('state')=='same':
   proof=record.get('mount_proof',{});require(isinstance(proof,dict) and proof.get('complete') is True and proof.get('identity')==record.get('identity'),'postflight mount proof');successful.add(who)
  else:require(record.get('successful') is False and record.get('state')=='exited' and who not in final,'postflight unresolved process state')
 require(final and final<=successful,'postflight final census coverage')

def final_bytes(template,release_sha):
 sentinel=b'RELEASE_SHA256='+bytes((39,))+b'RELEASE_HASH_REQUIRED'+bytes((39,));require(template.count(sentinel)==1 and H64.fullmatch(release_sha),'finalization binding')
 return template.replace(sentinel,b"RELEASE_SHA256='"+release_sha.encode()+b"'")
def fixed_release_inputs():
 return {'prior_postflight':prior_release_inputs(),'old_commit':OLD_COMMIT,'support_sha256':SUPPORT_SHA,'old_release_sha256':OLD_RELEASE_SHA,'observer_commit':OBSERVER_COMMIT,'observer_sha256':OBSERVER_SHA,'observer_test_sha256':OBSERVER_TEST_SHA,'predecessor_sha256':PREDECESSOR_SHA,'boot_id':BOOT,'launcher_identities':[list(x) for x in LAUNCHERS],'source_evidence':{'path':str(OLD_DIR),'device':26,'inode':69508,'comparable_sha256':COMPARABLE_SHA,'historical_identity_sha256':IDENTITY_SHA,'admission_identity_sha256':LIVE_IDENTITY_SHA,'stable_noatime_snapshots':True,'special':SPECIAL},'archive':{'path':str(ARCHIVE),'device':1831,'inode':31513,'size':ARCHIVE_BYTES,'sha256':ARCHIVE_SHA},'locks':[{'path':str(WORK/name),'device':1831,'inode':ino,'size':size,'sha256':sha,'uid':0,'gid':0,'mode':0o600,'immutable':True} for name,ino,size,sha in LOCKS],'protected':{'disk_candidate':{'path':str(WORK/'mckernel-exact-candidate-76ae20b5-disk-1'),'device':1831,'inode':4194306},'disk_backup':{'path':str(WORK/'mckernel-exact-metadata-backup-76ae20b5-disk-1'),'device':1831,'inode':4204970},'seal':{'path':str(WORK/'native-exact-candidate-disk-validation-76ae20b5-2-evidence/corrupt-tmpfs-archive.bin'),'device':1831,'inode':4849667,'size':40004941,'sha256':'192f8fe161ee0e486b0c0532f64bc34bb0684da2b113d01d13dc4f4ba7bb1c2c'}},'resource_floors':{'host':16<<30,'scratch':12<<30,'tmpfs':4<<30,'memory':4<<30},'output':str(OUTPUT),'rounds':3,'timeout_seconds':TIMEOUT_SECONDS,'retirement':False,'deletion':False,'lock_removal':False}

def admit(support,release_path):
 require(Path(release_path)==SOURCE/RELEASE_REL,'canonical release argument')
 head,upstream,fetched=(support.gscalar(support.GIT,'rev-parse',x) for x in ('HEAD','@{upstream}','FETCH_HEAD'))
 require(head==upstream==fetched,'fetched head mismatch')
 pin=PinnedFile(SOURCE/RELEASE_REL,RELEASE_SHA256)
 try:
  require(support.blob(support.GIT,fetched,RELEASE_REL)==pin.raw,'fetched release bytes');r=decode(pin.raw)
 finally:pin.close()
 require(set(r)=={'schema','status','inputs','template','finalization'} and r['schema']=='mckernel.retirement-postflight-release.v1' and r['status']=='PASS_ONE_SHOT_POSTFLIGHT' and r['inputs']==fixed_release_inputs(),'postflight release scope')
 template=r['template'];commit=template.get('commit');require(isinstance(commit,str) and re.fullmatch('[0-9a-f]{40}',commit),'template commit')
 require(r['finalization']=={'prior_ancestor':commit,'allowed_changed_paths':[PACKET_REL,RELEASE_REL]},'mechanical finalization scope')
 for ancestor in (commit,OLD_COMMIT,OBSERVER_COMMIT,PRIOR_COMMIT):require(support.run_bounded(support.gargv(support.GIT,'merge-base','--is-ancestor',ancestor,fetched))[2]==0,'source ancestry')
 require(digest(support.blob(support.GIT,PRIOR_COMMIT,PACKET_REL))==PRIOR_PACKET_SHA and digest(support.blob(support.GIT,PRIOR_COMMIT,RELEASE_REL))==PRIOR_RELEASE_SHA,'prior postflight source binding')
 require(support.gout(support.GIT,'diff','--name-only',commit,fetched).decode().splitlines()==[PACKET_REL,RELEASE_REL],'nonmechanical finalization')
 raw=support.blob(support.GIT,commit,PACKET_REL);test=support.blob(support.GIT,commit,TEST_REL)
 require(digest(raw)==template.get('packet_sha256') and digest(test)==template.get('test_sha256'),'template digests')
 require(support.blob(support.GIT,fetched,PACKET_REL)==final_bytes(raw,RELEASE_SHA256) and support.blob(support.GIT,fetched,TEST_REL)==test,'finalization bytes')
 return r,fetched

def execute(release_path):
 require(RELEASE_SHA256!='RELEASE_HASH_REQUIRED' and H64.fullmatch(RELEASE_SHA256),'DRAFT_NOT_RELEASED')
 require(os.geteuid()==0 and os.getegid()==0,'external root boundary required')
 pins=[];modules=[];oldfd=None;priorfd=None;output=None;publisher=None;protected=None;failure=None;completed=[];support=None
 require(signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),'preexisting execution timer')
 old_signals={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGALRM)}
 def interrupted(signum,frame):raise Error('postflight interrupted')
 def pin(path,sha=None,size=None,identity=None,root_owned=False):
  value=PinnedFile(path,sha,size,identity,root_owned);pins.append(value);return value
 try:
  for sig in old_signals:signal.signal(sig,interrupted)
  signal.setitimer(signal.ITIMER_REAL,TIMEOUT_SECONDS)
  support_pin=pin(SOURCE/SUPPORT_REL,SUPPORT_SHA);support=module_from(support_pin,'_postflight_support');modules.append(support)
  release,fetched=admit(support,release_path)
  selfpin=pin(SOURCE/PACKET_REL);require(selfpin.raw==support.blob(support.GIT,fetched,PACKET_REL),'local finalized packet')
  observer_pin=pin(SOURCE/OBSERVER_REL,OBSERVER_SHA);test_pin=pin(SOURCE/OBSERVER_TEST_REL,OBSERVER_TEST_SHA)
  old_release_pin=pin(SOURCE/OLD_RELEASE_REL,OLD_RELEASE_SHA);old_release=decode(old_release_pin.raw)
  for value,commit,path in ((support_pin,OLD_COMMIT,SUPPORT_REL),(old_release_pin,OLD_COMMIT,OLD_RELEASE_REL),(observer_pin,OBSERVER_COMMIT,OBSERVER_REL),(test_pin,OBSERVER_COMMIT,OBSERVER_TEST_REL)):
   require(value.raw==support.blob(support.GIT,commit,path),'historical source binding')
  require(digest(support.blob(support.GIT,OLD_COMMIT,OBSERVER_REL))==PREDECESSOR_SHA,'predecessor source binding')
  observer=module_from(observer_pin,'_postflight_corrected_observer');modules.append(observer)
  archive=pin(ARCHIVE,ARCHIVE_SHA,ARCHIVE_BYTES,(1831,31513),True);archived=archive_inventory(archive.raw)
  oldfd=open_directory(OLD_DIR);oldstat=os.fstat(oldfd)
  require((oldstat.st_dev,oldstat.st_ino,oldstat.st_uid,oldstat.st_gid,stat.S_IMODE(oldstat.st_mode))==(26,69508,0,0,0o700),'original evidence directory')
  rows,identities=source_inventory(oldfd);validate_original_inventory(rows,identities,archived)
  priorarchive=pin(PRIOR_ARCHIVE,PRIOR_ARCHIVE_SHA,PRIOR_ARCHIVE_BYTES,root_owned=True);priorarchived=archive_inventory(priorarchive.raw)
  priorfd=open_directory(PRIOR_DIR);priorstat=os.fstat(priorfd)
  require((priorstat.st_dev,priorstat.st_ino,priorstat.st_uid,priorstat.st_gid,stat.S_IMODE(priorstat.st_mode))==(26,69537,0,0,0o700),'prior postflight evidence directory')
  priorrows,priorids=source_inventory(priorfd);validate_prior_inventory(priorrows,priorids,priorarchived)
  priorfailure=decode(pin(PRIOR_DIR/'packet.failure',PRIOR_SPECIAL['packet.failure'],root_owned=True).raw)
  require((priorfailure.get('schema'),priorfailure.get('status'),priorfailure.get('release_sha256'),priorfailure.get('round_sha256'))==('mckernel.retirement-postflight-result.v1','FAIL',PRIOR_RELEASE_SHA,[PRIOR_SPECIAL['post-delete-scan-1.json']]),'prior postflight failure provenance')
  for number,status in ((1,'PASS'),(2,'FAIL')):
   name='post-delete-scan-%d.json'%number;record=decode(pin(PRIOR_DIR/name,PRIOR_SPECIAL[name],root_owned=True).raw)
   require((record.get('schema'),record.get('status'),record.get('round'),record.get('observer_sha256'),record.get('baseline_sha256'),record.get('recovery_release_sha256'))==('mckernel.post-delete-live-reference-round.v1',status,number,PRIOR_OBSERVER_SHA,BASELINE_SHA,PRIOR_RELEASE_SHA),'prior postflight round provenance')
  lockpins=[]
  for name,ino,size,sha in LOCKS:lockpins.append(pin(WORK/name,sha,size,(1831,ino),True))
  baseline_pin=pin(OLD_DIR/'observer.stdout',BASELINE_SHA,root_owned=True)
  baseline=decode(baseline_pin.raw);targets,reference,inodes=validate_predecessor(baseline,old_release,observer)
  failure_pin=pin(OLD_DIR/'packet.failure',FAILURE_SHA,root_owned=True);original_failure=decode(failure_pin.raw)
  require((original_failure.get('schema'),original_failure.get('status'),original_failure.get('release_sha256'))==('mckernel.packet-failure.v2','FAIL',OLD_RELEASE_SHA),'original packet failure provenance')
  scan_pin=pin(OLD_DIR/'post-delete-scan-1.json',FAILED_SCAN_SHA,root_owned=True);failed_scan=decode(scan_pin.raw)
  require((failed_scan.get('schema'),failed_scan.get('status'),failed_scan.get('round'),failed_scan.get('observer_sha256'),failed_scan.get('baseline_sha256'))==('mckernel.post-delete-live-reference-round.v1','FAIL',1,PREDECESSOR_SHA,BASELINE_SHA),'original observer failure provenance')
  protected=support.ProtectedDescriptors();protected.__enter__()
  def guard():
   require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'boot identity')
   for pid,start in LAUNCHERS:require(support.proc_starttime(pid)==start,'launcher identity')
   support.check_resource_floors();protected.assert_held()
   for value in pins:value.assert_held()
   for value in lockpins:
    buf=bytearray(4);fcntl.ioctl(value.fd,support.FS_IOC_GETFLAGS,buf,True)
    require(struct.unpack('I',buf)[0]&support.FS_IMMUTABLE_FL,'mutable exclusion')
    record=decode(value.raw);require(record.get('schema')=='mckernel.retirement-build-owner-exclusion.v2' and record.get('release_sha256')==OLD_RELEASE_SHA and record.get('boot_id')==BOOT and record.get('operational_exclusion')==str(value.path) and record.get('immutable') is True,'exclusion content')
   require(not observer.absence_failures(),'original or quarantine survived')
   require((os.lstat(OLD_DIR).st_dev,os.lstat(OLD_DIR).st_ino)==(26,69508),'original evidence replaced')
   now,ids=source_inventory(oldfd);validate_original_inventory(now,ids,archived,prior=(rows,identities))
   require((os.lstat(PRIOR_DIR).st_dev,os.lstat(PRIOR_DIR).st_ino)==(26,69537),'prior postflight evidence replaced')
   now,ids=source_inventory(priorfd);validate_prior_inventory(now,ids,priorarchived,prior=(priorrows,priorids))
  guard()
  parent=open_directory(OUTPUT.parent)
  try:
   st=os.fstat(parent);require((st.st_dev,st.st_ino,st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode))==(26,1,0,0,0o1777),'fresh output parent')
   os.mkdir(OUTPUT.name,0o700,dir_fd=parent);os.fsync(parent)
  finally:os.close(parent)
  output=support.OutputDir(OUTPUT);output.assert_fresh();publisher=support.OutputDir(OUTPUT);publisher.assert_fresh()
  for number in range(1,4):
   guard();output.assert_bound()
   row=observer.post_delete_round(number,BASELINE_SHA,targets,reference,inodes)
   row.update(boot_id=BOOT,observer_pid=os.getpid(),observer_starttime=str(support.proc_starttime(os.getpid())),predecessor_observer_sha256=PREDECESSOR_SHA,recovery_release_sha256=RELEASE_SHA256)
   output.write('post-delete-scan-%d.json'%number,encoded(row)+b'\n')
   validate_round(row,number,inodes);guard();output.assert_bound();completed.append(digest(encoded(row)+b'\n'))
  require(len(completed)==3,'three rounds required')
 except BaseException as error:failure=type(error).__name__
 # All pinned inputs and ordinary cleanup finish before terminal publication.
 try:signal.setitimer(signal.ITIMER_REAL,0)
 except BaseException:failure=failure or 'TimerCleanupError'
 for sig,handler in old_signals.items():
  try:signal.signal(sig,handler)
  except BaseException:failure=failure or 'SignalCleanupError'
 if protected is not None:
  try:protected.close()
  except BaseException:failure=failure or 'ProtectedCleanupError'
 if oldfd is not None:
  try:os.close(oldfd)
  except BaseException:failure=failure or 'EvidenceCleanupError'
 if priorfd is not None:
  try:os.close(priorfd)
  except BaseException:failure=failure or 'PriorEvidenceCleanupError'
 for value in reversed(pins):
  try:value.close()
  except BaseException:failure=failure or 'DescriptorCleanupError'
 for module in modules:
  try:os.close(module._postflight_source_fd)
  except BaseException:failure=failure or 'SourceCleanupError'
 if output is not None:
  try:output.close()
  except BaseException:failure=failure or 'OutputCleanupError'
 if publisher is not None:
  try:
   value={'schema':'mckernel.retirement-postflight-result.v1','status':'FAIL' if failure else 'PASS_POSTFLIGHT_ONLY','release_sha256':RELEASE_SHA256,'round_sha256':completed,'error_type':failure,'retirement':False,'deletion':False,'lock_removal':False}
   # No cleanup or retry of a partially written result. A failed write makes
   # this one-shot namespace unusable and is externally reported as failure.
   publisher.write('packet.failure' if failure else 'packet.status',encoded(value)+b'\n')
  except BaseException:failure=failure or 'TerminalDurabilityError'
  # Only read-only directory descriptors remain after durable publication.
  # Closing these cannot alter the terminal record; process exit releases them.
  try:publisher.close()
  except BaseException:pass
 if failure:raise Error('postflight failed: '+failure)
 return completed

def main(argv=None):
 parser=argparse.ArgumentParser();parser.add_argument('--release',required=True);args=parser.parse_args(argv);execute(args.release)
if __name__=='__main__':
 try:main()
 except BaseException as error:print('FAIL_CLOSED '+type(error).__name__,file=sys.stderr);sys.exit(2)
