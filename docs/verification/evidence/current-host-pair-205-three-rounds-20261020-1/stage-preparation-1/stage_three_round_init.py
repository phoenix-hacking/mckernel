"""Replace only existing overlay init payload using the accepted header transformer."""
from pathlib import Path
import copy,gzip,hashlib,importlib.util,json,os,stat
D=Path(__file__).resolve().parent

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

def main():
 b=json.loads((D/'STAGE-INPUTS.json').read_bytes())
 for r in b['sources'].values():exact(r)
 parent=json.loads(Path(b['sources']['parent_manifest']['path']).read_bytes())
 if parent['artifacts']['mckernel_image']['sha256']!=b['image_sha256'] or [x['sha256'] for x in parent['modules']]!=b['module_sha256s']:raise ValueError('exact frozen image/module tuple')
 for r in (*parent['artifacts'].values(),*parent['modules'],*parent['staging'].values()):exact(r)
 out=Path(b['output']);out.mkdir(mode=0o700)
 original=Path(b['sources']['compiled_collector']['path']);raw_collector=original.read_bytes()
 if stat.S_IMODE(original.stat().st_mode)!=0o700:raise ValueError('preserve actual compiled collector0700')
 collector=out/'pair-init-0755';write(collector,raw_collector);collector.chmod(0o755)
 if original.read_bytes()!=collector.read_bytes() or stat.S_IMODE(original.stat().st_mode)!=0o700:raise ValueError('same collector bytes; original0700 unchanged')
 producer=load('accepted_header_producer',b['sources']['header_producer']['path']);ov=load('accepted_newc_overlay',b['sources']['overlay_module']['path'])
 nd=load('fixed_two_round_diagnostic',D/'native_diagnostic.py')
 overlay=json.loads(Path(parent['staging']['overlay_manifest']['path']).read_bytes())
 raw=gzip.decompress(Path(parent['staging']['derived_initramfs']['path']).read_bytes());n=overlay['base_cpio_size'];base=raw[:n];tail=raw[n:]
 if producer.sha(base)!=overlay['base_cpio_sha256']:raise ValueError('unchanged accepted full BASE prefix')
 changed,headers=producer.derive_base_payloads(ov,tail,{'init':(raw_collector,parent['staging']['collector']['sha256'])})
 if len(headers)!=1:raise ValueError('one existing overlay init member')
 final_raw=base+changed;old_records,_=ov.parse_newc(raw);records,_=ov.parse_newc(final_raw)
 if len(old_records)!=len(records):raise ValueError('exact original record count')
 final=ov._manifest(ov._replay_records(records));old=overlay['final_map']
 if set(final)!=set(old):raise ValueError('no archive member additions/removals')
 for name in old:
  omit={'size','sha256'} if name=='init' else set()
  if {k:v for k,v in old[name].items() if k not in omit}!={k:v for k,v in final[name].items() if k not in omit}:raise ValueError('retained member metadata/bytes '+name)
 output=out/'lifecycle.cpio.gz';write(output,ov._gzip(final_raw))
 if gzip.decompress(output.read_bytes())!=final_raw:raise ValueError('full archive reread')
 overlay.update(collector_sha256=producer.sha(raw_collector),final_map=final,output_identity=ov._identity(output.stat()),output_sha256=producer.sha(output.read_bytes()),overlay_sha256=producer.sha(changed),size=output.stat().st_size)
 overlay['sources']['collector']={'path':str(collector),'sha256':producer.sha(raw_collector),'identity':ov._identity(collector.stat())}
 js(out/'overlay-manifest.json',overlay)
 m=copy.deepcopy(parent);m['case_id']='practical.rust.fixed-three-rounds.accepted205';m['pair_rounds']=3
 m['staging'].update(collector=ref(collector),derived_initramfs=ref(output),overlay_manifest=ref(out/'overlay-manifest.json'),overlay_source=ref(Path(__file__)))
 nd._validate_manifest(m)
 for r in b['sources'].values():exact(r)
 js(out/'manifest.json',m)
 used=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
 if used>64<<20:raise ValueError('stage64MiB aggregate')
 result={'status':'PASS_FIXED_THREE_ROUND_INIT_STAGE_ONLY','manifest':ref(out/'manifest.json'),'overlay':ref(output),'collector':ref(collector),'original_collector':b['sources']['compiled_collector'],'parent_manifest':b['sources']['parent_manifest'],'base_prefix_sha256':producer.sha(base),'base_prefix_bytes':n,'only_changed_member':'init','record_count':len(records),'member_count':len(final),'header_proof':headers,'all_original_order_and_metadata_preserved':True,'pair_rounds':3,'stage_bytes':used,'guest_runs':0,'application_launches':0,'quota_credit':False}
 js(out/'stage-result.json',result);print(json.dumps({k:result[k] for k in ('status','record_count','member_count','stage_bytes','guest_runs')}))
if __name__=='__main__':main()
