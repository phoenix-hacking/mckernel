#!/usr/bin/python3
import argparse,ast,hashlib,importlib.util,json,os,sys
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('actual',BASE/'exact120.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(exist_ok=False);results=[]
 rows=json.loads(m.MANIFEST.read_text())['rows'];row=rows[0];selected=[row];r=row['restoration'];keys=sorted((r['git_blob'],r['git_commit']));data=('\n'.join(keys)+'\n').encode()
 good=''.join(k+' '+('blob '+str(r['size']) if k==r['git_blob'] else 'commit 1')+'\n' for k in keys).encode()
 def check(name,fn,expected=None):
  error=None
  try:value=fn()
  except Exception as e:error=repr(e)
  ok=error is None if expected is None else error is not None and expected in error
  results.append({'case':name,'status':'PASS' if ok else 'FAIL','error':error});assert ok,results[-1]
 check('ordinary-real-Git-two-object-headers-no-bodies',lambda:m.git_available(selected))
 owner=m.git_owner_identity();captured=[]
 def effectstub(argv,inputdata=None):
  captured.append(argv);assert inputdata==data
  assert argv==['/usr/bin/setpriv','--reuid=1000','--regid=1000','--clear-groups','--no-new-privs','/usr/bin/git','-C',str(m.REPO),'cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'];return good
 with patch.object(m.os,'getuid',return_value=0),patch.object(m.os,'geteuid',return_value=0),patch.object(m,'run',side_effect=effectstub):check('root-branch-exact-drop-argv-effectstub',lambda:m.git_available(selected))
 with patch.object(m.os,'geteuid',return_value=123):check('mixed-identity-refusal',m.git_metadata_argv,'credentials unsupported')
 with patch.object(m,'git_owner_identity',side_effect=[owner,owner+[('CHANGED',)]]),patch.object(m,'run',return_value=good):check('post-Git-owner-path-drift-refusal',lambda:m.git_available(selected),'owner/path raced')
 actual=m.os.fstat
 def badowner(fd):
  s=actual(fd)
  class Fake:pass
  f=Fake()
  for k in ('st_dev','st_ino','st_uid','st_gid'):setattr(f,k,getattr(s,k))
  f.st_uid=123;return f
 with patch.object(m.os,'fstat',side_effect=badowner):check('repository-owner-refusal',m.git_owner_identity,'owner/directory identity changed')
 with patch.object(m,'run',return_value=b''):check('missing-object-census-refusal',lambda:m.git_available(selected),'Git object census')
 with patch.object(m,'run',return_value=good.replace(b' blob ',b' tree ')):check('wrong-object-type-refusal',lambda:m.git_available(selected),'Git object unavailable')
 old=ast.parse((BASE/'source-a75-attempt5-git-failure/exact120.py').read_text());new=ast.parse((BASE/'exact120.py').read_text());func=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)}
 of,nf=func(old),func(new);changed=[k for k in of if of[k]!=nf.get(k)];assert changed==['git_available'],changed
 result={'status':'PASS_GIT_OWNER_METADATA_BOUNDARY','checks':results,'source_sha256':hashlib.sha256((BASE/'exact120.py').read_bytes()).hexdigest(),'changed_existing_functions':changed,'added_functions':sorted(set(nf)-set(of)),'root_branch_argv':captured,'root_execution':False,'blob_bodies_read':False,'ordinary_selected_blob':r['git_blob'],'ordinary_selected_commit':r['git_commit'],'version':sys.version,'interpreter':sys.executable,'limit':'Root setpriv effect boundary is stubbed; requires separate finite privileged Git-only diagnostic before full observer. No root/whole census/deletion.'}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':len(results)}))
if __name__=='__main__':main()
