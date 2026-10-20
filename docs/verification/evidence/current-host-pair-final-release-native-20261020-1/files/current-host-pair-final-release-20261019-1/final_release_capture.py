"""Frozen offline second-stop/final-public-release oracle; grants no native credit."""
import hashlib,importlib.util,json
from pathlib import Path
MAX_SERIAL=4*1024*1024
PINS={
 'life':('/home/holden/mckernel/scripts/application-tests/native_diagnostic_lifecycle_capture.py','0585f78b80e603c010316418ce307794d59e1d92581b845ec6b2e74e22c8954b'),
 'cycle':('/home/holden/mckernel-work/scratch/native-resource-reboot-cycle-decoder-20261017-2/reboot_capture.py','eb9fa1106ec8caead27eaae37202c38bdae05c854cf61d533e89f86e18257cb5'),
 'resource':('/home/holden/mckernel-work/scratch/native-resource-release-collector-20261017-1/transport-correction1/resource_capture.py','e66e014f4b67854f05457770a42250fb5e0929e0da304bdbc2b7366b6bde9240'),
 'pool':('/home/holden/mckernel/scripts/application-tests/native_resource_release_capture.py','9c628074de9ae897e82f15c2f4438d2558c2a10fde6a0d5a288b8964eddfcc76')}
def need(value,label):
 if not value:raise ValueError(label)
def load(role):
 path,digest=PINS[role];p=Path(path);need(hashlib.sha256(p.read_bytes()).hexdigest()==digest,'frozen consumer identity')
 s=importlib.util.spec_from_file_location('final_release_'+role,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def pairs(items):
 d={}
 for key,value in items:
  need(key not in d,'duplicate JSON key');d[key]=value
 return d
def record(body):
 return json.loads(body,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
def evaluate(serial):
 need(type(serial)is str and len(serial.encode('utf-8'))<=MAX_SERIAL,'bounded UTF8 serial')
 cycle=load('cycle');life=load('life');resource=load('resource');pool=load('pool')
 first=cycle.evaluate(serial);life.validate_lifecycle_capture(serial)
 headers={};payload=[];final=[];positions={};final_positions=[];final_bytes=0
 allowed={'ND_FINAL_LIFECYCLE','ND_FINAL_LIFECYCLE_STREAM','ND_FINAL_RESOURCE','ND_FINAL_RESOURCE_STREAM','ND_FINAL_RESOURCE_CHUNK'}
 for index,line in enumerate(serial.splitlines(keepends=True)):
  if not line.startswith(('ND_FINAL','ND_LIFECYCLE ','ND_RESOURCE ','ND_REBOOT ','ND_PAYLOAD ')):continue
  need(line.endswith('\n'),'unterminated phase record')
  bare=line[:-2] if line.endswith('\r\n') else line[:-1]
  prefix,sep,body=bare.partition(' ');need(sep and '\r' not in bare,'phase framing')
  if prefix.startswith('ND_FINAL'):
   need(prefix in allowed,'unknown final phase');final.append((prefix,body));final_positions.append(index);final_bytes+=len(line.encode('utf-8'))
  if prefix in {'ND_LIFECYCLE','ND_RESOURCE','ND_REBOOT','ND_FINAL_LIFECYCLE','ND_FINAL_RESOURCE'}:
   need(prefix not in headers,'duplicate phase header');headers[prefix]=record(body);positions[prefix]=index
  if prefix=='ND_PAYLOAD':payload.append((index,bare,record(body)))
 need(len(payload)==1,'one unchanged payload')
 names=['ND_LIFECYCLE','ND_RESOURCE','ND_REBOOT','ND_FINAL_LIFECYCLE','ND_FINAL_RESOURCE']
 need(set(headers)==set(names),'all five phase headers')
 need([positions[n] for n in names]==sorted(positions[n] for n in names),'phase publication order')
 need(final_positions and max(final_positions)<payload[0][0] and final_bytes<=16384,'bounded final records before payload publication')
 need([p for p,_ in final[:4]]==['ND_FINAL_LIFECYCLE','ND_FINAL_LIFECYCLE_STREAM','ND_FINAL_LIFECYCLE_STREAM','ND_FINAL_RESOURCE'] and all(p in {'ND_FINAL_RESOURCE_STREAM','ND_FINAL_RESOURCE_CHUNK'} for p,_ in final[4:]),'final stop then release stream grouping')
 # Normalize ONLY the fixed new outer namespace; helper bytes remain exact.
 normalized=''.join(prefix.replace('ND_FINAL_','ND_',1)+' '+body+'\n' for prefix,body in final)+payload[0][1]+'\n'
 final_life=life.validate_lifecycle_capture(normalized)
 stdout,stderr,status=resource.decode(normalized);final_pool=pool.evaluate(stdout,stderr,status)
 stamps=[]
 for name in names:
  h=headers[name]
  for k in ('started_ns','reaped_ns','finished_ns'):
   need(type(h[k])is int and 0<h[k]<(1<<64),'phase timestamp')
  need(h['started_ns']<=h['reaped_ns']<=h['finished_ns'],'local phase order')
  stamps.append(h)
 need(type(payload[0][2]['reaped_ns'])is int and payload[0][2]['reaped_ns']<=stamps[0]['started_ns'],'payload before firststop')
 for before,after in zip(stamps,stamps[1:]):need(before['finished_ns']<after['started_ns'],'sameguest phase order')
 need(type(payload[0][2]['finished_ns'])is int and stamps[-1]['finished_ns']<=payload[0][2]['finished_ns'],'final release before collector finish')
 return {'status':'PASS_SECOND_STOP_AND_FINAL_PUBLIC_RELEASE_PROTOCOL_ONLY',
  'first_public_cycle':first,'first_subtrace_flags_scope':'unchanged first-release/reboot boundary, before final stop; not final whole-state flags','final_strict_stop':final_life,'final_public_pool':final_pool,
  'second_stop_verified':True,'final_public_release_verified':True,
  'native_execution_verified':False,'full_restoration_verified':False,
  'physical_generation_identity_verified':False,'second_application_launched':False,
  'repeat_quota_credit':False,'nonnull_FP_acceptance':False}
