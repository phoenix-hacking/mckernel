from pathlib import Path
import copy,json,struct
p=Path('/home/holden/mckernel/scripts/tests/fixtures/stability-transport-fault/owner-published-hold-v1')
rows=[]
key=bytearray(80)
for off,v in [(0,11),(8,12),(16,13),(24,14),(32,3),(40,4096),(48,4136),(72,9)]:struct.pack_into('<Q',key,off,v)
for off,v in [(56,123),(60,1),(64,456),(68,2)]:struct.pack_into('<I',key,off,v)

def specimen(name,phase=1,mode=2):
 state={1:'initial',7:'selected',8:'held',2:'released',4:'released',3:'terminal',5:'recovery'}[phase]
 seq={'initial':0,'selected':1,'held':2,'released':3,'terminal':4,'recovery':4}[state]
 id=dict(os=2,pid=123,generation=9,nonce_low=0x0123456789abcdef,nonce_high=0xfedcba9876543210,mode=mode,
         sequence=seq,last_snapshot=0 if state=='initial' else 1 if state=='selected' else 3 if state in ('terminal','recovery') else 2,
         selected=state!='initial',held=state not in ('initial','selected'),released=state in ('released','terminal','recovery'),release_possible=state in ('held','released','terminal','recovery'),
         timer_seconds=35 if state not in ('initial','selected') else 0,held_ns=35700000000 if state not in ('initial','selected') else 0,
         terminal_ns=40100000000 if state=='terminal' else 0,barrier_calls=2 if state not in ('initial','selected') else 0,host_hold_calls=3 if state=='held' else 5 if state in ('released','terminal','recovery') else 0,
         key_hex=bytes(key).hex() if state!='initial' else bytes(80).hex(),capture_digest_hex=('1234567890abcdef'*4) if phase==8 else bytes(32).hex())
 req=bytearray(256)
 for off,v in [(0,2),(4,phase),(8,2),(12,123)]:struct.pack_into('<I',req,off,v)
 for off,v in [(16,9),(24,seq+1),(32,id['nonce_low']),(40,id['nonce_high']),(48,13 if seq else 0),(56,14 if seq else 0)]:struct.pack_into('<Q',req,off,v)
 if phase==8:
  struct.pack_into('<QQ',req,64,2,2);req[80:112]=bytes.fromhex('1234567890abcdef'*4)
 r=bytearray(req[:64])+bytearray(192);r[80:160]=key
 snapshot={1:1,7:2,8:2,2:3,4:3,3:4,5:4}[phase]
 stage=1 if phase==1 else 5 if phase==7 else 3
 end={1:120,7:35800000000,8:36100000000,2:40200000000,4:40200000000,3:45200000000,5:45200000000}[phase]
 for off,v in [(64,snapshot),(160,stage),(168,0 if phase==1 else 2),(176,40100000000 if phase in (2,3) else 0),(192,0 if phase==1 else 2),(200,seq+1),(208,0 if phase==1 else 35),(216,0 if phase==1 else 1),(224,0 if phase==1 else 35700000000),(232,0 if phase==1 else 3 if phase==7 else 5),(240,end-10),(248,end)]:struct.pack_into('<Q',r,off,v)
 collection=dict(open_result=7,open_errno=0,ioctl_result=0,ioctl_errno=0,raw_wait=0,ioctl_called=True,response_received=True,reaped=True,timed_out=False,begin_ns=end-20,end_ns=end+10)
 after=copy.deepcopy(id);after.update(key_hex=bytes(key).hex(),sequence=seq+1,selected=True,held=phase!=1,released=phase in (8,2,3,4,5),last_snapshot=snapshot,timer_seconds=0 if phase==1 else 35,held_ns=0 if phase==1 else 35700000000,barrier_calls=0 if phase==1 else 2,host_hold_calls=0 if phase==1 else 3 if phase==7 else 5,terminal_ns=40100000000 if phase in (2,3) else 0)
 if phase==7:after['release_possible']=False;id['release_possible']=False
 return dict(name=name,phase=phase,identity=id,request=req,reply=r,collection=collection,expected_result=0,expected_consumed=True,expected_after=after)

def add(x):
 assert x['name'] not in [r['name'] for r in rows]; rows.append(x)
def fail(x, consumed=True):
 x['expected_result']=-1;x['expected_consumed']=consumed;x['expected_after']=copy.deepcopy(x['identity'])
 if consumed:x['expected_after']['sequence']+=1
 return x

def field(x,off,value):struct.pack_into('<Q',x['reply'],off,value)
for name,phase,mode in [('valid-select',1,2),('valid-held-status',7,2),('valid-release-notify',8,2),('valid-release-recoverable',8,3),('valid-terminal',2,2),('valid-quiet',3,2),('valid-recovery',4,3),('valid-after-eight-shape-only',5,3)]:add(specimen(name,phase,mode))
for off in [0,4,8,12,16,24,32,40,48,56]:
 x=specimen('echo-mismatch-'+str(off),7);x['reply'][off]^=1;add(fail(x,False))
for name,off,val in [('snapshot',64,1),('stage',160,3),('accepted-sequence',168,1),('verification-error',184,1),('timer-absent',216,0),('timer-present-not-bool',216,2),('held-zero',224,0),('held-future',224,35800000001),('hold-overflow',232,1000001),('native-begin-before-call',240,35799999979),('native-end-before-begin',248,35799999989),('native-end-after-call',248,35800000011),('terminal-unexpected',176,100)]:
 x=specimen('held-'+name,7);field(x,off,val);add(fail(x))
for name,off,val in [('worker',88,17),('claim',104,18),('span',128,4137),('generation',152,10),('barrier',192,3),('timer',208,36),('held-time',224,35700000001),('holds-decrease',232,2)]:
 x=specimen('release-changed-'+name,8);field(x,off,val);add(fail(x))
for name,attr,value in [('missing-message','response_received',False),('unreaped','reaped',False),('late','timed_out',True),('no-ioctl','ioctl_called',False),('open-failed','open_result',-1),('open-errno','open_errno',5),('signal-raw','raw_wait',9),('exit137-raw','raw_wait',137<<8),('zero-begin','begin_ns',0)]:
 x=specimen(name,7);x['collection'][attr]=value;add(fail(x,False))
x=specimen('stale-consumption',7);field(x,200,1);add(fail(x,False))
x=specimen('future-request-sequence',7);struct.pack_into('<Q',x['request'],24,3);struct.pack_into('<Q',x['reply'],24,3);field(x,200,3);add(fail(x,False))
for phase in [1,7,8]:
 x=specimen('untouched-busy-phase-'+str(phase),phase);x['reply']=bytearray(x['request']);x['collection'].update(ioctl_result=-1,ioctl_errno=11)
 fail(x,False);x['expected_result']=-1 if phase==8 else 1;add(x)
x=specimen('ambiguous-copyout',8);x['reply']=bytearray(x['request']);x['collection'].update(ioctl_result=-1,ioctl_errno=14);add(fail(x,False))
x=specimen('consumed-pending-status',7)
for off,val in [(64,0),(72,(1<<64)-11),(160,2),(168,0),(208,0),(216,0),(224,0),(232,0)]:field(x,off,val)
x['collection'].update(ioctl_result=-1,ioctl_errno=11);fail(x);x['expected_result']=1;add(x)
x=specimen('consumed-release-error',8);field(x,64,0);field(x,72,(1<<64)-11);x['collection'].update(ioctl_result=-1,ioctl_errno=11);add(fail(x))
x=specimen('release-not-latched',8);x['identity']['release_possible']=False;add(fail(x))
x=specimen('duplicate-release',8);x['identity']['released']=True;add(fail(x))
x=specimen('notify-rejects-recovery',4,2);add(fail(x,False))
x=specimen('recovery-rejects-terminal',2,3);add(fail(x,False))
x=specimen('status-after-held',7);x['identity'].update(held=True,timer_seconds=35,held_ns=35700000000,barrier_calls=2,host_hold_calls=3);add(fail(x))
x=specimen('release-deadline-reached',8)
for off,val in [(240,39999999990),(248,40000000000)]:field(x,off,val)
x['collection'].update(begin_ns=39999999980,end_ns=40000000010);add(fail(x))
x=specimen('recovery-reserve-exactly-two-seconds',8,3)
for off,val in [(240,37999999990),(248,38000000000)]:field(x,off,val)
x['collection'].update(begin_ns=37999999980,end_ns=38000000010);add(fail(x))
x=specimen('quiet-before-five-seconds',3);field(x,240,45099999999);field(x,248,45100000000);x['collection'].update(begin_ns=45099999989,end_ns=45100000010);add(fail(x))
x=specimen('quiet-terminal-time-changed',3);field(x,176,40100000001);add(fail(x))
x=specimen('terminal-missing-time',2);field(x,176,0);add(fail(x))
x=specimen('timer-zero-with-present-is-valid',7);field(x,208,0);field(x,224,1000000000);field(x,240,1100000000);field(x,248,1100000010);x['collection'].update(begin_ns=1099999990,end_ns=1100000020);x['expected_after'].update(timer_seconds=0,held_ns=1000000000);add(x)
x=specimen('timer-deadline-overflow',7);field(x,208,(1<<64)-1);add(fail(x))

for off in [8,12,16,32,40,48,56]:
 x=specimen('joint-request-reply-identity-'+str(off),7);x['request'][off]^=1;x['reply'][off]^=1;add(fail(x,False))
for off in [64,72,80,112,255]:
 x=specimen('release-request-proof-'+str(off),8);x['request'][off]^=1;add(fail(x,False))
x=specimen('status-nonzero-request-tail',7);x['request'][255]=1;add(fail(x,False))

def arr(v):return '{'+','.join('0x%02x'%b for b in v)+'}'
def cval(v):return 'true' if v is True else 'false' if v is False else 'UINT64_C(%d)'%v if v>=0 else str(v)
def ident(d):
 return '{'+','.join('.'+k+'='+ (arr(bytes.fromhex(v)) if k.endswith('_hex') else cval(v)) for k,v in d.items()).replace('.key_hex=','.key=').replace('.capture_digest_hex=','.capture_digest=')+'}'
header='/* Independent literal metadata vectors. Generator/spec retained. */\nstatic const struct vector vectors[] = {\n'
for x in rows:
 header+=' {.name="'+x['name']+'",.phase='+str(x['phase'])+',.identity='+ident(x['identity'])+',.request='+arr(x['request'])+',.observation={.reply='+arr(x['reply'])+','+','.join('.'+k+'='+cval(v) for k,v in x['collection'].items())+'},.expected='+str(x['expected_result'])+',.consumed='+cval(x['expected_consumed'])+',.after='+ident(x['expected_after'])+'},\n'
header+='};\n'
(p/'metadata_vectors.h').write_text(header)
for x in rows:x['request_hex']=bytes(x.pop('request')).hex();x['reply_hex']=bytes(x.pop('reply')).hex()
(p/'metadata-expectations.json').write_text(json.dumps(dict(schema_version=1,scope='synthetic-client-metadata-only',case_count=len(rows),actual_ioctl_executed=False,cases=rows),indent=2)+'\n')
(p/'metadata-vector-generator.py').write_bytes(Path(__file__).read_bytes())
print('Prepared',len(rows),'independent literal metadata vectors; none executed')
