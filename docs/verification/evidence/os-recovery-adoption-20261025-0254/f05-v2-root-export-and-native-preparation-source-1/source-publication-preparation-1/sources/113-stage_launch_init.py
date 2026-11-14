"""Three exact module members in BASE; immutable suffix and archive metadata."""
from pathlib import Path
import copy,gzip,hashlib,importlib.util,json,os,stat
D=Path(__file__).resolve().parent
NAMES=('ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def ref(path):
 p=Path(path);s=p.stat();return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=s.st_size,mode=s.st_mode)
def exact(r):
 if ref(r['path'])!=r:raise ValueError('changed exact source '+r['path'])
def write(p,b):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def js(p,v):write(p,(json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
def stage_bytes(producer,ov,raw,overlay,changes):
 if tuple(sorted(changes))!=tuple(sorted('modules/'+n for n in NAMES)):raise ValueError('exact three selected module members')
 n=overlay['base_cpio_size'];base=raw[:n];tail=raw[n:]
 if producer.sha(base)!=overlay['base_cpio_sha256']:raise ValueError('original BASE prefix identity')
 before,_=ov.parse_newc(raw)
 if ov._manifest(ov._replay_records(before))!=overlay['final_map']:raise ValueError('original full archive member map')
 changed_base,headers=producer.derive_base_payloads(ov,base,changes)
 if len(headers)!=3:raise ValueError('three original BASE members once each')
 final_raw=changed_base+tail;after,_=ov.parse_newc(final_raw)
 if len(before)!=len(after):raise ValueError('retained complete record count')
 for old,new in zip(before,after):
  omit={'data','size','sha256'} if old['name'] in changes else set()
  if {k:v for k,v in old.items() if k not in omit}!={k:v for k,v in new.items() if k not in omit}:raise ValueError('retained original record order/metadata '+old['name'])
 final=ov._manifest(ov._replay_records(after));old=overlay['final_map']
 if set(final)!=set(old):raise ValueError('no archive additions/removals')
 for name in old:
  omit={'size','sha256'} if name in changes else set()
  if {k:v for k,v in old[name].items() if k not in omit}!={k:v for k,v in final[name].items() if k not in omit}:raise ValueError('untouched member bytes or metadata '+name)
 return changed_base,tail,final_raw,final,headers,len(after)
def main():
 b=json.loads((D/'STAGE-INPUTS.json').read_bytes())
 for r in b['sources'].values():exact(r)
 parent=json.loads(Path(b['sources']['parent_manifest']['path']).read_bytes())
 if parent['artifacts']['mckernel_image']['sha256']!=b['image_sha256'] or [r['sha256'] for r in parent['modules']]!=b['module_sha256s']:raise ValueError('exact original205 tuple')
 for r in (*parent['artifacts'].values(),*parent['modules'],*parent['staging'].values()):exact(r)
 modules=b['new_modules']
 if tuple(Path(r['path']).name for r in modules)!=NAMES:raise ValueError('exact new composite module order')
 for r in modules:exact(r)
 for key in ('module_actual_acceptance','module_physical_retirement'):exact(b[key])
 nd=load('composite_diagnostic',D/'native_diagnostic.py');binding=load('exact_composite_binding',D/'composite_module_binding.py')
 binding.validate_module_binding({'artifacts':parent['artifacts'],'modules':modules})
 original=Path(b['sources']['compiled_collector']['path']);raw_collector=original.read_bytes();original_mode=b['sources']['compiled_collector']['mode']
 if original.stat().st_mode!=original_mode or stat.S_IMODE(original_mode)!=0o755:raise ValueError('accepted staged collector0755 identity')
 producer=load('accepted_header_producer',b['sources']['header_producer']['path']);ov=load('accepted_newc_overlay',b['sources']['overlay_module']['path'])
 overlay=json.loads(Path(parent['staging']['overlay_manifest']['path']).read_bytes());raw=gzip.decompress(Path(parent['staging']['derived_initramfs']['path']).read_bytes())
 changes={'modules/'+Path(new['path']).name:(Path(new['path']).read_bytes(),old['sha256']) for old,new in zip(parent['modules'],modules)}
 changed_base,tail,final_raw,final,headers,count=stage_bytes(producer,ov,raw,overlay,changes)
 out=Path(b['output']);out.mkdir(mode=0o700)
 collector=out/'pair-init-0755';write(collector,raw_collector);collector.chmod(0o755)
 derived_base=out/'base.cpio.gz';write(derived_base,ov._gzip(changed_base))
 output=out/'lifecycle.cpio.gz';write(output,ov._gzip(final_raw))
 if gzip.decompress(derived_base.read_bytes())!=changed_base or gzip.decompress(output.read_bytes())!=final_raw:raise ValueError('both complete derived archives reread')
 overlay.update(base_cpio_sha256=producer.sha(changed_base),base_cpio_size=len(changed_base),base_sha256=producer.sha(derived_base.read_bytes()),final_map=final,output_identity=ov._identity(output.stat()),output_sha256=producer.sha(output.read_bytes()),overlay_sha256=producer.sha(tail),size=output.stat().st_size)
 overlay['sources']['base']={'path':str(derived_base),'sha256':producer.sha(derived_base.read_bytes()),'identity':ov._identity(derived_base.stat())}
 overlay['sources']['collector']={'path':str(collector),'sha256':producer.sha(raw_collector),'identity':ov._identity(collector.stat())}
 js(out/'overlay-manifest.json',overlay)
 m=copy.deepcopy(parent);m['case_id']='practical.rust.composite64.module-abi-ordinary-vma.accepted205';m['modules']=modules
 m['artifacts']['initramfs']=ref(derived_base);m['artifacts']['root_base']=ref(derived_base)
 m['staging'].update(base_initramfs=ref(derived_base),collector=ref(collector),derived_initramfs=ref(output),overlay_manifest=ref(out/'overlay-manifest.json'),overlay_source=ref(Path(__file__)))
 nd._validate_manifest(m)
 for r in b['sources'].values():exact(r)
 for r in modules:exact(r)
 js(out/'manifest.json',m)
 used=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
 if used>64<<20:raise ValueError('aggregate64MiB stage cap')
 result=dict(status='PASS_COMPOSITE64_THREE_MODULE_STAGE_ONLY',manifest=ref(out/'manifest.json'),overlay=ref(output),derived_base=ref(derived_base),collector=ref(collector),original_collector=b['sources']['compiled_collector'],parent_manifest=b['sources']['parent_manifest'],only_changed_members=sorted(changes),module_actual_acceptance=b['module_actual_acceptance'],module_physical_retirement=b['module_physical_retirement'],record_count=count,member_count=len(final),header_proof=headers,unchanged_overlay_suffix_sha256=producer.sha(tail),all_original_order_and_metadata_preserved=True,pair_rounds=10,stage_bytes=used,guest_runs=0,application_launches=0,quota_credit=False)
 js(out/'stage-result.json',result);print(json.dumps({k:result[k] for k in ('status','record_count','member_count','stage_bytes','guest_runs')}))
if __name__=='__main__':main()
