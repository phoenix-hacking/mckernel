"""Two replacement members and one added public helper; pinned newc engines only."""
import argparse,contextlib,copy,hashlib,importlib.util,json,os,resource,stat
from pathlib import Path
D=Path(__file__).resolve().parent
ENGINE=Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-native-20261019-1/module_span_engine_cap16.py')
ENGINE_SHA='04e308a5bd8a3b6d80480763bcee6e629d61d815c618a6ae7cf89043575e8a1f'
CAP=64<<20
def need(ok,label):
 if not ok:raise ValueError(label)
def sha(b):return hashlib.sha256(b).hexdigest()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main(binding,digest):
 need(os.getuid()==1000 and os.sched_getaffinity(0)=={7},'UID1000/CPU7')
 need(0<resource.getrlimit(resource.RLIMIT_AS)[0]<=1<<30,'AS1GiB')
 need(sha(ENGINE.read_bytes())==ENGINE_SHA,'pinned existing transform')
 e=load('existing_cycle_span_engine',ENGINE);ov=e.parser()
 with contextlib.ExitStack() as stack:
  source=ov._Source(binding,stack);need(source.sha256==digest,'whole stage binding');b=json.loads(source.data)
  need(b['schema']=='mckernel.selected205.two-complete-cycle-stage-inputs.v1','fixed stage input schema')
  inputs={}
  for key,r in b['inputs'].items():
   need(set(r)=={'path','sha256','bytes'},'full ref3');obj=ov._Source(r['path'],stack)
   need(obj.sha256==r['sha256'] and len(obj.data)==r['bytes'],'whole input '+key);inputs[key]=obj
  parent=json.loads(inputs['parent'].data);meta=json.loads(inputs['meta'].data)
  original_nd=load('accepted_original_single_pair_manifest_gate',b['inputs']['original_nd']['path']);original_nd._validate_manifest(parent)
  need(parent['artifacts']['mckernel_image']['sha256']==b['image_sha256'] and [r['sha256'] for r in parent['modules']]==b['module_sha256s'],'selected205 matched tuple')
  need(sha(Path(__file__).read_bytes())==inputs['stager'].sha256,'actual stager self binding')
  for name in ('boot','collector','release'):
   obj=inputs[name];st=os.fstat(obj.fd)
   observed=dict(path=obj.path.path,device=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=oct(stat.S_IMODE(st.st_mode)),size=st.st_size,nlink=st.st_nlink,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns,sha256=obj.sha256)
   need(observed==b['compiled_originals'][name] and observed['mode']=='0o700','whole actual compiled descriptor/original0700 '+name)
   ov._check_collector(obj.data)
  base=e.inflate(inputs['base'].data);whole=e.inflate(inputs['overlay'].data)
  need(whole.startswith(base) and len(base)==meta['base_cpio_size'] and sha(base)==meta['base_cpio_sha256'],'actual base prefix')
  tail=whole[len(base):]
  need(inputs['base'].sha256==meta['base_sha256'] and inputs['overlay'].sha256==meta['output_sha256'] and sha(tail)==meta['overlay_sha256'],'compressed versus raw suffix identities')
  old=ov._manifest(ov._replay_records(ov.parse_newc(whole)[0]));need(old==meta['final_map'],'complete old replay map')
  member='bin/native-resource-release-probe';need(member not in old,'new public helper absent from old selected205')
  need(old['bin/native-boot']['mode']==old['init']['mode']==stat.S_IFREG|0o755,'inherited executable modes')
  newbase,bootproof=e.transform(base,inputs['boot'].data,old['bin/native-boot'],ov,'bin/native-boot')
  newtail,initproof=e.transform(tail,inputs['collector'].data,old['init'],ov,'init')
  # Existing archive encoder supplies the single genuinely new member. Existing
  # complete records, order, trailers and zero padding remain span-identical.
  addition=ov._archive([(member,inputs['release'].data,stat.S_IFREG|0o755)])
  output_raw=newbase+newtail+addition;need(len(output_raw)<=CAP,'raw64MiB')
  final=ov._manifest(ov._replay_records(ov.parse_newc(output_raw)[0]));need(set(final)==set(old)|{member},'exact one added member')
  for name,row in old.items():
   omit={'size','sha256'} if name in ('init','bin/native-boot') else set()
   need({k:v for k,v in row.items() if k not in omit}=={k:v for k,v in final[name].items() if k not in omit},'unchanged metadata and bytes '+name)
  oldsp=e.raw_spans(whole,ov);newsp=e.raw_spans(newbase+newtail,ov);need(len(oldsp)==len(newsp),'all original raw spans')
  proofs=[]
  for a,z in zip(oldsp,newsp):
   changed=(a['name']=='bin/native-boot') or (a['name']=='init' and a['offset']>=len(base))
   need((a['kind'],a['name'])==(z['kind'],z['name']),'original raw span order')
   if not changed:need(a['bytes']==z['bytes'],'untouched raw span bytes')
   proofs.append(dict(kind=a['kind'],name=a['name'],changed=changed,old_sha256=sha(a['bytes']),new_sha256=sha(z['bytes'])))
  compressed_base=ov._gzip(newbase);compressed=ov._gzip(output_raw)
  need(sum(map(len,[compressed_base,compressed,inputs['boot'].data,inputs['collector'].data,inputs['release'].data,inputs['oracle'].data]))<CAP-2*(1<<20),'aggregate64MiB')
  for root,floor,growth in [('/home/holden',16<<30,8<<20),('/home/holden/mckernel-work/scratch',12<<30,CAP)]:
   v=os.statvfs(root);need(v.f_bavail*v.f_frsize>=floor+growth+(640<<20),'floor+growth+reserve')
  target=Path(b['output']);need(target.is_absolute() and target.parent.resolve()==target.parent,'canonical target')
  edge=ov._Path(str(target));stack.callback(edge.close)
  try:edge.lstat()
  except FileNotFoundError:pass
  else:raise ValueError('fresh stage output')
  for obj in [source,*inputs.values()]:obj.verify()
  os.mkdir(edge.name,0o700,dir_fd=edge.parent);fd=os.open(edge.name,os.O_DIRECTORY|os.O_NOFOLLOW|os.O_RDONLY,dir_fd=edge.parent);stack.callback(os.close,fd);identity=os.fstat(fd);total=0
  def write(name,data,mode=0o600):
   nonlocal total
   need('/' not in name and total+len(data)<=CAP,'bounded named output')
   f=os.open(name,os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_WRONLY,mode,dir_fd=fd)
   with os.fdopen(f,'wb') as stream:os.fchmod(stream.fileno(),mode);stream.write(data);stream.flush();os.fsync(stream.fileno())
   total+=len(data)
  def ref(name,data,mode=0o600):return dict(path=str(target/name),sha256=sha(data),size=len(data),mode=stat.S_IFREG|mode)
  for role,name in [('boot','native-boot'),('collector','init'),('release','native-resource-release-probe')]:write(name,inputs[role].data,0o755)
  write('base.cpio.gz',compressed_base);write('lifecycle.cpio.gz',compressed);write('cycle_oracle.py',inputs['oracle'].data);write('stage_cycles.py',inputs['stager'].data)
  updated=copy.deepcopy(meta);updated.update(base_sha256=sha(compressed_base),base_cpio_sha256=sha(newbase),base_cpio_size=len(newbase),collector_sha256=inputs['collector'].sha256,overlay_sha256=sha(newtail+addition),output_sha256=sha(compressed),size=len(compressed),output_identity=ov._identity(os.stat('lifecycle.cpio.gz',dir_fd=fd)),final_map=final)
  updated['sources']['collector']=dict(path=str(target/'init'),sha256=inputs['collector'].sha256,identity=ov._identity(os.stat('init',dir_fd=fd)))
  updated['sources']['base']=dict(path=str(target/'base.cpio.gz'),sha256=sha(compressed_base),identity=ov._identity(os.stat('base.cpio.gz',dir_fd=fd)))
  mb=(json.dumps(updated,indent=2)+'\n').encode();write('overlay-manifest.json',mb)
  native=copy.deepcopy(parent);native['case_id']='practical.rust.selected205.two-complete-native-cycles'
  for name in ('initramfs','root_base'):native['artifacts'][name]=ref('base.cpio.gz',compressed_base)
  native['artifacts']['native_boot']=ref('native-boot',inputs['boot'].data,0o755)
  native['staging'].update(base_initramfs=ref('base.cpio.gz',compressed_base),derived_initramfs=ref('lifecycle.cpio.gz',compressed),collector=ref('init',inputs['collector'].data,0o755),overlay_manifest=ref('overlay-manifest.json',mb),overlay_source=ref('stage_cycles.py',inputs['stager'].data))
  write('manifest.json',(json.dumps(native,indent=2)+'\n').encode())
  result=dict(status='PASS_SOURCE_BOUND_TWO_COMPLETE_CYCLE_STAGE_ONLY',input_refs=b['inputs'],native_acceptance=False,changed_existing_members=['bin/native-boot','init'],added_members=[member],unchanged_modules=parent['modules'],image=parent['artifacts']['mckernel_image'],boot_header_proof=bootproof,init_header_proof=initproof,old_raw_spans=proofs,old_member_count=len(old),new_member_count=len(final),base_prefix_replaced_only_boot=True,original_compiled_modes_preserved=True,stage_bytes=total,full_restoration_verified=False,guest_runs=0)
  write('stage-result.json',(json.dumps(result,indent=2)+'\n').encode())
  for obj in [source,*inputs.values()]:obj.verify()
  edge.verify();need((edge.lstat().st_dev,edge.lstat().st_ino)==(identity.st_dev,identity.st_ino),'stable stage output');os.fsync(fd)
  print(json.dumps({k:result[k] for k in ('status','changed_existing_members','added_members','stage_bytes','guest_runs')}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--binding',required=True);p.add_argument('--binding-sha256',required=True);a=p.parse_args();main(a.binding,a.binding_sha256)
