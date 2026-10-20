"""Validate retained archive + complete actual M03 document. Never recompress."""
from pathlib import Path
import copy,gzip,hashlib,importlib.util,json,os,stat
D=Path(__file__).resolve().parent
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def read(r):
 p=Path(r['path']);fd=os.open(p,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as f:
  a=os.fstat(f.fileno());data=f.read(96<<20);b=os.fstat(f.fileno());c=p.lstat()
  if not stat.S_ISREG(a.st_mode) or not all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in FIELDS):raise ValueError('stable whole FD '+str(p))
  if len(data)!=r['size'] or a.st_mode!=r['mode'] or hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError('exact whole reference '+str(p))
 return data,{k:getattr(a,k) for k in FIELDS}
def write_json(p,v):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def authority():
 inputs=json.loads((D/'INPUTS.json').read_bytes())
 for name in ('parent_manifest','binding','collector_ref','overlay','overlay_source','original_stage_source','original_input_pins','typed_validator','constructor','proposal'):read(inputs[name])
 parent=json.loads(read(inputs['parent_manifest'])[0]);binding=json.loads(read(inputs['binding'])[0]);collector=json.loads(read(inputs['collector_ref'])[0]);overlay=json.loads(read(inputs['overlay'])[0])
 constructor=load('canonical_m03_constructor',inputs['constructor']['path']);nd=load('unchanged_m03_typed_validator',inputs['typed_validator']['path'])
 doc=constructor.construct(parent,binding,collector,inputs['archive'],inputs['overlay'],inputs['overlay_source'])
 if doc!=json.loads(read(inputs['proposal'])[0]):raise ValueError('whole proposed document changed')
 refs=list(doc['artifacts'].values())+doc['modules']+list(doc['staging'].values())
 if len(refs)!=17:raise ValueError('complete17actual reference roles')
 identities={}
 for r in refs:
  _,identity=read(r);identities[r['path']]=identity
 validated=nd._validate_manifest(copy.deepcopy(doc))
 if validated!=doc:raise ValueError('strict canonical full-document identity')
 return inputs,parent,binding,collector,overlay,doc,nd,identities

def check():
 inputs,parent,binding,collector,overlay,doc,nd,identities=authority()
 ov=load('accepted_newc_engine',inputs['overlay_source']['path']);stage=load('frozen_original_stage',inputs['original_stage_source']['path'])
 base_data,_=read(binding['accepted_stage_base']);base_raw=gzip.decompress(base_data)
 data,_=read(inputs['archive']);raw=gzip.decompress(data)
 if len(base_raw)!=overlay['base_cpio_size'] or hashlib.sha256(base_raw).hexdigest()!=overlay['base_cpio_sha256'] or raw[:len(base_raw)]!=base_raw:raise ValueError('complete immutable accepted BASE prefix')
 if hashlib.sha256(raw[len(base_raw):]).hexdigest()!=overlay['overlay_sha256']:raise ValueError('exact retained overlay tail')
 old_overlay=json.loads(read(parent['staging']['overlay_manifest'])[0]);before,_=ov.parse_newc(base_raw);after,_=ov.parse_newc(raw)
 old_map=ov._manifest(ov._replay_records(before));new_map=ov._manifest(ov._replay_records(after))
 if old_map!=old_overlay['final_map'] or new_map!=overlay['final_map']:raise ValueError('actual complete archive final maps')
 stage.retained_map(old_map,new_map)
 negative=[]
 for label,key in [('extra-pair-key','extra'),('changed-derived-mode','mode')]:
  wrong=copy.deepcopy(doc)
  if key=='extra':wrong['pair_rounds']=10
  else:wrong['staging']['derived_initramfs']['mode']^=0o100
  try:nd._validate_manifest(wrong)
  except nd.DiagnosticError as e:
   expected='manifest keys differ' if key=='extra' else 'derived_initramfs size/mode drift'
   if str(e)!=expected:raise ValueError('wrong negative predicate '+str(e))
   negative.append(dict(case=label,status='EXPECTED_REFUSAL',error=str(e)))
  else:raise ValueError('negative accepted '+label)
 for path,identity in identities.items():
  if {k:getattr(Path(path).lstat(),k) for k in FIELDS}!=identity:raise ValueError('input identity changed during check')
 result=dict(status='PASS_COMPLETE_ACTUAL_MANIFEST_ARCHIVE_AND_TWO_NEGATIVES',manifest_proposal=inputs['proposal'],canonical_keys=sorted(doc),reference_roles=17,unique_reference_files=len(identities),actual_record_count=len(after),actual_member_count=len(new_map),raw_bytes=len(raw),original_full_prefix_bytes=len(base_raw),only_final_changed_members=['apps/app','init'],original_prefix_unchanged=True,exact_existing_archive=inputs['archive'],exact_existing_overlay=inputs['overlay'],identities=identities,negatives=negative,recompression=False,manifest_published=False,native_acceptance=False,guest_runs=0)
 write_json(D/'LOCAL-CHECK-RESULT.json',result)
 print(json.dumps(dict(status='PASS',whole_reference_roles=17,negative_cases=2,archive_bytes=inputs['archive']['size'],recompression=False)))
if __name__=='__main__':check()
