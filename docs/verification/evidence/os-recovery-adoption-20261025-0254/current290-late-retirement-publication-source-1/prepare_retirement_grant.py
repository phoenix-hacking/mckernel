"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite UID1000 metadata preparation. No process observations, execution or signals.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time

EVIDENCE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
WINDOW='new18h-20261026-bf8b8eb1832f4c94a0166f20a95642ea'
CUTOFFS=[1793100290.0,882395.5689528405,897734.6960034363]
OPERATION='RETIRE_EXACT_PREDECESSOR_KEEPER_PIDFD_ONLY'
GRANT_NAME='ROOT-ACTUAL-PREDECESSOR-RETIREMENT-GRANT.json'
REVIEW_NAME='ACTUAL-PREDECESSOR-RETIREMENT-INDEPENDENT-RELEASE.json'
PREDECESSOR=dict(boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',fd=6,parent=1193470,pgid=1193468,pid=1193473,starttime='83392603')
ORIGIN=dict(boot_id=PREDECESSOR['boot_id'],fd=3,parent=1060803,pgid=1060803,pid=1060806,starttime='80309560')
ADAPTER='exact-held-keeper1193473-fd6-origin1060806-v1'
PREDECESSOR_LAUNCH_SHA='4b12ca19177fcc5e5269608217286dbb01104a141570e79e14413429a9d5bfcf'
SOURCE_HASHES=dict(custody='5f7c9cd748b68116a958ed9d23be4ee69def6a4fa383c7638d92689e384ba6f1',keeper='942342288186d5ba186297b5a4b65fccff5940f31effe4dce1f2c8607e927027',phase='83df82d4e5bdb6310b7510bbcb2b42685ac460e66b93ef69b9c24ef6ba0d3ea7')
PIPELINE={role:dict(path=str(EVIDENCE/'current290-held-keeper-successor-source-1'/name),bytes=size,sha256=digest) for role,name,size,digest in [
 ('entry','capture_entry.py',11544,'358414da5b56b2aa94cf0ed34774ec69eeed551d8a87cf72758cb2a0d91068b5'),
 ('outer','capture_outer.py',9167,'3d3e46527400d7142a9c98dfa63f665d9973057526dce66b39417ac2e71800c4'),
 ('runtime','runtime_pipeline.py',17230,'fc0e0e58c60918e4ca80e4dee2e4d25678259317df9852a76ced649523c766aa')]}


def need(ok,why):
 if not ok:raise ValueError(why)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def parse(raw):
 def pairs(items):
  result={}
  for key,value in items:need(key not in result,'duplicate-json-key');result[key]=value
  return result
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite-json')))
def real_directory(path):
 path=Path(path);need(path.is_absolute() and path.resolve(strict=True)==path,'real-parent-path-no-symlinks')
 info=path.stat();need(stat.S_ISDIR(info.st_mode),'directory-required')
 return [info.st_dev,info.st_ino,info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode)]
def read_regular(path):
 path=Path(path);real_directory(path.parent);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=1<<20,'bounded-regular-metadata')
  raw=bytearray()
  while len(raw)<=before.st_size:
   block=os.read(fd,min(65536,before.st_size+1-len(raw)))
   if not block:break
   raw.extend(block)
  after=os.fstat(fd);fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  need(len(raw)==before.st_size and all(getattr(before,key)==getattr(after,key) for key in fields),'metadata-raced')
  current=path.lstat();need((current.st_dev,current.st_ino)==(after.st_dev,after.st_ino),'metadata-path-raced')
  raw=bytes(raw);return parse(raw),dict(path=str(path),bytes=len(raw),sha256=sha(raw))
 finally:os.close(fd)
def exclusive(directory,name,raw,mode=0o600):
 binding=real_directory(directory);fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  info=os.fstat(fd);need([info.st_dev,info.st_ino,info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode)]==binding,'opened-parent-binding')
  out=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode,dir_fd=fd)
  try:
   view=memoryview(raw)
   while view:
    count=os.write(out,view);need(count>0,'metadata-write-no-progress');view=view[count:]
   os.fsync(out)
  finally:os.close(out)
  os.fsync(fd)
 finally:os.close(fd)
 return dict(path=str(Path(directory)/name),bytes=len(raw),sha256=sha(raw))


def build_grant(prep,*,evidence_root=EVIDENCE):
 """Metadata only; evidence_root substitution is for private fixture directories."""
 prep=Path(prep);real_directory(prep);prefix='ROOT-NEW18H-KEEPER-SUCCESSOR-PREPARATION-'
 need(prep.parent==evidence_root and prep.name.startswith(prefix) and prep.name[len(prefix):].isdigit() and int(prep.name[len(prefix):])>=2,'fresh-successor-preparation-required')
 need(all(now<end for now,end in zip([time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)],CUTOFFS)),'fixed-parent-window-ended')
 packet,launch=read_regular(prep/'LAUNCH-PACKET.json');process,process_ref=read_regular(prep/'RUNTIME/PROCESS.json');held,held_ref=read_regular(prep/'RUNTIME/HELD-CUSTODY.json')
 need(packet.get('author')=='/root' and packet.get('scope')==SCOPE and packet.get('window_id')==WINDOW and packet.get('fixed_cutoffs')==CUTOFFS,'exact-new-window-packet')
 need(packet.get('standby_seconds')==120 and packet.get('mode')=='STANDBY_ONLY_UNTIL_SEPARATE_RETIREMENT_AUTH','unchanged-standby-admission')
 need(packet.get('pipeline_sources')==PIPELINE and packet.get('source_hashes')==SOURCE_HASHES,'exact-selected-source-bindings')
 need(packet.get('predecessor_custodian')==PREDECESSOR and packet.get('old_actor')==ORIGIN and packet.get('successor_custody_adapter')==ADAPTER,'exact-predecessor-not-origin-target')
 composition=packet['custody_successor_composition']
 need(composition.get('target')==PREDECESSOR and composition.get('lock_origin_pid')==1060806 and composition.get('predecessor_launch_sha256')==PREDECESSOR_LAUNCH_SHA and composition.get('custody_adapter')==ADAPTER,'exact-predecessor-composition')
 for key,name in [('evidence_directory','RUNTIME'),('entry_capture_directory','ENTRY'),('outer_capture_directory','OUTER')]:
  need(packet.get(key)==str(prep/name) and packet.get(key+'_identity')==real_directory(prep/name),'exact-preparation-directory:'+name)
 inbox=packet['command_inbox'];need(inbox.get('path')==str(prep/'INBOX') and inbox.get('identity')==real_directory(prep/'INBOX') and inbox['identity'][2:]==[0,0,0o700],'exact-root-inbox')
 keeper=process.get('keeper');need(isinstance(keeper,dict) and set(keeper)=={'pid','starttime','pgid'} and type(keeper['pid']) is int and keeper['pid']>0 and type(keeper['pgid']) is int and keeper['pgid']>0 and isinstance(keeper['starttime'],str) and keeper['starttime'].isdigit() and keeper['pid'] not in (1060806,1193473,1203549),'new-actual-keeper-required')
 need(process.get('launch_sha256')==launch['sha256'] and process.get('old_actor')==ORIGIN and process.get('source_hashes')==SOURCE_HASHES and process.get('scope')==SCOPE,'exact-runtime-process-binding')
 command=bytes.fromhex(process['command_hex']).split(b'\0');need(command[-1]==b'','framed-runtime-command');command=[arg.decode() for arg in command[:-1]]
 expected=['/home/holden/anaconda3/bin/python3.9','-I','-B',PIPELINE['entry']['path'],'--packet',launch['path'],'--packet-sha256',launch['sha256'],'--capture-directory',str(prep/'ENTRY'),'--authorization',str(prep/'LAUNCH-AUTHORIZATION.json'),'--authorization-sha256']
 need(command[:-1]==expected and len(command[-1])==64 and all(c in '0123456789abcdef' for c in command[-1]),'exact-new-process-argv')
 need(held.get('scope')==SCOPE and held.get('custody_adapter')==ADAPTER and held.get('predecessor_custodian')==PREDECESSOR and held.get('predecessor_launch_sha256')==PREDECESSOR_LAUNCH_SHA and held.get('old_actor')==ORIGIN and held.get('positive_pidfd_target_alive') is True and held.get('actor_birth_rechecked') is True and held.get('actual_retirement') is False and held.get('quarantine_untouched') is True,'exact-live-held-custody-metadata')
 custody=held['custody'];need(custody.get('holder_pid')==1193473 and custody.get('holder_fd')==6 and custody.get('retained_fd')==6 and custody.get('device')==27 and custody.get('inode')==4 and custody.get('lock_origin_pid')==1060806 and custody.get('same_description_observed') is True,'exact-held-copy-origin')
 return dict(author='/root',operation=OPERATION,scope=SCOPE,keeper=keeper,actual_keeper_process=process_ref,held_custody=held_ref,launch_sha256=launch['sha256'],pipeline_sources=packet['pipeline_sources'],source_hashes=packet['source_hashes'],target=PREDECESSOR,predecessor_custodian=PREDECESSOR,successor_custody_adapter=ADAPTER,lock_origin_pid=1060806,pidfd_sigkill_budget=1,numeric_or_group_signal_budget=0,predecessor_launch_sha256=PREDECESSOR_LAUNCH_SHA,fixed_cutoffs=CUTOFFS,standby_seconds=120,retry=False,later_adoption_shared_release_not_granted=True),packet


def prepare(prep,*,evidence_root=EVIDENCE):
 grant,_=build_grant(prep,evidence_root=evidence_root)
 ref=exclusive(Path(prep),GRANT_NAME,canonical(grant))
 return dict(root_grant=ref,keeper=grant['keeper'])

def main(argv=None):
 need(os.getuid()==os.geteuid()==1000,'uid1000-metadata-preparation-only')
 args=sys.argv[1:] if argv is None else argv;need(len(args)==1,'usage: prepare_retirement_grant.py PREP')
 print(json.dumps(prepare(Path(args[0])),sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
