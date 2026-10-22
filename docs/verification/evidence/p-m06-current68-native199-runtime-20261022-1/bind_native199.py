"""Join a genuine raw stage through the existing overlay transformer.

No guest/root effects. Failed outputs are retained; every publication is exclusive.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,stat
R=Path(__file__).resolve().parent;N=R.parent
STAGE=N/'filled-stage-execution-1/nproc-profile-correction-1/actual-selfexec-199-stage-2'
DATA_SHA='5736ae9156826dfe24cc595bfe915bde22e444c6eb346e7b62efbc24690164e4'
MAP_SHA='5072b59eea21eaeb6a952d0cb3ff58a0d3a7db4f5cf9a38eabfa1befc4f5ce11'
INVENTORY_SHA='c12023f653da7bb466af97b1c7bd296966892979159e062e1b65c83c62f3c7c2'
def need(ok,why):
 if not ok:raise ValueError(why)
def checked_json(path,digest):
 raw=Path(path).read_bytes();need(hashlib.sha256(raw).hexdigest()==digest,'fixed input identity');return json.loads(raw)
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def ref(path,digest=None):
 p=Path(path);need(p.is_absolute() and p.resolve(strict=True)==p and not p.is_symlink(),'canonical file ref');s=p.stat();need(stat.S_ISREG(s.st_mode),'regular file ref')
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 need(digest is None or h.hexdigest()==digest,'file reference hash')
 return dict(path=str(p),sha256=h.hexdigest(),size=s.st_size,mode=s.st_mode)
def write_new(path,value):
 with Path(path).open('x')as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def validate_stage(stage,data,replacements,inventory):
 need(set(stage)=={'schema_version','kind','base_root','payload','collector','source_inventory','staged_inventory','replacements','artifacts','tools'},'raw stage schema')
 need(stage['schema_version']==1 and stage['kind']=='native-diagnostic-initramfs','raw stage kind')
 need(stage['base_root']==inventory['base_root'] and stage['source_inventory']==inventory['source_inventory'],'actual admitted source inventory')
 need(stage['payload']=={k:data['cases'][0]['binary'][k] for k in ('path','sha256')} and stage['collector']=={k:data['collector'][k] for k in ('path','sha256')},'exact selected app/collector tuple')
 need(set(stage['replacements'])==set(replacements),'exact replacement names')
 for name,expected in replacements.items():
  actual=stage['replacements'][name]
  need(all(actual[k]==v for k,v in expected.items()),'exact replacement tuple '+name)
  need(all(actual['final_'+k]==expected[k] for k in ('sha256','size','mode')),'raw replacement final tuple '+name)
 need(set(stage['artifacts'])=={'initramfs.cpio','initramfs.cpio.gz'},'raw archive names')
 need(stage['tools']=={'cpio':'/usr/bin/cpio','gzip':'/usr/bin/gzip'},'raw tool tuple')
 rows={r['path']:r for r in stage['staged_inventory']};need(len(rows)==len(stage['staged_inventory']),'duplicate staged member')
 for name,expected in replacements.items():
  need(name in rows and rows[name]['type']=='file' and all(rows[name][k]==expected[k] for k in ('sha256','size','mode')),'staged artifact tuple '+name)
 return rows

def build():
 data=checked_json(N/'CURRENT68-STAGE-INPUT-DATA.json',DATA_SHA);repl=checked_json(N/'REPLACEMENTS.ACTUAL-CURRENT68-AND-IMAGE.json',MAP_SHA);inventory=checked_json(N/'ACTUAL-BASE-INVENTORY-ADMISSION-2.json',INVENTORY_SHA)
 need(STAGE.resolve(strict=True)==STAGE,'canonical actual stage');raw=STAGE/'manifest.json';stage=json.loads(raw.read_text());rows=validate_stage(stage,data,repl,inventory)
 base=ref(STAGE/'initramfs.cpio.gz',stage['artifacts']['initramfs.cpio.gz']);cpio=ref(STAGE/'initramfs.cpio',stage['artifacts']['initramfs.cpio'])
 overlay=load('exact_runtime_overlay',R/'native_diagnostic_overlay.py')
 output=R/'actual-native199-overlay-1.cpio.gz';overlay_receipt=R/'actual-native199-overlay-1.manifest.json';runtime_path=R/'GENERATED-NATIVE199-MANIFEST.json'
 need(all(not os.path.lexists(p) for p in (output,overlay_receipt,runtime_path)),'fresh derived output namespaces')
 b=data['cases'][0]['binary'];c=data['collector'];m=data['launcher']
 result=overlay.build_overlay(base['path'],b['path'],c['path'],m['path'],str(output),collector_sha256=c['sha256'],mcexec_sha256=m['sha256'],payload_sha256=b['sha256'],base_sha256=base['sha256'],base_size=base['size'],base_cpio_sha256=cpio['sha256'],base_cpio_size=cpio['size'])
 # Prove all old members survived and only the exact permitted overlay records changed.
 need(set(result['final_map'])==set(rows),'complete staged/final namespace join')
 for name,row in rows.items():
  out=result['final_map'][name];need(out['sha256']==(row['sha256'] if row['type']=='file' else hashlib.sha256(b'').hexdigest()) and out['size']==(row['size'] if row['type']=='file' else 0) and out['mode']==(stat.S_IFDIR if row['type']=='dir' else stat.S_IFREG)|row['mode'],'staged/final byte and mode join '+name)
 write_new(overlay_receipt,result)
 bybase={x['path']:x for x in inventory['source_inventory']};br=Path(inventory['base_root'])
 artifacts={'bzImage':{'mode':33188,'path':'/home/holden/mckernel-work/scratch/native-artifact-revalidate-authority3-20261017-1/payload/native-rust-build-evidence/bzImage','sha256':'032653ee0661b059c325e2a0911a9d492805f1a889c4df515473d69a8be105bc','size':16130048},'initramfs':base,'root_base':base}
 for name,member in (('native_boot','bin/native-boot'),('loader','lib64/ld-linux-x86-64.so.2'),('libc','lib64/libc.so.6')):artifacts[name]=ref(br/member,bybase[member]['sha256'])
 artifacts.update(mckernel_image=ref(repl['images/mckernel.img']['path'],repl['images/mckernel.img']['sha256']),mcexec=ref(m['path'],m['sha256']),payload=ref(b['path'],b['sha256']))
 case=data['cases'][0];oracle=case['oracle'];stdout=Path(oracle['stdout']['path']).read_bytes();stderr=Path(oracle['stderr']['path']).read_bytes();need(len(stdout)==199 and hashlib.sha256(stdout).hexdigest()==oracle['stdout']['sha256'] and stderr==b'','strict199 oracle')
 manifest=dict(schema_version=1,kind='native-diagnostic-manifest',case_id=case['id'],artifacts=artifacts,modules=[ref(repl['modules/'+x]['path'],repl['modules/'+x]['sha256'])for x in ('ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko')],profile=dict(name='native-diagnostic-4vcpu-8192mib',memory_mib=8192,vcpus=4,numa_nodes=2),payload=dict(cwd=case['cwd'],argv=case['argv'],env=case['env'],oracle=dict(stdout_hex=stdout.hex(),stderr_hex=stderr.hex(),exit_code=37),stdout_limit_bytes=1024,stderr_limit_bytes=1024),staging=dict(base_initramfs=base,derived_initramfs=ref(output,result['output_sha256']),collector=ref(c['path'],c['sha256']),overlay_source=ref(R/'native_diagnostic_overlay.py'),overlay_manifest=ref(overlay_receipt)))
 diagnostic=load('exact_runtime_diagnostic',R/'native_diagnostic.py');diagnostic._validate_manifest(manifest)
 write_new(runtime_path,manifest)
 return manifest
if __name__=='__main__':build()
