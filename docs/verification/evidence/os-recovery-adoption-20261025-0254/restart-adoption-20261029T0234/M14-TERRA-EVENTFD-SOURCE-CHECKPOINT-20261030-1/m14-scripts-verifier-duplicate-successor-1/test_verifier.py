#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,os,pathlib,subprocess,sys,tempfile
O=pathlib.Path(__file__).resolve().parent; work=pathlib.Path(tempfile.mkdtemp(prefix='fixture-',dir=O)); script=O/'verify_scripts_view.py'
def h(b):return hashlib.sha256(b).hexdigest()
manifest={'base_root_mode':'0755','base_members':[{'path':'alpha','type':'file','mode':'0644','bytes':3,'sha256':h(b'one')},{'path':'nested','type':'directory','mode':'0755'},{'path':'nested/base','type':'file','mode':'0644','bytes':3,'sha256':h(b'two')}],'additions':[{'path':'extra','type':'file','mode':'0644','bytes':5,'sha256':h(b'three')}]}
def make(name,variant):
 root=work/name;root.mkdir(mode=0o755);os.chmod(root,0o755);(root/'nested').mkdir(mode=0o755);os.chmod(root/'nested',0o755)
 def file(p,data,perms=0o644):p.write_bytes(data);os.chmod(p,perms)
 if variant!='missing':file(root/'alpha',b'xxx' if variant=='bad_hash' else b'one',0o600 if variant=='bad_mode' else 0o644)
 file(root/'nested/base',b'two')
 if variant=='symlink':os.symlink('alpha',root/'extra')
 elif variant=='hardlink':os.link(root/'alpha',root/'extra')
 else:file(root/'extra',b'three')
 if variant=='external_hardlink':os.link(root/'alpha',work/(name+'-outside'))
 if variant=='extra':file(root/'surplus',b'x')
 if variant=='root_mode':os.chmod(root,0o700)
 if variant=='root_symlink':link=work/(name+'-link');os.symlink(root,link);return link
 return root
results=[]
for name,variant,ok in [('good','good',True),('missing','missing',False),('extra','extra',False),('mode','bad_mode',False),('hash','bad_hash',False),('symlink','symlink',False),('hardlink','hardlink',False),('outside_hardlink','external_hardlink',False),('root_mode','root_mode',False),('root_symlink','root_symlink',False)]:
 root=make(name,variant);m=work/(name+'.json');data=json.dumps(manifest,sort_keys=True).encode();m.write_bytes(data);cmd=[sys.executable,'-B',str(script),'--manifest',str(m),'--manifest-sha256',h(data),'--root',str(root)];r=subprocess.run(cmd,capture_output=True,text=True);assert (r.returncode==0)==ok,(name,r.returncode,r.stderr);results.append({'case':name,'argv':cmd,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
for name, mutate in [('duplicate',lambda m:m['base_members'].append(m['base_members'][0])),('manifest_symlink',lambda m:m['base_members'][0].update(type='symlink')),('dotdot',lambda m:m['base_members'][0].update(path='../alpha'))]:
 mobj=json.loads(json.dumps(manifest));mutate(mobj);data=json.dumps(mobj,sort_keys=True).encode();p=work/(name+'.json');p.write_bytes(data);cmd=[sys.executable,'-B',str(script),'--manifest',str(p),'--manifest-sha256',h(data),'--root',str(work/'good')];r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode!=0,(name,r.stdout);results.append({'case':name,'argv':cmd,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
cmd=[sys.executable,'-B',str(script),'--manifest',str(work/'good.json'),'--manifest-sha256','0'*64,'--root',str(work/'good')];r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode!=0;results.append({'case':'bad_manifest_digest','argv':cmd,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
(work/'RESULTS.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS',len(results),'actual checker cases; fixtures retained at',work)
