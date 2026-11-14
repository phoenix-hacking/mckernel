"""Bounded ordinary source/body/parser checks; never invokes PID1, ioctls or guests."""
import hashlib,importlib.util,json,os,resource,subprocess,time
from pathlib import Path
Q=Path(__file__).resolve().parent;OUT=Q/'ordinary-check-1';START=time.monotonic()
def need(ok,label):
 if not ok:raise AssertionError(label)
def sha(data):return hashlib.sha256(data).hexdigest()
def put(name,value):
 with (OUT/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
need(os.getuid()==1000 and os.sched_getaffinity(0)=={7},'UID/CPU7');need(0<resource.getrlimit(resource.RLIMIT_AS)[0]<=1073741824,'AS1GiB');need(0<resource.getrlimit(resource.RLIMIT_CPU)[0]<=30,'CPU30')
for r in json.loads((Q/'ORDINARY-INPUT-PINS.json').read_bytes()):
 b=Path(r['path']).read_bytes();need(len(b)==r['bytes'] and sha(b)==r['sha256'],'frozen input '+r['path'])
OUT.mkdir(mode=0o700)
def run(label,argv,expected=0):
 remaining=28-(time.monotonic()-START);need(remaining>0,'shared work28s')
 with (OUT/(label+'.stdout')).open('xb') as out,(OUT/(label+'.stderr')).open('xb') as err:
  begin=time.monotonic();p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,close_fds=True)
  try:rc=p.wait(timeout=remaining)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,15)
   try:p.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait(timeout=1)
   put(label+'.status.json',dict(argv=argv,returncode=p.returncode,direct_join=True,timed_out=True));raise
 put(label+'.status.json',dict(argv=argv,pid=p.pid,returncode=rc,direct_join=True,seconds=time.monotonic()-begin,streams_closed=True))
 try:os.killpg(p.pid,0)
 except ProcessLookupError:pass
 else:raise AssertionError('owned group remains')
 need(rc==expected and (OUT/(label+'.stderr')).stat().st_size==0,'expected clean child '+label)
 return (OUT/(label+'.stdout')).read_bytes()
common=['/usr/bin/gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static','-fno-pie','-no-pie','-Wl,-z,noexecstack']
header='/home/holden/mckernel-work/scratch/native-lifecycle-probe-source-20261017-1/compiled-3/include'
boot=json.loads((Q/'FROZEN-BOOT-COMPILE-ARGV.json').read_bytes());run('compile-boot',boot)
run('compile-collector',common+['-DND_CORE_THREADS',str(Q/'candidate/collector-two-complete-cycles.c'),'-o',str(OUT/'collector')])
run('compile-resource',common+['-I',header,str(Q/'candidate/native-resource-release-two.c'),'-o',str(OUT/'resource-two')])
run('compile-resource-body',common+['-I',header,str(Q/'fixtures/resource-two-body.c'),'-o',str(OUT/'resource-body')])
run('compile-cycle-body',common+['-DND_CORE_THREADS',str(Q/'fixtures/cycle-body.c'),'-o',str(OUT/'cycle-body')])
(OUT/'admission.txt').write_text('0 -16 -16\n')
spec=importlib.util.spec_from_file_location('cycle_oracle',Q/'cycle_oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
pool=run('resource-positive',[str(OUT/'resource-body'),'0',str(OUT/'admission.txt')]);oracle.public_release_two(pool,b'',0)
for scenario in (9,10):
 data=run('resource-refusal-'+str(scenario),[str(OUT/'resource-body'),str(scenario),str(OUT/'admission.txt')],1)
 try:oracle.public_release_two(data,b'',1)
 except ValueError:pass
 else:raise AssertionError('CPU2 failure accepted')
# Use retained exact successful first-stop bytes strictly as model input.
old=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-repeatability-20261019-1/readback-2.stdout');saved=json.loads(old.read_bytes())['observation']['serial'];life=None
for line in saved.splitlines():
 if line.startswith('ND_LIFECYCLE_STREAM '):
  v=json.loads(line.partition(' ')[2])
  if v['name']=='stdout':life=bytes.fromhex(v['capture']['hex'])
need(life is not None,'saved strict5stop bytes');(OUT/'life.stdout').write_bytes(life);(OUT/'pool.stdout').write_bytes(pool)
body_bytes=run('actual-cycle-body',[str(OUT/'cycle-body'),str(OUT/'life.stdout'),str(OUT/'pool.stdout')]);body_lines=body_bytes.decode().splitlines();need(len(body_lines)==2 and body_lines[1].startswith('ND_CYCLE0_PAIR '),'actual C pair serializer output');body=json.loads(body_lines[0]);actual_writer=json.loads(body_lines[1].partition(' ')[2]);need(actual_writer['generation']==41 and [len(bytes.fromhex(a['streams']['stdout']['hex'])) for a in actual_writer['apps']]==[387,254],'actual C serializers exact app bytes')
need(body['positive']==1 and body['refusals']==8 and body['prefix_vectors']==3,'actual C gates')
# New expected-generation specialization preserves the accepted generation1 body.
semantic=json.loads(Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-compatibility-independent-review-20261019-1/ACTUAL-205-TWO-CPU-AND-RUST-PAIR-NATIVE-DIAGNOSTIC-REVIEW.json').read_bytes());r=semantic['actual_result_json'];raw=Path(r['path']).read_bytes();need(len(raw)==r['bytes'] and sha(raw)==r['sha256'],'authentic closed205result');observation=json.loads(raw)['observation'];manifest=json.loads(oracle.MANIFEST.read_bytes());original=oracle.bound(oracle.ND,oracle.ND_SHA,'original_generation1');baseline=original._pair_body(manifest,observation);same=oracle.pair_checker(1)._pair_body(manifest,observation);need(baseline['guest_report']==same['guest_report'],'generation1 exact body equivalence')
# A synthetic source-contract generation is explicit fixture data, never runtime credit.
import copy,struct
synthetic=copy.deepcopy(observation);synthetic['serial']=synthetic['serial'].replace('generation=1 ','generation=41 ')
for line in synthetic['serial'].splitlines(keepends=True):
 if line.startswith('ND_PAIR '):
  v=json.loads(line.partition(' ')[2]);v['generation']=41;synthetic['serial']=synthetic['serial'].replace(line,'ND_PAIR '+json.dumps(v,separators=(',',':'))+'\n');break
oracle.pair_checker(41)._pair_body(manifest,synthetic)
try:oracle.pair_checker(79)._pair_body(manifest,synthetic)
except Exception:pass
else:raise AssertionError('wrong generation accepted')

# Explicitly modeled two-complete-cycle stream; original capture is immutable.
def encoded(index,kind,name,data):
 out=['ND_CYCLE_STREAM '+json.dumps(dict(cycle=index,kind=kind,name=name,bytes=len(data)),separators=(',',':'))+'\n']
 for at in range(0,len(data),512):out.append('ND_CYCLE_CHUNK '+json.dumps(dict(cycle=index,kind=kind,name=name,offset=at,hex=data[at:at+512].hex()),separators=(',',':'))+'\n')
 return ''.join(out)
def control(index,kind,start,finish,stdout):
 h=dict(cycle=index,kind=kind,helper_rc=0,raw_wait_status=0,clean=1,fault=0,timeout=0,started_ns=start,reaped_ns=finish-1,finished_ns=finish,stdout_observed=len(stdout),stderr_observed=0,stdout_eof=1,stderr_eof=1)
 return 'ND_CYCLE_CONTROL '+json.dumps(h,separators=(',',':'))+'\n'+encoded(index,kind,'stdout',stdout)+encoded(index,kind,'stderr',b'')
original_report=baseline['guest_report'];trace='\n'.join(x for x in observation['serial'].splitlines() if not x.startswith('ND_PAIR '))+'\n';modeled=[]
for index,generation in enumerate((41,79)):
 report=copy.deepcopy(original_report);report['generation']=generation;shift=index*10**12
 for i,a in enumerate(report['apps']):
  a['cwd']='/case/cycle%d/two-app/work%d'%(index,i)
  for key in ('started_ns','reaped_ns','finished_ns'):a[key]+=shift
  for stream in a['streams'].values():stream['eof_ns']+=shift
 start=min(a['started_ns'] for a in report['apps']);end=max(a['finished_ns'] for a in report['apps']);fresh=trace.replace('generation=1 ','generation='+str(generation)+' ').encode()
 modeled.append(control(index,'boot',start-100,start-10,b''));identity=dict(cycle=index,os=0,generation=generation,challenge=('%032x'%(index+11)),prior_log_bytes=6,fresh_log_bytes=len(fresh));modeled.append('ND_CYCLE_IDENTITY '+json.dumps(identity,separators=(',',':'))+'\n');modeled.append(encoded(index,'pair','assignment',struct.pack('<QQQIIQii',0x3155504344524150,0,index+11,0,2,generation,1,2)));modeled.append(encoded(index,'pair','kernel_log',fresh));modeled.append('ND_CYCLE%d_PAIR '%index+json.dumps(report,separators=(',',':'))+'\n');modeled.append(control(index,'stop',end+10,end+20,life));modeled.append(control(index,'release',end+30,end+40,pool))
modeled=''.join(modeled)+'ND_CYCLES_DONE '+json.dumps(dict(completed=2,good=True,logger_seconds=120,full_restoration_verified=False),separators=(',',':'))+'\n';(OUT/'MODELED-two-cycles.serial').write_text(modeled)
full=oracle.evaluate_protocol(modeled);need(full['payload_launches']==4 and not full['native_execution_verified'],'scoped full model')
refusals=0
def refuse(text):
 global refusals
 try:oracle.evaluate_protocol(text)
 except Exception:refusals+=1;return
 raise AssertionError('invalid full model accepted')
refuse(modeled.replace('ND_CYCLE1_PAIR ','ND_CYCLE9_PAIR ',1));refuse(modeled[:modeled.index('ND_CYCLE1_PAIR ')]);refuse(modeled.replace('"generation":79','"generation":41',1));refuse(modeled.replace('"completed":2','"completed":1'));refuse(modeled.replace('"good":true','"good":false'));refuse(modeled.replace('"helper_rc":0','"helper_rc":1',1));refuse(modeled.replace('"challenge":"0000000000000000000000000000000c"','"challenge":"0000000000000000000000000000000b"'));refuse(modeled.replace('"cycle":1,"kind":"boot"','"cycle":0,"kind":"boot"',1))

def bad_assignment(index,field,value):
 lines=modeled.splitlines(keepends=True)
 for at,line in enumerate(lines):
  if line.startswith('ND_CYCLE_CHUNK '):
   row=json.loads(line.partition(' ')[2])
   if row['cycle']==index and row['kind']=='pair' and row['name']=='assignment':
    wire=list(struct.unpack('<QQQIIQii',bytes.fromhex(row['hex'])));wire[field]=value;row['hex']=struct.pack('<QQQIIQii',*wire).hex();lines[at]='ND_CYCLE_CHUNK '+json.dumps(row,separators=(',',':'))+'\n';return ''.join(lines)
 raise AssertionError('assignment vector unreachable')
refuse(bad_assignment(1,5,41));refuse(bad_assignment(1,1,17));refuse(bad_assignment(0,4,3));refuse(bad_assignment(0,7,1));refuse(modeled.replace('"cwd":"/case/cycle0/two-app/work0"','"cwd":"/case/cycle1/two-app/work0"',1))
result=dict(status='PASS_TWO_COMPLETE_CYCLE_SOURCE_AND_PARTIAL_MODEL_ONLY',actual_C_body=body,CPU2_inventory_positive=1,CPU2_inventory_refusals=2,generation1_equivalence=True,synthetic_generation_context_positive=1,wrong_generation_refused=True,full_two_cycle_protocol_fixture=True,full_model_refusals=refusals,native_cycles=0,real_launches=0,full_restoration_verified=False,seconds=time.monotonic()-START)
put('result.json',result);print(json.dumps({k:result[k] for k in ['status','CPU2_inventory_positive','CPU2_inventory_refusals','full_two_cycle_protocol_fixture','native_cycles']}))
