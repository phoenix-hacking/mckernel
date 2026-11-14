#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,os,pathlib,subprocess,sys,tempfile
O=pathlib.Path(__file__).resolve().parent;work=pathlib.Path(tempfile.mkdtemp(prefix='json-fixture-',dir=O));root=work/'root';root.mkdir(mode=0o755);os.chmod(root,0o755)
good=b'{"base_root_mode":"0755","base_members":[],"additions":[]}'
cases={'valid':(good,True),'duplicate_top':(b'{"base_root_mode":"0700","base_root_mode":"0755","base_members":[],"additions":[]}',False),'duplicate_nested':(b'{"base_root_mode":"0755","base_members":[{"path":"first","path":"second","type":"file","mode":"0644","bytes":0,"sha256":"'+b'0'*64+b'"}],"additions":[]}',False),'duplicate_digest':(b'{"base_root_mode":"0755","base_members":[{"path":"x","type":"file","mode":"0644","bytes":0,"sha256":"'+b'0'*64+b'","sha256":"'+b'1'*64+b'"}],"additions":[]}',False)}
results=[]
for program in [O/'verify_scripts_view.py',O.parent/'m14-scripts-overlay-verifier-1/verify_scripts_view.py']:
 for name,(data,ok) in cases.items():
  path=work/(program.parent.name+'-'+name+'.json');path.write_bytes(data);cmd=[sys.executable,'-B',str(program),'--manifest',str(path),'--manifest-sha256',hashlib.sha256(data).hexdigest(),'--root',str(root)];r=subprocess.run(cmd,capture_output=True,text=True);assert (r.returncode==0)==ok,(program,name,r.stdout,r.stderr)
  if not ok:assert 'duplicate JSON key' in r.stderr,(name,r.stderr)
  results.append({'program':str(program),'case':name,'argv':cmd,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
(work/'RESULTS.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS both predecessor and successor reject 3 raw duplicate-key JSON cases with matching digest; valid fixture passes; evidence at',work)
