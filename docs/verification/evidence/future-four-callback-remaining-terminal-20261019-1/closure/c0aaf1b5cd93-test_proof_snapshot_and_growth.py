from pathlib import Path
import hashlib,json,os,stat,tempfile,types
P=Path(__file__).resolve().parent;source_bytes=(P/'seed_remaining_image_work.py').read_bytes();m=types.ModuleType('actual_seed');exec(compile(source_bytes,str(P/'seed_remaining_image_work.py'),'exec'),m.__dict__);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();results=[]
for case in ['proof-mutates-during-copy','growing-source-before-write']:
 with tempfile.TemporaryDirectory(prefix='seed-proof-growth-',dir=P) as temp:
  root=Path(temp);source=root/'original';(source/'output/build').mkdir(parents=True);(source/'evidence').mkdir();m.SOURCE=source
  target=source/'output/build/a.bin';target.write_bytes(b'abc');receipt=source/'evidence/receipt.json';receipt.write_bytes(b'{"status":"FAIL"}')
  rows=[]
  for base,dirs,files in os.walk(source):
   for name in dirs+files:
    p=Path(base)/name;st=p.lstat();row={'relative':str(p.relative_to(source)),'metadata':m.metadata(st)}
    if stat.S_ISREG(st.st_mode):row['sha256']=h(p)
    rows.append(row)
  manifest=root/'manifest.json';manifest.write_text(json.dumps({'schema':'mckernel.future-four-callback-nine-phase-seed.v1','request_sha256':m.REQUEST_SHA,'source_root':str(source),'source_root_metadata':m.metadata(source.stat()),'entries':rows}))
  original={'retained_files':[{'path':str(target),'sha256':h(target),'bytes':3}],'failure_receipt':{'path':str(receipt),'sha256':h(receipt),'bytes':receipt.stat().st_size}}
  proof=root/'proof.json';proof.write_text(json.dumps(original));proof_hash=h(proof);dest=root/'fresh';dest.mkdir(mode=0o700);saved_read=os.read;injected=[False]
  def changed_read(fd,count):
   data=saved_read(fd,count)
   if not injected[0] and os.readlink('/proc/self/fd/'+str(fd))==str(target) and data:
    injected[0]=True
    if case=='proof-mutates-during-copy':proof.write_text(json.dumps({'retained_files':[],'failure_receipt':{'path':str(source/'evidence/UNVERIFIED')}}))
    else:return data+b'EXCEEDS_DECLARED_FILE_SIZE'
   return data
  os.read=changed_read
  try:
   if case=='proof-mutates-during-copy':
    result=m.seed_remaining_image_work(dest,manifest,h(manifest),proof,proof_hash)
    adopted=json.loads((dest/'remaining-phase-proof.json').read_text())
    assert injected[0] and h(proof)!=proof_hash and adopted['origin_proof_sha256']==proof_hash
    assert len(adopted['retained_files'])==1 and adopted['retained_files'][0]['path']=='/work/output/build/a.bin'
    assert adopted['failure_receipt']['path']=='/work/prior-evidence/receipt.json' and result['origin_proof_sha256']==proof_hash
   else:
    try:m.seed_remaining_image_work(dest,manifest,h(manifest),proof,proof_hash)
    except RuntimeError as exc:assert 'exceeds declared size before write' in str(exc)
    else:raise AssertionError('growing source accepted')
    assert injected[0] and (dest/'output/build/a.bin').stat().st_size==0
    journal=[json.loads(x) for x in (dest/'remaining-seed-journal.jsonl').read_text().splitlines()]
    assert journal[-1]['state']=='ENTRY_STARTED' and journal[-1]['source_relative']=='output/build/a.bin'
  finally:os.read=saved_read
  results.append(case)
print(json.dumps({'status':'PASS_SAME_PROOF_SNAPSHOT_AND_BOUNDED_GROWTH','affected_cases':len(results),'unverified_proof_rejected':True,'oversize_destination_bytes':0,'actual_failed_tree_copied':False,'compiler':False,'root':False}))
