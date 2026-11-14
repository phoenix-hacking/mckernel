"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded readonly serial-prefix observation. Producer reports are lowerbounds, never acceptance.
"""
from pathlib import Path
import base64,hashlib,importlib.util,json,os,stat,sys
NONCE='110f473a34f14ca58d88e080e273be2c'
SERIAL=Path('/home/holden/mckernel-work/native-runs/l12a1/p')/('attempt-'+NONCE)/'serial.log'
DECODER=Path('/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1/current110-variant-1/final-LONG-execution-preparation-1/bounded-correction-1/final-execution-assembly-1/post-M14-fresh-admission-preparation-1/expired-release-successor-1/serialized-release-successor-2/source/p12_long_session.py')
DECODER_SHA='bff717d885afdda0d82cd0ab05a0930a3e66b242c6200b1295f2173bb4cdc5d3'
CAP=8*2**20

def need(v,m):
 if not v:raise ValueError(m)
def anchor(pid,start):
 try:
  fields=(Path('/proc')/str(pid)/'stat').read_text().rpartition(') ')[2].split()
  return dict(pid=pid,expected_start=start,observed_start=int(fields[19]),state=fields[0],same_identity=int(fields[19])==start)
 except (FileNotFoundError,PermissionError,ValueError,IndexError) as exc:
  return dict(pid=pid,expected_start=start,same_identity=False,status='UNKNOWN_OR_RETIRED',error=type(exc).__name__)
def observe(pid,start):
 need(os.getuid()==os.geteuid()==1000,'ordinaryUID1000read only')
 raw_decoder=DECODER.read_bytes();need(hashlib.sha256(raw_decoder).hexdigest()==DECODER_SHA,'exact accepted decoder')
 spec=importlib.util.spec_from_file_location('accepted_LONG_wire_decoder',DECODER);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
 before_anchor=anchor(pid,start)
 need(SERIAL.resolve(strict=True)==SERIAL,'exact canonical nonce serialpath')
 fd=os.open(SERIAL,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
 try:
  a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_uid==a.st_gid==1000 and stat.S_IMODE(a.st_mode)==0o600 and a.st_dev==66306,'selectedHOSTUID1000serialidentity')
  size=min(a.st_size,CAP);parts=[];left=size
  while left:
   block=os.read(fd,min(left,65536));need(bool(block),'serial shrank during prefixread');parts.append(block);left-=len(block)
  raw=b''.join(parts);b=os.fstat(fd);named=SERIAL.lstat()
  fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink')
  need(all(getattr(a,k)==getattr(b,k)==getattr(named,k) for k in fields) and b.st_size>=a.st_size and named.st_size>=a.st_size,'same anchored append-capable serialFD; no shrink/replace')
 finally:os.close(fd)
 end=raw.rfind(b'\n')+1;complete=raw[:end];tail=raw[end:]
 text=complete.decode('ascii');need(text.count('\n')<=262144,'bounded prefixlinecount')
 total=0;rounds=0;profile_seen=False;pending={};latest=None;wire_error=None
 try:
  for line in text.splitlines(keepends=True):
   need(len(line)<d.LINE_CAP,'accepted wireline cap')
   name,_,payload=line.rstrip('\n').partition(' ')
   if name not in {'ND_PAIR_LONG_PROFILE','ND_PAIR_ROUND_START','ND_PAIR','ND_PAIR_ROUND_END','ND_PAIR_LONG_PROGRESS'}:continue
   need(len(line)<(4096 if name=='ND_PAIR' else 1024),'accepted JSONframecap')
   row=d.record(payload)
   if name=='ND_PAIR_LONG_PROFILE':
    need(not profile_seen and row==d.PROFILE and all(type(row[k]) is int for k in d.PROFILE),'exact once LONGprofile');profile_seen=True;continue
   need(profile_seen,'counter without sourceprofile')
   if name=='ND_PAIR_ROUND_START':
    d.keys(row,('round','time_ns','procfs_empty'));need(row['round']==rounds and d.integer(row['time_ns'],1) and row['procfs_empty'] is True and not pending,'ordered roundstart');pending['start']=row
   elif name=='ND_PAIR':
    need('start' in pending and 'report' not in pending and type(row.get('apps')) is list and len(row['apps'])==2 and row.get('os')==0 and row.get('generation')==1,'paired source identity');pending['report']=row
   elif name=='ND_PAIR_ROUND_END':
    d.keys(row,('round','time_ns','procfs_empty'));need('report' in pending and 'end' not in pending and row['round']==rounds and d.integer(row['time_ns'],1) and row['procfs_empty'] is True and row['time_ns']>pending['start']['time_ns'],'ordered roundend');pending['end']=row
   else:
    d.keys(row,('round','work_ns','cumulative_work_ns','launches'));need('end' in pending and all(d.integer(row[k]) for k in row),'complete progress frame')
    apps=pending['report']['apps'];need(all(all(d.integer(app.get(k),1) for k in ('pid','started_ns','reaped_ns','finished_ns')) and pending['start']['time_ns']<=app['started_ns']<=app['reaped_ns']<=app['finished_ns']<=pending['end']['time_ns'] for app in apps),'reported real app timebounds')
    need(apps[0]['pid']!=apps[1]['pid'] and max(app['started_ns'] for app in apps)<min(app['reaped_ns'] for app in apps),'reported distinct overlapping applications')
    work=max(app['reaped_ns'] for app in apps)-min(app['started_ns'] for app in apps)
    need(row==dict(round=rounds,work_ns=work,cumulative_work_ns=total+work,launches=(rounds+1)*2),'existing wire progress arithmetic')
    rounds+=1;total+=work;need(rounds<=d.PROFILE['round_cap'],'round cap');latest=row;pending={}
 except (ValueError,TypeError,KeyError,IndexError) as exc:wire_error=type(exc).__name__+': '+str(exc)
 after_anchor=anchor(pid,start)
 return dict(scope=__doc__,status='OBSERVED_PRODUCER_WIRE_LOWERBOUND_ONLY' if wire_error is None and latest is not None else 'UNKNOWN_OR_INCOMPLETE_LIVE_COUNTERS',nonce=NONCE,serial_path=str(SERIAL),prefix=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode(),complete_line_bytes=end,unparsed_incomplete_tail_bytes=len(tail),initial_file_size=a.st_size,final_file_size=b.st_size,prefix_cap_bytes=CAP,capped_before_initial_EOF=a.st_size>CAP,identity={k:getattr(a,k) for k in fields}),producer_reported_completed_launches=rounds*2 if latest is not None else None,producer_reported_mixed_work_ns=total if latest is not None else None,last_complete_progress=latest,pending_round_excluded=bool(pending),wire_error=wire_error,anchor_before=before_anchor,anchor_after=after_anchor,anchor_identity_consistent=before_anchor.get('same_identity') is True and after_anchor.get('same_identity') is True,owner_private_ledger_live='UNKNOWN; owner queue flush only after verified absence+mutexrelease',qualification='Progress is sourceproducer-reported and structuraltime/accounting checked only. Fullkerneltrace/publicshutdown/finalretirement/full strict paircheck remain terminal-only. No launch orwork credit from elapsedwall; partial/invalid record neverincrements lowerbound; these numbers are not acceptance.',full_check_long_session_invoked=False,application_acceptance=False,native_acceptance=False,signals=0,mutations=0)
if __name__=='__main__':
 result=None
 try:
  need(len(sys.argv)==3 and sys.argv[1].isdigit() and sys.argv[2].isdigit(),'rootprovided actual anchorPID and birth required')
  result=observe(int(sys.argv[1]),int(sys.argv[2]))
 except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:result=dict(scope=__doc__,status='UNKNOWN_LIVE_COUNTERS',error=type(exc).__name__+': '+str(exc),application_acceptance=False,native_acceptance=False,signals=0,mutations=0)
 print(json.dumps(result,sort_keys=True))
