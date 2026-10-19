from pathlib import Path
import ast,builtins,hashlib,json,os,stat,tempfile,time,types,uuid
P=Path(__file__).resolve().parent
blob=(P/'seed_remaining_image_work.py').read_bytes();m=types.ModuleType('exact_seed');exec(compile(blob,str(P/'seed_remaining_image_work.py'),'exec'),m.__dict__)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='actual-partial-seed-',dir=P) as temp:
 root=Path(temp);source=root/'original';(source/'output/build').mkdir(parents=True);(source/'evidence').mkdir();m.SOURCE=source
 (source/'output/build/a.bin').write_bytes(b'preserve first completed bytes');(source/'output/build/z.bin').write_bytes(b'inject before this file opens');(source/'evidence/receipt.json').write_bytes(b'{"status":"FAIL"}')
 rows=[]
 for base,dirs,files in os.walk(source):
  for name in dirs+files:
   p=Path(base)/name;st=p.lstat();row={'relative':str(p.relative_to(source)),'metadata':m.metadata(st)}
   if stat.S_ISREG(st.st_mode):row['sha256']=h(p)
   rows.append(row)
 manifest=root/'manifest.json';manifest.write_text(json.dumps({'schema':'mckernel.future-four-callback-nine-phase-seed.v1','request_sha256':m.REQUEST_SHA,'source_root':str(source),'source_root_metadata':m.metadata(source.stat()),'entries':rows}))
 proof=root/'proof.json';proof.write_text('{}');work=root/'fresh';work.mkdir(mode=0o700);original={r['relative']:r.get('sha256') for r in rows if 'sha256' in r}
 saved_open=os.open
 def fail_second(path,flags,*args,**kwargs):
  if path=='z.bin' and kwargs.get('dir_fd') is not None:raise OSError('FIXTURE_SEED_SECOND_FILE_OPEN_FAILURE')
  return saved_open(path,flags,*args,**kwargs)
 os.open=fail_second
 try:
  try:m.seed_remaining_image_work(work,manifest,h(manifest),proof,h(proof))
  except OSError as exc:assert 'FIXTURE_SEED_SECOND_FILE_OPEN_FAILURE' in str(exc)
  else:raise AssertionError('injected partial seed did not fail')
 finally:os.open=saved_open
 journal=[json.loads(x) for x in (work/'remaining-seed-journal.jsonl').read_text().splitlines()]
 assert journal[0]['state']=='BEGIN' and journal[-1]['state']=='ENTRY_STARTED' and journal[-1]['source_relative']=='output/build/z.bin'
 assert any(x['state']=='ENTRY_COMMITTED' and x.get('source_relative')=='output/build/a.bin' for x in journal)
 assert (work/'output/build/a.bin').read_bytes()==(source/'output/build/a.bin').read_bytes() and not (work/'output/build/z.bin').exists()
 assert all(h(source/rel)==sha for rel,sha in original.items())
 print(json.dumps({'status':'PASS_ACTUAL_SEED_PARTIAL_FAILURE_JOURNAL','completed_prefix_preserved':True,'incomplete_entry_explicit':True,'original_bytes_preserved':True,'actual_failed_build_copied':False}))
# Actual ImageOwner.run body with ownership and Docker effects stubbed.
ownerpath=P/'native_rust_exact_mckernel_image_container_owner_remaining.py';tree=ast.parse(ownerpath.read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='ImageOwner');node=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='run')
with tempfile.TemporaryDirectory(prefix='actual-owner-partial-',dir=P) as temp:
 root=Path(temp);work=root/'work';work.mkdir();owner_evidence=root/'owner';owner_evidence.mkdir();events=[];records={};builtins._future4_fixture_events=events
 helper=root/'stub_seed.py';helper.write_text("import builtins\ndef seed_remaining_image_work(work,*args):\n builtins._future4_fixture_events.append('seed')\n (work/'partial-seed').write_bytes(b'partial')\n (work/'remaining-seed-journal.jsonl').write_text('{\\\"state\\\":\\\"ENTRY_STARTED\\\"}\\n')\n raise RuntimeError('FIXTURE_PARTIAL_SEED_FAILURE')\n")
 metadata_file=root/'metadata.json';metadata_file.write_text('{}');ref=lambda p:{'path':str(p),'sha256':h(p),'bytes':p.stat().st_size}
 request={'common_exclusion_path':str(root/'common'),'candidate_sha':'942c927b1ec93cc31284ff498455909d9bb2d0fc','ihk_sha':'3114d9e7101ad52030eb3effa849a5c108972a1f','image_id':'image-pinned','jobs':4,'timeout':19800,'remaining_image_seed':{'helper':ref(helper),'manifest':ref(metadata_file),'retained_phase_proof':ref(metadata_file)}}
 class Shared:
  @staticmethod
  def acquire_heavy_operation(*args):events.append('shared');return root/'shared',{'nonce':'stub'}
  @staticmethod
  def _release_exclusion(path,row,receipt):assert receipt['status']=='FAIL';events.append('shared-retained')
 class Common:
  def __init__(self,*args):pass
  def acquire(self):events.append('common')
 class Lease:
  def __init__(self,*args):pass
  def acquire(self):events.append('lease')
  def release(self):events.append('positive-no-container-lease-release')
 class Docker:
  def call(self,*args,**kwargs):raise AssertionError('Docker reached after seed failure')
 host=types.SimpleNamespace(Lease=Lease)
 bound={'evidence':work/'evidence','output':work/'output','attempt':owner_evidence/'attempt','owner_evidence':owner_evidence,'host_owner':host,'lease':root/'lease','work':work}
 def fail(ok,message):
  if not ok:raise RuntimeError(message)
 def save(path,value):records[str(path)]=value
 globs={'_sha256':h,'_SHARED_HEAVY_ENTRY_CONTRACT':Shared,'CommonExclusion':Common,'_revalidate_inputs':lambda *x:None,'_fsync_dir':lambda *x:None,'uuid':uuid,'RECEIPT_SCHEMA':'fixture-only','_fail':fail,'Path':Path,'hashlib':hashlib,'json':json,'time':time,'_exclusive_json':save,'OWNER_RECEIPT_NAME':'owner-receipt.json'}
 exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(ownerpath),'exec'),globs)
 class Owner:
  def __init__(self):self.request=request;self.docker=Docker();self.signals=None
  def validate(self):assert not any(work.iterdir());events.append('empty-work-admission');return bound
 Owner.run=globs['run'];result=Owner().run()
 assert events[:5]==['shared','empty-work-admission','common','lease','seed'],events
 assert result['status']=='FAIL' and result['retired'] is True and result['cleanup_separately_required'] is True
 assert 'FIXTURE_PARTIAL_SEED_FAILURE' in result['error'] and result['remaining_image_seed_inputs']==request['remaining_image_seed']
 assert result['remaining_image_seed_journal']==str(work/'remaining-seed-journal.jsonl') and (work/'partial-seed').read_bytes()==b'partial'
 assert (work/'remaining-seed-journal.jsonl').is_file() and events[-1]=='shared-retained' and str(owner_evidence/'owner-receipt.json') in records
 del builtins._future4_fixture_events
 print(json.dumps({'status':'PASS_ACTUAL_OWNER_PARTIAL_SEED_FAILURE','cleanup_required':True,'receipt_and_partial_journal_preserved':True,'shared_common_retained':True,'actual_owner_or_Docker_effects':False}))
