from pathlib import Path
import hashlib,json,os,stat,tempfile,types
P=Path(__file__).resolve().parent
blob=(P/'seed_remaining_image_work.py').read_bytes();m=types.ModuleType('exact_seed');exec(compile(blob,str(P/'seed_remaining_image_work.py'),'exec'),m.__dict__)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='seed-interface-',dir=P) as temp:
 root=Path(temp);src=root/'original';src.mkdir(mode=0o700);m.SOURCE=src
 (src/'output/build').mkdir(parents=True);(src/'evidence').mkdir()
 cache=src/'output/build/CMakeCache.txt';cache.write_bytes(b'CMAKE_CACHEFILE_DIR:INTERNAL=/work/output/build\nCMAKE_HOME_DIRECTORY:INTERNAL=/src\n');os.utime(cache,ns=(1234567890000000000,1234567890000000000))
 (src/'evidence/receipt.json').write_text('{"status":"FAIL"}\n');os.symlink('CMakeCache.txt',src/'output/build/cache-link')
 proof=root/'proof.json';proof.write_text(json.dumps({'retained_files':[{'path':str(cache),'sha256':h(cache),'bytes':cache.stat().st_size}],'failure_receipt':{'path':str(src/'evidence/receipt.json'),'sha256':h(src/'evidence/receipt.json'),'bytes':(src/'evidence/receipt.json').stat().st_size}}))
 def manifest():
  rows=[]
  for base,dirs,files in os.walk(src,followlinks=False):
   for name in dirs+files:
    p=Path(base)/name;st=p.lstat();r={'relative':str(p.relative_to(src)),'metadata':m.metadata(st)}
    if stat.S_ISREG(st.st_mode):r['sha256']=h(p)
    if stat.S_ISLNK(st.st_mode):r['target']=os.readlink(p)
    rows.append(r)
  data={'schema':'mckernel.future-four-callback-nine-phase-seed.v1','request_sha256':m.REQUEST_SHA,'source_root':str(src),'source_root_metadata':m.metadata(src.stat()),'entries':rows}
  out=root/'manifest.json';out.write_text(json.dumps(data));return out
 mp=manifest();original={p:r['sha256'] for p,r in [(cache,{'sha256':h(cache)}),(src/'evidence/receipt.json',{'sha256':h(src/'evidence/receipt.json')})]}
 dest=root/'fresh';dest.mkdir(mode=0o700);result=m.seed_remaining_image_work(dest,mp,h(mp),proof,h(proof))
 assert result['status']=='SEEDED_EXACT_RETAINED_NINE_PHASES'
 assert (dest/'output/build/CMakeCache.txt').read_bytes()==cache.read_bytes()
 assert (dest/'output/build/CMakeCache.txt').stat().st_mtime_ns==cache.stat().st_mtime_ns
 assert os.readlink(dest/'output/build/cache-link')=='CMakeCache.txt'
 adopted=json.loads((dest/'remaining-phase-proof.json').read_text());assert adopted['source_root']=='/src' and adopted['output_root']=='/work/output' and adopted['failure_receipt']['path']=='/work/prior-evidence/receipt.json'
 assert all(h(p)==sha for p,sha in original.items());negative=0
 for label in ['nonempty-destination','unknown-source','changed-bytes']:
  d=root/label;d.mkdir(mode=0o700);mp=manifest();mh=h(mp)
  if label=='nonempty-destination':(d/'unexpected').write_bytes(b'x')
  elif label=='unknown-source':(src/'unexpected').write_bytes(b'x')
  else:cache.write_bytes(b'changed')
  try:m.seed_remaining_image_work(d,mp,mh,proof,h(proof))
  except RuntimeError:negative+=1
  else:raise AssertionError('seed boundary accepted '+label)
  if label=='unknown-source':(src/'unexpected').unlink()
 print(json.dumps({'status':'PASS_ACTUAL_CASE_SEED_INTERFACE','positive':1,'negative':negative,'original_bytes_preserved':True,'container_paths_preserved':True,'real_partial_build_seeded':False,'compiler':False,'root':False}))
# Exercise the actual owner.run body; every ownership/Docker effect is a stub.
import ast,builtins,uuid,time
ownerpath=P/'native_rust_exact_mckernel_image_container_owner_remaining.py'
tree=ast.parse(ownerpath.read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='ImageOwner');run_node=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='run')
with tempfile.TemporaryDirectory(prefix='owner-order-',dir=P) as temp:
 root=Path(temp);work=root/'work';work.mkdir();owner_evidence=root/'owner';owner_evidence.mkdir();events=[];records={};builtins._future4_fixture_events=events
 helper=root/'stub_seed.py';helper.write_text("import builtins\ndef seed_remaining_image_work(*args):\n builtins._future4_fixture_events.append('seed')\n return {'proof_sha256':'a'*64}\n")
 metadata_file=root/'metadata.json';metadata_file.write_text('{}')
 ref=lambda p:{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size}
 request={'common_exclusion_path':str(root/'common'),'candidate_sha':'942c927b1ec93cc31284ff498455909d9bb2d0fc','ihk_sha':'3114d9e7101ad52030eb3effa849a5c108972a1f','image_id':'image-pinned','jobs':4,'timeout':19800,'remaining_image_seed':{'helper':ref(helper),'manifest':ref(metadata_file),'retained_phase_proof':ref(metadata_file)}}
 class Shared:
  @staticmethod
  def acquire_heavy_operation(r,kind):events.append('shared');return root/'shared',{'nonce':'stub'}
  @staticmethod
  def _release_exclusion(path,row,receipt):
   assert receipt['status']=='FAIL';events.append('shared-retained')
 class Common:
  def __init__(self,*args):pass
  def acquire(self):events.append('common')
 class Lease:
  def __init__(self,*args):pass
  def acquire(self):events.append('lease')
  def release(self):events.append('lease-positive-retirement-release')
 class Docker:
  client_retirement_unproven=False
  def call(self,args,**kwargs):
   if args[:2]==['image','inspect']:return types.SimpleNamespace(stdout=json.dumps([{'Id':'image-pinned','Architecture':'amd64'}]),stderr='',returncode=0)
   if args[0]=='create':events.append('container-create');raise RuntimeError('FIXTURE_POST_SEED_CREATE_FAILURE')
   if args[0]=='logs':return types.SimpleNamespace(stdout='',stderr='',returncode=0)
   raise AssertionError('unexpected Docker effect '+str(args))
 def retire(*args):events.append('positive-retirement-stub');return {'State':{'Running':False}}
 host=types.SimpleNamespace(Lease=Lease,retire=retire)
 bound={'evidence':work/'evidence','output':work/'output','attempt':owner_evidence/'attempt','owner_evidence':owner_evidence,'host_owner':host,'lease':root/'lease','work':work,'source':root/'source','manifest':metadata_file,'toolchain':metadata_file,'driver':root/'driver','provenance':metadata_file,'gitlink_manifest':None,'toolchain_schema':'test.v2','mounts_by_target':{}}
 def save(path,value):records[str(path)]=value
 def fail(ok,message):
  if not ok:raise RuntimeError(message)
 globs={'_sha256':h,'os':os,'_SHARED_HEAVY_ENTRY_CONTRACT':Shared,'CommonExclusion':Common,'_revalidate_inputs':lambda *x:None,'_fsync_dir':lambda *x:None,'uuid':uuid,'RECEIPT_SCHEMA':'fixture-only','RESOURCE_ARGS':[],'_fail':fail,'Path':Path,'hashlib':hashlib,'json':json,'types':types,'time':time,'_exclusive_json':save,'_exclusive_text':lambda *x:None,'OWNER_RECEIPT_NAME':'owner-receipt.json'}
 exec(compile(ast.fix_missing_locations(ast.Module(body=[run_node],type_ignores=[])),str(ownerpath),'exec'),globs)
 class Owner:
  def __init__(self):self.request=request;self.docker=Docker();self.signals=None
  def validate(self):
   assert not any(work.iterdir());events.append('empty-work-admission');return bound
 Owner.run=globs['run'];result=Owner().run()
 assert events[:6]==['shared','empty-work-admission','common','lease','seed','container-create'],events
 assert result['status']=='FAIL' and result['retired'] is True and 'FIXTURE_POST_SEED_CREATE_FAILURE' in result['error']
 assert events[-1]=='shared-retained' and str(owner_evidence/'owner-receipt.json') in records
 assert 'remaining_image_seed' in result
 del builtins._future4_fixture_events
 print(json.dumps({'status':'PASS_ACTUAL_OWNER_RUN_ORDER_EFFECT_STUBS','actual_order':events[:6],'post_seed_failure_receipt_preserved':True,'shared_common_preserved':True,'real_owner_or_Docker_effects':False}))

# Exact owner body also retains partial-seed cleanup authority if seeding fails
# before Docker create. Original captures of the prior cases remain preserved.
with tempfile.TemporaryDirectory(prefix='partial-seed-failure-',dir=P) as temp:
 root=Path(temp);work=root/'work';work.mkdir();owner_evidence=root/'owner';owner_evidence.mkdir();events=[];records={};builtins._future4_fixture_events=events
 helper=root/'stub_seed.py';helper.write_text("import builtins\ndef seed_remaining_image_work(work,*args):\n builtins._future4_fixture_events.append('seed')\n (work/'partial-seed').write_bytes(b'partial')\n raise RuntimeError('FIXTURE_PARTIAL_SEED_FAILURE')\n")
 metadata_file=root/'metadata.json';metadata_file.write_text('{}')
 request={'common_exclusion_path':str(root/'common'),'candidate_sha':'942c927b1ec93cc31284ff498455909d9bb2d0fc','ihk_sha':'3114d9e7101ad52030eb3effa849a5c108972a1f','image_id':'image-pinned','jobs':4,'timeout':19800,'remaining_image_seed':{'helper':ref(helper),'manifest':ref(metadata_file),'retained_phase_proof':ref(metadata_file)}}
 bound={'evidence':work/'evidence','output':work/'output','attempt':owner_evidence/'attempt','owner_evidence':owner_evidence,'host_owner':host,'lease':root/'lease','work':work,'source':root/'source','manifest':metadata_file,'toolchain':metadata_file,'driver':root/'driver','provenance':metadata_file,'gitlink_manifest':None,'toolchain_schema':'test.v2','mounts_by_target':{}}
 result=Owner().run()
 assert result['status']=='FAIL' and result['retired'] is True and result['cleanup_separately_required'] is True
 assert result['remaining_image_seed_started'] is True and result['remaining_image_seed_inputs']==request['remaining_image_seed']
 assert (work/'partial-seed').read_bytes()==b'partial' and 'container-create' not in events and events[-1]=='shared-retained'
 assert str(owner_evidence/'owner-receipt.json') in records
 del builtins._future4_fixture_events
 print(json.dumps({'status':'PASS_ACTUAL_OWNER_PARTIAL_SEED_FAILURE_PRESERVATION','partial_bytes_and_receipt_preserved':True,'common_shared_retained':True,'cleanup_required':True,'real_owner_or_Docker_effects':False}))
