"""Single app-only offline stage; requires dispatcher ordinary grant. No runtime launch.
Functional OS/apps plus compute-C retirement into Rust/reviewed assembly.
"""
from pathlib import Path
import ast, copy, hashlib, importlib.util, json, os
D=Path(__file__).resolve().parent

def exact(row):
 p=Path(row['path']);a=p.lstat();raw=p.read_bytes();b=p.lstat()
 assert (a.st_dev,a.st_ino,a.st_mode,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_dev,b.st_ino,b.st_mode,b.st_size,b.st_mtime_ns,b.st_ctime_ns)
 assert a.st_mode==row['mode'] and len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 return raw

def load(name,row):
 exact(row);s=importlib.util.spec_from_file_location(name,row['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 cfg=json.loads((D/'INPUTS.json').read_bytes())
 for r in cfg.values():exact(r)
 parent=json.loads(exact(cfg['parent']));engine=load('accepted_derive',cfg['derive_engine']);ov=load('accepted_overlay',cfg['overlay_engine'])
 # Only change accepted retained_map's declared data allowlist; its function body is unchanged.
 assert engine.CHANGED==frozenset(('init',));engine.CHANGED=frozenset(('apps/app',))
 out=D/'ordinary-stage-1';assert not os.path.lexists(out);out.mkdir(mode=0o700)
 app=D/'ordinary-compile-1/app';assert app.is_file() and app.lstat().st_mode==0o100755
 payload=engine.ref(app)
 base=cfg['base'];old=json.loads(exact(cfg['old_overlay']))['final_map']
 archive=out/'clone3-io.cpio.gz'
 overlay=engine.derive(ov,base,payload,cfg['collector'],parent['artifacts']['mcexec'],archive,old)
 assert overlay['final_map']['init']==old['init']
 engine.js(out/'overlay-manifest.json',overlay)
 manifest=copy.deepcopy(parent);manifest['case_id']='practical.process.clone3-io-unsupported'
 manifest['payload']['oracle']={'stdout_hex':(D/'expected.stdout').read_bytes().hex(),'stderr_hex':'','exit_code':0}
 manifest['artifacts']['payload']=payload
 manifest['artifacts']['initramfs']=manifest['artifacts']['root_base']=base
 manifest['staging']=dict(base_initramfs=base,derived_initramfs=engine.ref(archive),collector=cfg['collector'],overlay_source=cfg['overlay_engine'],overlay_manifest=engine.ref(out/'overlay-manifest.json'))
 # Accepted strict validator unchanged; replace only its single exact case-binding literal.
 raw=exact(cfg['evaluator']).decode();tree=ast.parse(raw)
 nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='M03_CASE_BINDING' for t in n.targets)]
 assert len(nodes)==1;node=nodes[0];binding=ast.literal_eval(node.value)
 binding.update(case_id=manifest['case_id'],payload_artifact=payload,payload=manifest['payload'],accepted_stage_base=base)
 lines=raw.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=['M03_CASE_BINDING = '+repr(binding)+'\n']
 variant=''.join(lines);newtree=ast.parse(variant);newnode=[n for n in newtree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='M03_CASE_BINDING' for t in n.targets)][0]
 node.value=copy.deepcopy(newnode.value);assert ast.dump(tree,include_attributes=False)==ast.dump(newtree,include_attributes=False)
 engine.write(out/'native_diagnostic.py',variant.encode())
 nd=load('clone3_exact_case',engine.ref(out/'native_diagnostic.py'));nd._validate_manifest(manifest)
 engine.js(out/'manifest.json',manifest);assert nd.load_manifest(str(out/'manifest.json'))==manifest
 engine.js(out/'stage-result.json',dict(status='OFFLINE_STAGE_ONLY',manifest=engine.ref(out/'manifest.json'),payload=payload,collector=cfg['collector'],permitted_final_changes=['apps/app'],original_prefix_unchanged=True,guest_runs=0,native_acceptance=False,normalization=None))
 assert sum(p.stat().st_size for p in out.iterdir())<64<<20
 print(json.dumps(dict(status='OFFLINE_STAGE_ONLY',guest_runs=0)))
if __name__=='__main__':main()
