"""Offline actual-C body and explicitly synthetic final-phase composition; no native credit."""
import hashlib,importlib.util,json,os,resource,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
START=time.monotonic()
def need(ok,label):
 if not ok:raise AssertionError(label)
def ref(path):
 p=Path(path);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def write(name,body):
 with (HERE/name).open('xb') as f:f.write(body)
def dump(name,value):write(name,(json.dumps(value,sort_keys=True)+'\n').encode())
need(os.sched_getaffinity(0)=={7},'exact CPU7 allocation')
need(resource.getrlimit(resource.RLIMIT_AS)[0]<=1073741824 and resource.getrlimit(resource.RLIMIT_CPU)[0]<=30,'outer AS/CPU caps')
for pin in json.loads((HERE/'OFFLINE-INPUT-PINS.json').read_bytes()):need(ref(pin['path'])==pin,'full frozen input')
plan=json.loads((HERE/'OFFLINE-CHECK-PROPOSAL.json').read_bytes())
for name in plan['fresh_outputs']:
 need(not Path(name).exists(),'fresh output '+name)
def run(label,argv):
 remaining=28-(time.monotonic()-START);need(remaining>0,'shared work budget')
 with (HERE/(label+'.stdout')).open('xb') as out,(HERE/(label+'.stderr')).open('xb') as err:
  begin=time.monotonic();p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,close_fds=True)
  try:rc=p.wait(timeout=remaining)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,15)
   try:rc=p.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(p.pid,9);rc=p.wait(timeout=1)
   dump(label+'.status.json',{'argv':argv,'pid':p.pid,'returncode':rc,'direct_join':True,'timed_out':True});raise
  status={'argv':argv,'pid':p.pid,'returncode':rc,'direct_join':True,'seconds':time.monotonic()-begin}
 dump(label+'.status.json',status)
 try:os.killpg(p.pid,0)
 except ProcessLookupError:pass
 else:raise AssertionError('child group remains')
 need(rc==0 and (HERE/(label+'.stderr')).stat().st_size==0,'clean '+label)
flags=['/usr/bin/gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static','-fno-pie','-no-pie','-Wl,-z,noexecstack','-DND_CORE_THREADS']
run('compile-collector',flags+[str(HERE/'collector-typed-avx-final-release.c'),'-o',str(HERE/'collector-final-release')])
run('compile-body',flags+[str(HERE/'final-phase-body-harness.c'),'-o',str(HERE/'final-phase-body-harness')])
spec=importlib.util.spec_from_file_location('final_oracle',HERE/'final_release_capture.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
old=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-repeatability-20261019-1')
serial=json.loads((old/'readback-2.stdout').read_bytes())['observation']['serial']
resource_decoder=oracle.load('resource');poolout,poolerr,poolstatus=resource_decoder.decode(serial)
need(poolerr==b'' and poolstatus==0,'authentic successful pool input')
lifeout=None;reboot=None
for line in serial.splitlines():
 if line.startswith('ND_LIFECYCLE_STREAM '):
  value=json.loads(line.partition(' ')[2])
  if value['name']=='stdout':lifeout=bytes.fromhex(value['capture']['hex'])
 if line.startswith('ND_REBOOT '):reboot=json.loads(line.partition(' ')[2])
need(lifeout is not None and reboot is not None,'authentic phase input')
write('fixture-lifecycle.stdout',lifeout);write('fixture-pool.stdout',poolout)
base=reboot['finished_ns']+1000
run('actual-body',[str(HERE/'final-phase-body-harness'),str(old/'admission-vector-0.raw'),str(HERE/'fixture-lifecycle.stdout'),str(HERE/'fixture-pool.stdout'),str(base)])
body=(HERE/'actual-body.stdout').read_text();baseline,rest=body.split('FIRST_BEGIN\n',1);first,final=rest.split('FINAL_BEGIN\n',1)
need(baseline.removeprefix('BASELINE_BEGIN\n')==first,'unchanged phase0 exact serializer bytes')
need(final.endswith('END\n'),'complete actual serializer');final=final[:-4]
lines=serial.splitlines(keepends=True);payload_indices=[i for i,x in enumerate(lines) if x.startswith('ND_PAYLOAD ')]
need(len(payload_indices)==1,'one saved payload');index=payload_indices[0]
# MODELED ONLY: extend collector finish time; original retained capture is never written.
payload=json.loads(lines[index].partition(' ')[2]);payload['finished_ns']=base+5000
modeled=''.join(lines[:index])+final+'ND_PAYLOAD '+json.dumps(payload,separators=(',',':'))+'\n'+''.join(lines[index+1:])
write('MODELED-final-release.serial',modeled.encode())
positive=[];negative=[]
def passed(name,text):
 value=oracle.evaluate(text);need(value['second_stop_verified'] and value['final_public_release_verified'] and not value['native_execution_verified'],'scoped result');positive.append(name);return value
def refused(name,text):
 try:oracle.evaluate(text)
 except (ValueError,AssertionError,KeyError):negative.append(name);return
 raise AssertionError('accepted invalid '+name)
result=passed('actual-C-final-serialization-modeled-composition',modeled)
passed('console-equivalent-CRLF',modeled.replace('\r\n','\n').replace('\n','\r\n'))
refused('authentic-first-iteration-has-no-final-phase',serial)
rows=modeled.splitlines(keepends=True)
def mutate(prefix,key,value):
 changed=list(rows)
 for i,line in enumerate(changed):
  if line.startswith(prefix+' '):
   row=json.loads(line.partition(' ')[2]);row[key]=value;changed[i]=prefix+' '+json.dumps(row,separators=(',',':'))+'\n';return ''.join(changed)
 raise AssertionError('missing mutation target')
header=next(x for x in rows if x.startswith('ND_FINAL_LIFECYCLE '))
refused('duplicate-final-stop',modeled.replace(header,header+header))
refused('missing-final-stop',modeled.replace(header,''))
refused('nonzero-final-stop',mutate('ND_FINAL_LIFECYCLE','raw_wait_status',1))
refused('final-stop-before-reboot',mutate('ND_FINAL_LIFECYCLE','started_ns',1))
refused('release-before-final-stop',mutate('ND_FINAL_RESOURCE','started_ns',base+500))
refused('unknown-final-phase',modeled.replace('ND_FINAL_LIFECYCLE ', 'ND_FINAL_UNKNOWN ',1))
refused('truncated-final-capture',modeled[:modeled.index('ND_FINAL_RESOURCE_STREAM ')])
changed=list(rows);found=False
for i,line in enumerate(changed):
 if line.startswith('ND_FINAL_RESOURCE_CHUNK '):
  value=json.loads(line.partition(' ')[2]);raw=bytes.fromhex(value['hex'])
  if b'"bytes":0' in raw:
   value['hex']=raw.replace(b'"bytes":0',b'"bytes":1',1).hex();changed[i]='ND_FINAL_RESOURCE_CHUNK '+json.dumps(value,separators=(',',':'))+'\n';found=True;break
need(found,'inventory-zero negative reachable');refused('false-final-public-memory-inventory',''.join(changed))
result={'status':'PASS_OFFLINE_FINAL_STOP_AND_PUBLIC_RELEASE_COMPOSITION_ONLY','positive':len(positive),'refusals':len(negative),'actual_C_gate_scenarios':9,'first_phase_serialization_byteidentical':True,'positive_names':positive,'refusal_names':negative,'modeled_oracle_result':result,'native_cycles':0,'full_restoration_verified':False,'future_queue_predecessor':None,'total_seconds':time.monotonic()-START}
dump('offline-result.json',result);print(json.dumps({k:result[k] for k in ('status','positive','refusals','actual_C_gate_scenarios')}))
