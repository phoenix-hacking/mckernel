"""Fixed two-real-pair OS lifecycle protocol oracle. No runtime/restore/quota credit."""
import ast,copy,hashlib,importlib.util,json,re,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
ND=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-compatibility-20261019-1/n3-variant/native_diagnostic.py')
ND_SHA='8d29c650b74285d9d22435391059dfca7ae7605d0c1158a2a9cb850bd3aa0e20'
MANIFEST=Path('/home/holden/mckernel-work/scratch/cp205m-261019-1/manifest.json')
MANIFEST_SHA='4aa72c2a5a759bda71c4a0e8e33499068261346113ec2c9fd19d4669b3f8e41d'
def need(ok,label):
 if not ok:raise ValueError(label)
def pairs(rows):
 out={}
 for k,v in rows:need(k not in out,'duplicate JSON field');out[k]=v
 return out
def parse(raw):return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,'nonfinite JSON'))
def bound(path,pin,name):
 data=path.read_bytes();need(hashlib.sha256(data).hexdigest()==pin,'frozen '+name)
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class ExpectedGeneration(ast.NodeTransformer):
 """Only source-pinned expected generation literals; never rewrite observed bytes."""
 def __init__(self,value):self.value=value
 def visit_Constant(self,node):
  if type(node.value)is str and 'generation=1' in node.value:
   return ast.copy_location(ast.Constant(node.value.replace('generation=1','generation='+str(self.value))),node)
  return node
 def visit_Compare(self,node):
  node=self.generic_visit(node)
  if isinstance(node.left,ast.Subscript) and isinstance(node.left.slice,ast.Constant) and node.left.slice.value=='generation' and len(node.comparators)==1 and isinstance(node.comparators[0],ast.Constant) and node.comparators[0].value==1:
   node.comparators[0]=ast.Constant(self.value)
  return node
 def visit_Tuple(self,node):
  node=self.generic_visit(node)
  if len(node.elts)>=2 and all(isinstance(x,ast.Constant) for x in node.elts[:2]) and [x.value for x in node.elts[:2]]==['0','1']:node.elts[1]=ast.Constant(str(self.value))
  return node
def pair_checker(generation):
 need(type(generation)is int and 0<generation<2**64,'actual nonzero OS incarnation')
 m=bound(ND,ND_SHA,'strict_pair_base')
 tree=ast.parse(ND.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'_pair_trace','_pair_body'}];need(len(nodes)==2,'two existing pair consumers')
 adapted=ExpectedGeneration(generation).visit(ast.Module(body=nodes,type_ignores=[]));ast.fix_missing_locations(adapted);exec(compile(adapted,str(ND)+':expected-generation-only','exec'),m.__dict__)
 return m
def public_release_two(stdout,stderr,status):
 need(stderr==b'' and status==0,'resource helper exit')
 rows=[parse(x) for x in stdout.decode('ascii').splitlines()];kept=[];cpu2=[]
 for row in rows:
  (cpu2 if str(row.get('stage','')).startswith('cpu2_') else kept).append(row)
 need(len(cpu2)==8,'two exact CPU2online observations')
 for group,phase in zip((cpu2[:4],cpu2[4:]),('before','after')):
  need([x.get('stage') for x in group]==['cpu2_online_'+phase+'_release','cpu2_online_read','cpu2_online_value','cpu2_online_close'],'CPU2 read order')
  need(set(group[0])=={'stage','request','return','errno','linux_result'} and group[0]['request']==0 and group[0]['return']>=0 and group[0]['errno']==0 and group[1]['return']==2 and group[1]['errno']==0 and group[2]['value']==1 and group[3]['return']==0 and group[3]['errno']==0,'CPU2online actual result')
 # Original CPU1+MEM128->0 resource oracle consumes its unchanged original records.
 original=bound(Path('/home/holden/mckernel/scripts/application-tests/native_resource_release_capture.py'),'9c628074de9ae897e82f15c2f4438d2558c2a10fde6a0d5a288b8964eddfcc76','public_pool_original')
 raw=('\n'.join(json.dumps(x,separators=(',',':')) for x in kept)+'\n').encode()
 value=original.evaluate(raw,b'',0);return dict(public_pool=value,CPU2_online_before_and_after=True,physical_identity_verified=False)
def evaluate_protocol(serial):
 need(type(serial)is str and len(serial.encode('utf-8'))<=4*1024*1024,'serial UTF8 cap')
 bad_markers=bound(ND,ND_SHA,'cycle_original_bad_markers').BAD_MARKERS
 need(not bad_markers.search(serial),'kernel failure marker in whole serial')
 rows=[];pair_reports={};done=[]
 for line in serial.splitlines(keepends=True):
  if not line.startswith('ND_CYCLE'):continue
  need(line.endswith('\n'),'complete cycle record');wire=line[:-2] if line.endswith('\r\n') else line[:-1];need('\r' not in wire,'onlyterminalCR')
  prefix,sep,body=wire.partition(' ');need(sep,'cycle frame');obj=parse(body)
  if prefix in ('ND_CYCLE0_PAIR','ND_CYCLE1_PAIR'):
   index=int(prefix[len('ND_CYCLE')]);need(index not in pair_reports,'one realpair/cycle');pair_reports[index]=(len(rows),obj);rows.append((prefix,obj))
  elif prefix=='ND_CYCLES_DONE':done.append(obj);rows.append((prefix,obj))
  else:need(prefix in {'ND_CYCLE_IDENTITY','ND_CYCLE_CONTROL','ND_CYCLE_STREAM','ND_CYCLE_CHUNK'},'known cycle records');rows.append((prefix,obj))
 need(len(done)==1 and done[0]=={'completed':2,'good':True,'logger_seconds':120,'full_restoration_verified':False},'two complete finite cycles')
 need(set(pair_reports)=={0,1} and rows[-1][0]=='ND_CYCLES_DONE','two realpair reports')
 published=[]
 for prefix,value in rows[:-1]:
  index=int(prefix[len('ND_CYCLE')]) if prefix in ('ND_CYCLE0_PAIR','ND_CYCLE1_PAIR') else value.get('cycle')
  need(type(index)is int and index in (0,1),'only two fixed cycles');published.append(index)
 need(published==sorted(published),'stopfirstfailure cycle publication order')
 source=MANIFEST.read_bytes();need(hashlib.sha256(source).hexdigest()==MANIFEST_SHA,'frozen205manifest');manifest=parse(source);results=[];last_finish=0;generations=[];nonces=[]
 for index in (0,1):
  own=[(p,v) for p,v in rows if v.get('cycle')==index];ident=[v for p,v in own if p=='ND_CYCLE_IDENTITY'];need(len(ident)==1,'one authenticated cycle identity');identity=ident[0];g=identity['generation'];need(identity['os']==0 and type(identity['challenge'])is str and re.fullmatch('[0-9a-f]{32}',identity['challenge']) and int(identity['challenge'],16)>0,'source-owned fresh challenge')
  need(g not in generations and identity['challenge'] not in nonces,'fresh actual incarnation/challenge');generations.append(g);nonces.append(identity['challenge'])
  streams={};controls={};pos=0
  while pos<len(own):
   prefix,value=own[pos];pos+=1
   if prefix=='ND_CYCLE_CONTROL':
    kind=value['kind'];need(kind in {'boot','stop','release'} and kind not in controls,'unique helper kind');controls[kind]=value;continue
   need(prefix!='ND_CYCLE_CHUNK','unexpected/duplicate chunk')
   if prefix!='ND_CYCLE_STREAM':continue
   key=(value['kind'],value['name']);size=value['bytes'];need(key not in streams and type(size)is int and 0<=size<=262144,'unique bounded stream');out=bytearray()
   while len(out)<size:
    need(pos<len(own),'missing cycle chunk');cp,cv=own[pos];pos+=1;need(cp=='ND_CYCLE_CHUNK' and cv['cycle']==index and (cv['kind'],cv['name'])==key and cv['offset']==len(out) and type(cv['hex'])is str and re.fullmatch('(?:[0-9a-f]{2}){1,512}',cv['hex']),'ordered cycle bytes');chunk=bytes.fromhex(cv['hex']);need(len(chunk)==min(512,size-len(out)),'exact chunk bound');out.extend(chunk)
   streams[key]=bytes(out)
  need(set(controls)=={'boot','stop','release'} and set(streams)=={('pair','kernel_log'),('pair','assignment'),*[ (k,n) for k in ('boot','stop','release') for n in ('stdout','stderr')]},'complete control/trace streams')
  for kind in ('boot','stop','release'):
   h=controls[kind];need(all(type(h[k])is int for k in ('helper_rc','raw_wait_status','clean','fault','timeout','started_ns','reaped_ns','finished_ns','stdout_observed','stderr_observed','stdout_eof','stderr_eof')),'controlintegerfields');need((h['helper_rc'],h['raw_wait_status'],h['clean'],h['fault'],h['timeout'],h['stdout_eof'],h['stderr_eof'])==(0,0,1,0,0,1,1),'control success');need(0<h['started_ns']<=h['reaped_ns']<=h['finished_ns'],'helper time');need(h['stdout_observed']==len(streams[(kind,'stdout')])<=(4096 if kind=='release' else 1024) and h['stderr_observed']==len(streams[(kind,'stderr')])==0,'complete control accounting')
  proof=streams[('pair','assignment')];need(len(proof)==48,'full48Bassignment');magic,n0,n1,osid,count,actualg,cpu0,cpu1=struct.unpack('<QQQIIQii',proof);need(magic==0x3155504344524150 and (n0 or n1) and osid==0 and count==2 and actualg==g and (cpu0,cpu1)==(1,2) and ('%016x%016x'%(n0,n1))==identity['challenge'],'whole fresh proof/identity/CPU join')
  report=pair_reports[index][1];trace=streams[('pair','kernel_log')].decode('utf-8');need(not bad_markers.search(trace),'kernel failure marker in decoded cycle trace');need(len(streams[('pair','kernel_log')])==identity['fresh_log_bytes'],'trace bytecount')
  expected=copy.deepcopy(manifest)
  for i,a in enumerate(expected['pair']['apps']):a['cwd']='/case/cycle%d/two-app/work%d'%(index,i)
  serial_one=trace+'\nND_PAIR '+json.dumps(report,separators=(',',':'))+'\n';checked=pair_checker(g)._pair_body(expected,{'serial':serial_one})
  apps=report['apps'];need(last_finish<controls['boot']['started_ns']<=controls['boot']['finished_ns']<min(a['started_ns'] for a in apps) and max(a['finished_ns'] for a in apps)<controls['stop']['started_ns']<=controls['stop']['finished_ns']<controls['release']['started_ns'],'full lifecycle order')
  life=bound(Path('/home/holden/mckernel/scripts/application-tests/native_diagnostic_lifecycle_capture.py'),'0585f78b80e603c010316418ce307794d59e1d92581b845ec6b2e74e22c8954b','strict_stop_original');life._probe(streams[('stop','stdout')]);pool=public_release_two(streams[('release','stdout')],b'',0)
  last_finish=controls['release']['finished_ns'];results.append(dict(pair=checked['guest_report'],public_release=pool,generation_observed=g,challenge=identity['challenge']))
 return dict(status='PASS_TWO_REAL_PAIR_LIFECYCLE_PROTOCOLS_ONLY',cycles=results,real_pair_reports=2,payload_launches=4,logger_seconds=120,native_execution_verified=False,physical_frame_identity_verified=False,full_generation_restoration_verified=False,repeat_quota_credit=False,nonnull_FP_acceptance=False)
