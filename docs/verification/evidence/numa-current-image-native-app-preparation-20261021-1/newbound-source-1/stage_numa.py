"""One existing focused NUMA image/payload stage derivative. No native execution.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Requires dispatcher ordinary source/profile release; preserves accepted metadata route.
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
def main():
 ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--case',choices=['numa'],required=True);ap.add_argument('--binding',required=True);ap.add_argument('--binding-sha256',required=True);ap.add_argument('--preflight-only',action='store_true');a=ap.parse_args()
 need(os.sched_getaffinity(0)=={6}and resource.getrlimit(resource.RLIMIT_AS)[0]<=1073741824,'CPU6/1GiB')
 need(sha(Path(a.binding).read_bytes())==a.binding_sha256,'binding bytes');b=json.loads(Path(a.binding).read_text());c=b['cases'][a.case]
 review=b['image_artifact_review'];exact(review);r=json.loads(Path(review['path']).read_bytes())
 need(review['sha256']=='7331e75da3966e7e1059257b6456f651f78f056a66363cd9be849f7f9adf5629','fixed genuine image artifact decision')
 need(r['schema']=='mckernel.current-numa-scheduler.production-image-artifact-review.v1'and r['decision']=='PASS_ACTUAL_CURRENT_NUMA_SCHEDULER_IMAGE_AND_REAL_MCEEXEC_LINK_ARTIFACTS_ONLY'and r['implementation_ownership']is False,'independent actual artifact acceptance')
 need(r['status']=='PASS_CURRENT_IMAGE_BUILD_LINK_AND_NAMED_BOUNDARIES_NO_NATIVE_ACCEPTANCE' and r['reviewer'] and r['source_derivative_sha256']=='ea825bb5fd67fb5165d578dfb17831c00c399663f34049d6e132b4c701f994f7' and r['materialization_sha256']=='1b584ee5b65f39467c8215bb2fc272e1fb0e9c95ee23e01e16e523a8a551a3fa','actual current source artifact decision')
 need(r['observations']['mcexec_equals_accepted_threads_launcher'] is True,'accepted unchanged launcher')
 for key,role in [('image_source','artifacts/mckernel.img'),('mcexec_source','artifacts/mcexec')]:
  fact=r['artifact_descriptors_verified'][role];v=b[key];need(v['path']==fact['path']and v['sha256']==fact['sha256']and v['size']==fact['bytes'],'accepted exact artifact '+key);exact(v)
 exact(b['consumer_contract']);exact(b['accepted_actual_app_review']);exact(b['accepted_threads_stage']);exact(b['dynamic_closure_observation'])
 stage=json.loads(Path(b['accepted_threads_stage']['path']).read_bytes());need(b['accepted_threads_stage']['sha256']=='c6ad2a7f02c686fafcf7fbe645706a0202a1e7f0183e7e5e074865e841771e67','accepted actual threads stage')
 need(c['old_manifest']==stage['accepted_manifest'] and c['old_base']==stage['accepted_outputs']['base'] and c['old_overlay']==stage['accepted_outputs']['overlay'] and c['old_overlay_manifest']==stage['overlay_manifest'],'exact actual current threads baseline')
 need(b['mcexec_source']['sha256']==stage['accepted_outputs']['mcexec']['sha256']=='689dcad27b2ce3a30f49df1bfe9452f2169a14e9c350c24c9677c88b1f152876' and b['mcexec_source']['size']==stage['accepted_outputs']['mcexec']['size']==394656,'unchanged accepted launcher bytes')
 need(b['dynamic_closure_observation']['sha256']=='338f6eafeefce26cf4fb826c58d17762c7c204806e146b09ec480facd4452314','reuse genuine launcher dependency acceptance')
 need(b['accepted_actual_app_review']['sha256']=='3abbf0e84f3921e87a52199a83db86baf187adb775fa15e78765f39dabf00001','accepted unchanged Linux NUMA payload/oracle')
 need(c['payload']['sha256']=='0339cb5fcba4ea4f1f2977fd0d3a7653b48e0af1de7e0625fbfafbfe13fce5fb' and c['payload']['size']==5619416,'fixed already compiled NUMA payload')
 need(b['payload_contract']=={'argv': ['/bin/mcexec', '-t', '1', '0', 'app', 'threads'], 'cwd': '/case/work', 'env': {'COKERNEL_PATH': '/apps', 'PATH': '/usr/bin:/bin'}, 'oracle': {'stdout_hex': '6e756d6120616c6c6f7765643d3120696e74657276616c3d3120717565726965733d39206d6f64653d31206d61736b3d31206e65696768626f72733d322070726f636573733d31206775617264733d312062797465733d3132323838207072657365727665643d3120756e6d61707065643d310a', 'stderr_hex': '', 'exit_code': 37}, 'stdout_limit_bytes': 1024, 'stderr_limit_bytes': 1024},'exact NUMA oracle and honest init argv')
 for k in ['old_manifest','old_base','old_overlay','old_overlay_manifest','payload','collector','mcexec']:exact(c[k])
 exact(b['overlay_source']);exact(b['diagnostic_source']);assets=Path(b['assets_root']);manifests=Path(b['manifests_root']);out=Path(c['output_dir']);mp=Path(c['manifest_dir'])
 need(REPO in assets.parents and SCRATCH in manifests.parents,'unchanged visible mount roots');need(not os.path.lexists(out)and not os.path.lexists(mp),'fresh case output')
 for row in b['cases'].values():need(len(os.fsencode(row['endpoint']))==row['endpoint_encoded_bytes']<=107,'full endpoint preflight')
 need(shutil.disk_usage(REPO).free>=16*1024**3+640*1024**2+64*1024**2,'host floor plus640MiB reserve plus64MiBstage')
 need(shutil.disk_usage(SCRATCH).free>=12*1024**3+640*1024**2+64*1024**2,'scratch floor plus640MiB reserve plus64MiBstage')
 if a.preflight_only:
  print(json.dumps(dict(status='PASS_EXACT_REVIEWED_IMAGE_STAGE_PREFLIGHT',case=a.case,archives=0,runtime_release=False)));return
 need(not assets.exists()and not manifests.exists(),'fresh roots');assets.mkdir(mode=0o700);manifests.mkdir(mode=0o700)
 private(assets);private(manifests);out.mkdir(mode=0o700);mp.mkdir(mode=0o700)
 visible=assets/'image.artifact';write(visible,Path(b['image_source']['path']).read_bytes());visible.chmod(0o755)
 launcher=assets/'mcexec';write(launcher,Path(b['mcexec_source']['path']).read_bytes());launcher.chmod(0o755);launcher_ref=ref(launcher)
 payload_visible=assets/'numa.app';write(payload_visible,Path(c['payload']['path']).read_bytes());payload_visible.chmod(0o755);payload_ref=ref(payload_visible);need(payload_ref['sha256']==c['payload']['sha256'] and payload_ref['size']==c['payload']['size'],'exact runtime-visible NUMA payload copy')
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
 om=ov.build_overlay(str(base),str(payload_visible),c['collector']['path'],str(launcher),str(overlay),collector_sha256=c['collector']['sha256'],mcexec_sha256=c['mcexec']['sha256'],payload_sha256=c['payload']['sha256'],base_sha256=ref(base)['sha256'],base_size=base.stat().st_size,base_cpio_sha256=sha(patched),base_cpio_size=len(patched));js(out/'overlay-manifest.json',om)
 old=json.loads(Path(c['old_overlay_manifest']['path']).read_text())['final_map'];full=ov._replay_records(ov.parse_newc(gzip.decompress(overlay.read_bytes()))[0]);final=ov._manifest(full);need(final==om['final_map']and len(final)==len(old)==60 and set(final)==set(old),'full60 concatenated replay')
 deltas={n:{k:[old[n][k],final[n][k]]for k in old[n]if old[n][k]!=final[n][k]}for n in final if final[n]!=old[n]};need(set(deltas)=={'images/mckernel.img','apps/app'}and all(set(v)<={'sha256','size'}for v in deltas.values()),'only image and payload data deltas against accepted current threads overlay')
 need(final['bin/mcexec']==old['bin/mcexec'],'launcher final map explicitly unchanged')
 oldfull=ov._replay_records(ov.parse_newc(gzip.decompress(Path(c['old_overlay']['path']).read_bytes()))[0])
 for n in full:
  for k in full[n]:
   if k not in {'data','size','sha256'}:need(full[n][k]==oldfull[n][k],'all final metadata '+n+' '+k)
 m['case_id']='current-numa-interval';m['payload']=b['payload_contract'];m['artifacts']['payload']=payload_ref;m['artifacts']['mckernel_image']=image;m['artifacts']['mcexec']=launcher_ref
 for k in ['initramfs','root_base']:m['artifacts'][k]=ref(base)
 m['staging'].update(base_initramfs=ref(base),derived_initramfs=ref(overlay),overlay_manifest=ref(out/'overlay-manifest.json'));js(mp/'manifest.json',m);nd.load_manifest(str(mp/'manifest.json'))
 used=sum(p.stat().st_size for p in assets.rglob('*')if p.is_file());need(used<=64*1024**2,'64MiB aggregate stage output')
 js(out/'stage-result.json',dict(status='PASS_NUMA_IMAGE_AND_PAYLOAD_STAGE_PENDING_ACTUAL_CONSUMER_BINDING_AND_REVIEW',manifest=ref(mp/'manifest.json'),image=image,mcexec=launcher_ref,payload=payload_ref,artifact_review=review,base=ref(base),overlay=ref(overlay),deltas=deltas,raw_header_proof=proof,final_map=final,own_accepted_base_preserved=True,all_other_final_metadata_equal=True,aggregate_stage_bytes=used,runtime_release=False))
 print(json.dumps(dict(status='PASS_SINGLE_NUMA_IMAGE_AND_PAYLOAD_STAGE',case=a.case,image_sha256=image['sha256'],image_bytes=image['size'],aggregate_stage_bytes=used,guests=0,runtime_release=False)))
if __name__=='__main__':main()
