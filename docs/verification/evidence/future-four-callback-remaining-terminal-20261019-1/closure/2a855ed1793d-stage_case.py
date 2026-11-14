"""One fourleaf AVX/thread image-only stage proposal. No native execution.
Requires actual fourleaf reviewer contract, retention, and independent ordinary admission.
"""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,os,resource,shutil,stat,sys
D=Path(__file__).resolve().parent
REPO=Path('/home/holden/mckernel');SCRATCH=Path('/home/holden/mckernel-work/scratch')
def need(x,s):
 if not x:raise ValueError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 p=Path(p);s=p.stat();return dict(path=str(p),sha256=sha(p.read_bytes()),size=s.st_size,mode=s.st_mode)
def exact(r):need(ref(r['path'])==r,'exact input '+r['path'])
def write(p,b):
 with p.open('xb')as f:f.write(b)
def js(p,v):write(p,(json.dumps(v,indent=2)+'\n').encode())
def mod(n,p):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);sys.modules[n]=m;spec.loader.exec_module(m);return m
def private(p):
 s=p.lstat();need(p.resolve()==p and stat.S_ISDIR(s.st_mode)and s.st_uid==1000 and stat.S_IMODE(s.st_mode)==0o700,'private canonical directory '+str(p))

ARTIFACT_ROLES={'cpu','process','rust','image'}
ORIGINAL_KINDS={'CMakeCache.txt','build.make','build.stderr.log','build.stdout.log','compile_commands.json','cpu.c.o','link.txt','mckernel.img','mckernel.img.map','mckernel_rust.o','process.c.o','production-abi-checks.json','production-abi-cpu.c','production-abi-process.c','receipt.json','release-fallback-cpu.o','release-fallback-process.o','release-legacy-mckernel_rust.o','release-native-mckernel_rust.o','release-selected-cpu.o','release-selected-process.o'}
ROLE_KIND={'cpu':'cpu.c.o','process':'process.c.o','rust':'mckernel_rust.o','image':'mckernel.img'}
def typed_descriptor(d):
 need(type(d)is dict,'descriptor object')
 need(type(d.get('path'))is str and Path(d['path']).is_absolute(),'absolute descriptor path')
 need(type(d.get('sha256'))is str and len(d['sha256'])==64 and all(c in '0123456789abcdef'for c in d['sha256']),'descriptor digest')
 for k in ['bytes','dev','inode','uid','gid','mode','mtime_ns','ctime_ns']:
  need(type(d.get(k))is int and d[k]>=0,'typed descriptor '+k)
 need(d['mode']<=0o7777,'descriptor permission mode')
 for k in ['mtime_ns','ctime_ns','nlink']:
  if k in d:need(type(d[k])is int and d[k]>=0,'typed descriptor '+k)
 return d

def current_retained_descriptor(d):
 typed_descriptor(d);fd=os.open(d['path'],os.O_RDONLY|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode)and before.st_nlink==1,'retained regular single-link file')
  digest=hashlib.sha256()
  while True:
   chunk=os.read(fd,1024*1024)
   if not chunk:break
   digest.update(chunk)
  after=os.fstat(fd)
  fields={'dev':'st_dev','inode':'st_ino','uid':'st_uid','gid':'st_gid','bytes':'st_size','mtime_ns':'st_mtime_ns','ctime_ns':'st_ctime_ns','nlink':'st_nlink'}
  for k,a in fields.items():
   need(getattr(before,a)==getattr(after,a),'retained descriptor changed '+k)
   if k in d:need(d[k]==getattr(after,a),'current retained '+k)
  need(before.st_mode==after.st_mode and stat.S_IMODE(after.st_mode)==d['mode'],'current retained mode')
  need(digest.hexdigest()==d['sha256'],'current retained hash')
 finally:os.close(fd)

def validate_separate_retention_fact(r,b):
 """Completed retention evidence only; never independent retention acceptance."""
 need(r['remaining_retention']=='PERFORMED_SEPARATELY_NOT_ACCEPTED_IN_THIS_REPORT','completed separate retention scope')
 evidence=r['retention_separate_evidence'];bound=b['retention_separate_evidence']
 need(set(evidence)==set(bound)=={'outer_status','retained_objects','engine_result'},'fixed separate retention evidence roles')
 for role in ['outer_status','retained_objects','engine_result']:
  need(evidence[role]['path']==bound[role]['path']and evidence[role]['sha256']==bound[role]['sha256'],'separate retention evidence '+role);exact(bound[role])
 outer=json.loads(Path(bound['outer_status']['path']).read_text());result=json.loads(Path(bound['engine_result']['path']).read_text());pairs=json.loads(Path(bound['retained_objects']['path']).read_text())
 need(outer['returncode']==0 and type(outer['returncode'])is int and outer['direct_child_joined']is True,'separate retention operation joined')
 need(result['status']=='PASS_FINITE_EXACT_RETENTION_ONLY'and result['artifact_acceptance']is False and result['cleanup_authorized']is False,'separate operation is not acceptance or cleanup')
 need(type(pairs)is list and len(pairs)==21,'separate21 retention facts')
 return evidence

def canonical_fourleaf_acceptance(b,full,request,owner):
 # Fixed independent authority contract. Binding data never selects schema/decision/field names.
 review=b['image_artifact_review'];r=json.loads(Path(review['path']).read_text())
 need(r['schema']=='mckernel.independent-rust-four-leaf-image-actual-review.v1','fixed fourleaf schema')
 need(r['decision']=='PASS_ACTUAL_PRODUCTION_IMAGE_ARTIFACT_AND_GUARD_RETIREMENT','fixed fourleaf decision')
 need(r['implementation_ownership']is False and r['production_artifact_acceptance']is True and r['runtime_acceptance']is False and r['compute_c_retirement_credit']is False,'fixed acceptance scope')
 need(set(r['actual_artifacts'])==ARTIFACT_ROLES,'exact four artifact roles')
 artifacts=r['actual_artifacts']
 for d in artifacts.values():typed_descriptor(d)
 need(len({d['path']for d in artifacts.values()})==4,'unique original four roles')
 refs=r['source_request_bindings'];need(set(refs)=={'request','manifest','materialization_receipt'},'complete source pointer roles')
 for key,fkey in [('request','image_request'),('manifest','entire_source_manifest'),('materialization_receipt','materialization_receipt')]:
  need(refs[key]['path']==full[fkey]['path']and refs[key]['sha256']==full[fkey]['sha256'],'canonical full source pointer '+key)
 for key in ['source_identity','source_derivative_sha256','materialization_sha256','candidate_sha','candidate_identity_scope']:
  need(r[key]==full[key]==request[key],'canonical source identity '+key)
 need(r['source_identity']['path']==full['source_root']==request['source_root'],'canonical entire source root')
 originals=r['actual21_originals'];need(type(originals)is list and len(originals)==21,'exact21 original roles')
 need(originals==json.loads(Path(b['retained_production_manifest']['path']).read_text()),'canonical actual21 producer authority rows')
 need({x['kind']for x in originals}==ORIGINAL_KINDS,'fixed21 original role set')
 need(sum(x['action']=='copy'for x in originals)==17 and sum(x['action']=='reuse'for x in originals)==4,'copy17 reuse4 original roles')
 need(len({x['original']['path']for x in originals})==21 and len({x['retained']for x in originals})==21,'unique21 original and destination paths')
 for x in originals:
  need(set(x)=={'kind','action','original','retained','retained_authority_pending'},'fixed21 row fields')
  o=x['original'];need(type(o['mode'])is str and o['mode'].startswith('0o'),'original octal mode')
  projected=dict(path=o['path'],sha256=o['sha256'],bytes=o['size'],dev=o['device'],inode=o['inode'],uid=o['uid'],gid=o['gid'],mode=int(o['mode'],8),nlink=o['nlink'],mtime_ns=o['mtime_ns'],ctime_ns=o['ctime_ns'])
  typed_descriptor(projected)
  need(type(x['retained'])is str and Path(x['retained']).is_absolute(),'retained role destination')
  if x['kind']in ROLE_KIND.values():
   role=next(k for k,v in ROLE_KIND.items()if v==x['kind']);fact=artifacts[role]
   for k,v in projected.items():
    if k in fact:need(fact[k]==v,'full original artifact projection '+role+' '+k)
   for k in ['mtime_ns','ctime_ns']:
    if k in fact:need(o[k]==fact[k],'full original timestamp '+role+' '+k)
 primary=r['existing_primary_pairs'];need(set(primary)=={'count','copier_receipt','pairs'},'fixed primary pair fields');need(primary['count']==4 and type(primary['count'])is int,'exact4 retained copies')
 pairs=primary['pairs'];need(type(pairs)is list and len(pairs)==4 and {x['role']for x in pairs}==ARTIFACT_ROLES,'full copied role set')
 need(len({x['original']['path']for x in pairs})==4 and len({x['retained']['path']for x in pairs})==4,'unique retained copied role paths')
 need(primary['copier_receipt']['path']==b['primary_copier_receipt']['path']and primary['copier_receipt']['sha256']==b['primary_copier_receipt']['sha256'],'actual copier receipt authority')
 exact(b['primary_copier_receipt'])
 copied=json.loads(Path(b['primary_copier_receipt']['path']).read_text())
 need(copied['status']=='PASS_EXACT_FOUR_ARTIFACT_RETENTION_ONLY'and set(copied['artifacts'])==ARTIFACT_ROLES,'actual4 copier receipt')
 for pair in pairs:
  role=pair['role'];need(pair['original']==artifacts[role],'complete copied original descriptor '+role)
  retained=pair['retained'];current_retained_descriptor(retained)
  original=pair['original'];copy=copied['artifacts'][role]
  need(copy['source']==original and copy['retained_path']==retained['path'],'actual copier pair '+role)
  need(copy['retained_dev']==retained['dev']and copy['retained_inode']==retained['inode']and copy['sha256']==retained['sha256']and copy['bytes']==retained['bytes'],'actual copier retained descriptor '+role)
  need((original['dev'],original['inode'])!=(retained['dev'],retained['inode']),'independent retained inode '+role)
  for k in ['bytes','uid','gid','mode','sha256']:need(original[k]==retained[k],'copy preserved '+role+' '+k)
  row=next(x for x in originals if x['kind']==ROLE_KIND[role]);need(row['retained']==retained['path'],'declared retained destination '+role)
 selected=[x for x in pairs if x['role']=='image'];need(len(selected)==1,'exactly one selected image pair');pair=selected[0]
 need(pair==b['selected_image_retained_pair']and pair['original']==b['actual_image_source'],'selected actual image pair')
 image=b['retained_image'];retained=pair['retained']
 need(image['path']==retained['path']and image['sha256']==retained['sha256']and image['size']==retained['bytes']and stat.S_IMODE(image['mode'])==retained['mode'],'strict image reference projection')
 lineage=r['guard_retirement']
 need(lineage['retired']is True and lineage['container_id']==owner['container_id']=='ba93e7765e7e698393d7ab4c024e5a8d0f66d9a8bc2852872ed59c4ce463854f','actual stopped owner container')
 need(lineage['owner_nonce']==owner['owner_nonce']==b['owner_nonce']=='48e71075e2414894ad296a85a23c8e41','actual owner nonce lineage')
 need(lineage['owner_receipt']['path']==b['owner_receipt']['path']and lineage['owner_receipt']['sha256']==b['owner_receipt']['sha256']=='237af8d77af2e3ae2dd9974142e8c890c079ff2be5175509ee7ad46421158281','actual owner receipt lineage')
 need(lineage['common_shared_cleanup_pending']is True,'retained cleanup obligation')
 validate_separate_retention_fact(r,b)
 need(r['actual_source11']['count']==11 and type(r['actual_source11']['count'])is int,'source11 count')
 source11=r['actual_source11'];authority=b['source11_authority']
 need(type(authority)is dict,'actual source11 immutable bindings PENDING')
 need(set(source11)=={'count','host_owner','source11','current_guard','request_lineage'},'fixed source11 projection fields')
 for k in ['source11','current_guard']:
  need(source11[k]['path']==authority[k]['path']and source11[k]['sha256']==authority[k]['sha256'],'source11 authority ref '+k);exact(authority[k])
 need(authority['source11']['path']=='/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/source-sha256.json'and authority['source11']['sha256']=='ee61adc210497066f49c6f9bd31310fe20409b14efea3bf28c85271d3b05cc60','fixed actual11 source authority')
 source_map=json.loads(Path(authority['source11']['path']).read_text())
 need(source_map['guard_consumer_source_count']==11 and type(source_map['guard_consumer_source_count'])is int,'consumed source11 count')
 need(source_map['publication_row_count']==12 and type(source_map['publication_row_count'])is int and len(source_map['publication_rows'])==12,'actual publication12 count')
 consumed=source_map['source_sha256'];need(type(consumed)is dict and len(consumed)==11,'full11 consumed source map')
 for path,digest in consumed.items():
  need(type(path)is str and Path(path).is_absolute()and type(digest)is str and len(digest)==64 and all(c in '0123456789abcdef'for c in digest),'typed consumed source map')
 need(source11['host_owner']=='/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/adapters/native_rust_exact_build_container_owner.py','fixed actual host owner path')
 need(authority['current_guard']['path']in consumed and consumed[authority['current_guard']['path']]==authority['current_guard']['sha256'],'actual guard source consumed hash')
 need(source11['host_owner']==request['host_owner_path']and source11['host_owner']in consumed and consumed[source11['host_owner']]==request['host_owner_sha256'],'actual host owner consumed hash')
 links=source11['request_lineage'];need(set(links)=={'request','owner_receipt','guard_result','postjoin_readback'},'fixed source11 lineage pointers')
 expected={'request':full['image_request'],'owner_receipt':b['owner_receipt'],'guard_result':authority['guard_result'],'postjoin_readback':authority['postjoin_readback']}
 for k,v in expected.items():
  need(links[k]['path']==v['path']and links[k]['sha256']==v['sha256'],'source11 request lineage '+k);exact(v)
 postjoin=json.loads(Path(authority['postjoin_readback']['path']).read_text())
 need(postjoin['status']=='PASS_ORDINARY_GUARD_POSTJOIN_READBACK_ONLY'and postjoin['guard_direct_joined']is True and postjoin['root27_4_reacquired_after_join']is True,'actual guard postjoin')
 need(postjoin['guard_result_sha256']==authority['guard_result']['sha256']and postjoin['owner_receipt_sha256']==b['owner_receipt']['sha256']and postjoin['container_id']==owner['container_id'],'postjoin actual guard owner chain')
 for k in ['candidate_sha','candidate_identity_scope','materialization_sha256']:
  need(owner[k]==request[k],'owner full source lineage '+k)
 need(owner['ihk_sha']==request['ihk_sha'],'owner IHK lineage')
 return review

def validate_fourleaf_authority(b):
 """Validate one exact fixed fourleaf binding; return canonical report ref.
 Source/file reads only. No writes, subprocesses, profiles, runtime or root authority.
 Caller must independently pin this module and immutable binding before import/call.
 Retained image/four-copy FD identities stay live-bound; original paths stay evidence-only.
 """
 need(b['finalization_status']=='READY_EXACT_INDEPENDENT_ARTIFACT_BOUND','actual independent artifact finalization pending')
 for k in ['retained_image','image_artifact_review','retained_production_manifest','owner_receipt']:exact(b[k])
 full=b['full_fourleaf_source_authority']
 for k in ['image_request','entire_source_manifest','materialization_receipt']:exact(full[k])
 request=json.loads(Path(full['image_request']['path']).read_text());owner=json.loads(Path(b['owner_receipt']['path']).read_text())
 for k in ['source_root','source_identity','source_derivative_sha256','materialization_sha256','candidate_sha','candidate_identity_scope']:
  need(request[k]==full[k],'complete fourleaf authority '+k)
 need(full['image_request']['sha256']==b['producer_request_sha256']=='bc98516d19e79ac3cc4a0fd89ca4f9de7e60ee7b64c77ead65e808d44c61dba9','exact new request')
 need(owner['status']=='PASS'and owner['retired']is True and owner['owner_nonce']==b['owner_nonce']and owner['source_derivative_sha256']==full['source_derivative_sha256'],'joined new producer')
 return canonical_fourleaf_acceptance(b,full,request,owner)

def main():
 ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--case',choices=['roundtrip'],required=True);ap.add_argument('--binding',required=True);ap.add_argument('--binding-sha256',required=True);ap.add_argument('--preflight-only',action='store_true');a=ap.parse_args()
 need(os.sched_getaffinity(0)=={7}and resource.getrlimit(resource.RLIMIT_AS)[0]<=1073741824,'CPU7/1GiB')
 need(sha(Path(a.binding).read_bytes())==a.binding_sha256,'binding bytes');b=json.loads(Path(a.binding).read_text());c=b['cases'][a.case]
 review=validate_fourleaf_authority(b)
 for k in ['accepted_native_review','accepted_stage_result']:exact(b[k])
 for k in ['old_manifest','old_base','old_overlay','old_overlay_manifest','payload','collector','mcexec']:exact(c[k])
 exact(b['overlay_source']);exact(b['diagnostic_source']);assets=Path(b['assets_root']);manifests=Path(b['manifests_root']);out=Path(c['output_dir']);mp=Path(c['manifest_dir'])
 need(REPO in assets.parents and SCRATCH in manifests.parents,'unchanged visible mount roots');need(not os.path.lexists(out)and not os.path.lexists(mp),'fresh case output')
 for row in b['cases'].values():need(len(os.fsencode(row['endpoint']))==row['endpoint_encoded_bytes']<=107,'full endpoint preflight')
 need(shutil.disk_usage(REPO).free>=16*1024**3+576*1024**2+64*1024**2,'host floor plus576MiB reserve plus64MiBstage')
 need(shutil.disk_usage(SCRATCH).free>=12*1024**3+576*1024**2+64*1024**2,'scratch floor plus576MiB reserve plus64MiBstage')
 if a.preflight_only:
  print(json.dumps(dict(status='PASS_EXACT_REVIEWED_IMAGE_STAGE_PREFLIGHT',case=a.case,archives=0,runtime_release=False)));return
 if a.case=='roundtrip':
  need(not assets.exists()and not manifests.exists(),'fresh roots');assets.mkdir(mode=0o700);manifests.mkdir(mode=0o700)
 else:
  private(assets);private(manifests);need((assets/'avx/stage-result.json').is_file(),'AVX stage precedes threads')
 private(assets);private(manifests);out.mkdir(mode=0o700);mp.mkdir(mode=0o700)
 visible=assets/'image.artifact'
 if a.case=='roundtrip':
  write(visible,Path(b['retained_image']['path']).read_bytes());visible.chmod(0o755)
 else:need(ref(visible)['sha256']==b['retained_image']['sha256']and visible.stat().st_size==b['retained_image']['size'],'shared image exact')
 image=ref(visible);m=json.loads(Path(c['old_manifest']['path']).read_text());ov=mod('scheduler_stage_overlay',b['overlay_source']['path']);nd=mod('scheduler_stage_nd',b['diagnostic_source']['path']);raw=gzip.decompress(Path(c['old_base']['path']).read_bytes());records,_=ov.parse_newc(raw)
 parts=[];pos=0;count=0;data=visible.read_bytes();proof=[]
 while pos<len(raw):
  if raw[pos]==0:
   end=pos+1
   while end<len(raw)and raw[end]==0:end+=1
   parts.append(raw[pos:end]);pos=end;continue
  h=raw[pos:pos+110];v=ov._fields(h);name=raw[pos+110:pos+110+v[11]-1].decode();name=name[2:]if name.startswith('./')else name;ds=(pos+110+v[11]+3)&~3;end=(ds+v[6]+3)&~3
  if name=='images/mckernel.img':
   hh=bytearray(h);hh[54:62]=('%08x'%len(data)).encode()
   if h[:6]==b'070702':hh[102:110]=('%08x'%(sum(data)&0xffffffff)).encode()
   parts.append(bytes(hh)+raw[pos+110:ds]+data+b'\0'*(-len(data)%4));count+=1;proof.append(dict(name=name,old_header_hex=h.hex(),new_header_hex=bytes(hh).hex()))
  else:parts.append(raw[pos:end])
  pos=end
 need(count==1,'one image record');patched=b''.join(parts);rr,_=ov.parse_newc(patched);need(len(records)==len(rr),'all original records')
 for x,y in zip(records,rr):
  omit={'data','size','sha256'}if x['name']=='images/mckernel.img'else set();need({k:v for k,v in x.items()if k not in omit}=={k:v for k,v in y.items()if k not in omit},'all record metadata and order')
 base=out/'base.cpio.gz';write(base,ov._gzip(patched));overlay=out/'lifecycle.cpio.gz'
 om=ov.build_overlay(str(base),c['payload']['path'],c['collector']['path'],c['mcexec']['path'],str(overlay),collector_sha256=c['collector']['sha256'],mcexec_sha256=c['mcexec']['sha256'],payload_sha256=c['payload']['sha256'],base_sha256=ref(base)['sha256'],base_size=base.stat().st_size,base_cpio_sha256=sha(patched),base_cpio_size=len(patched));js(out/'overlay-manifest.json',om)
 old=json.loads(Path(c['old_overlay_manifest']['path']).read_text())['final_map'];full=ov._replay_records(ov.parse_newc(gzip.decompress(overlay.read_bytes()))[0]);final=ov._manifest(full);need(final==om['final_map']and len(final)==len(old)==60 and set(final)==set(old),'full60 concatenated replay')
 deltas={n:{k:[old[n][k],final[n][k]]for k in old[n]if old[n][k]!=final[n][k]}for n in final if final[n]!=old[n]};need(set(deltas)=={'images/mckernel.img'}and set(deltas['images/mckernel.img'])<={'sha256','size'},'only image data delta against own case old overlay')
 oldfull=ov._replay_records(ov.parse_newc(gzip.decompress(Path(c['old_overlay']['path']).read_bytes()))[0])
 for n in full:
  for k in full[n]:
   if k not in {'data','size','sha256'}:need(full[n][k]==oldfull[n][k],'all final metadata '+n+' '+k)
 m['artifacts']['mckernel_image']=image
 for k in ['initramfs','root_base']:m['artifacts'][k]=ref(base)
 m['staging'].update(base_initramfs=ref(base),derived_initramfs=ref(overlay),overlay_manifest=ref(out/'overlay-manifest.json'));js(mp/'manifest.json',m);nd.load_manifest(str(mp/'manifest.json'))
 used=sum(p.stat().st_size for p in assets.rglob('*')if p.is_file());need(used<=64*1024**2,'64MiB aggregate stage output')
 js(out/'stage-result.json',dict(status='PASS_IMAGE_ONLY_STAGE_PENDING_MODIFIED_CONSUMERS_AND_INDEPENDENT_REVIEW',manifest=ref(mp/'manifest.json'),image=image,artifact_review=review,base=ref(base),overlay=ref(overlay),deltas=deltas,raw_header_proof=proof,final_map=final,own_accepted_base_preserved=True,all_other_final_metadata_equal=True,aggregate_stage_bytes=used,runtime_release=False))
 print(json.dumps(dict(status='PASS_CASE_IMAGE_ONLY_STAGE',case=a.case,image_sha256=image['sha256'],image_bytes=image['size'],aggregate_stage_bytes=used,guests=0,runtime_release=False)))
if __name__=='__main__':main()
