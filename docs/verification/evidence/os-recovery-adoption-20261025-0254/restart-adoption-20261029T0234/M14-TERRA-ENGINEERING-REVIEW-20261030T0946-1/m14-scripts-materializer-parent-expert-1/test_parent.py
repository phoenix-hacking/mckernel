#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,importlib.util,json,os,pathlib,tempfile
O=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('materializer',O/'materializer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
work=pathlib.Path(tempfile.mkdtemp(prefix='parent-fixtures-',dir=O));results=[]
h=lambda data:hashlib.sha256(data).hexdigest()
def fixture(name):
 d=work/name;d.mkdir();src=d/'src';src.mkdir();src.chmod(0o751);(src/'base').write_bytes(b'abc');(src/'base').chmod(0o644)
 inputs=d/'inputs';inputs.mkdir();add=[]
 for i in range(6):
  data=str(i).encode();p=inputs/str(i);p.write_bytes(data);p.chmod(0o644);add.append(dict(path='new'+str(i),type='file',mode='0644',bytes=1,sha256=h(data),source_candidate=str(p)))
 parent=d/'outer'/'parent';parent.mkdir(parents=True)
 return d,src,parent/'dest',dict(base_root_mode='0751',base_members=[dict(path='base',type='file',mode='0644',bytes=3,sha256=h(b'abc'))],additions=add)
for case in ('baseline','rename_parent_replace','rename_ancestor_replace','rename_parent_symlink','checker_expected_count_fake'):
 d,src,dst,doc=fixture(case);old_copy=m._copy_one;old_load=m._load_checker;trigger=[False]
 try:
  if case.startswith('rename_'):
   def copy(*args):
    old_copy(*args)
    if not trigger[0]:
     trigger[0]=True;target=dst.parent.parent if case=='rename_ancestor_replace' else dst.parent;saved=target.with_name(target.name+'-saved');target.rename(saved)
     if case=='rename_parent_symlink':target.symlink_to(saved, target_is_directory=True)
     else:
      target.mkdir()
      if case=='rename_ancestor_replace':(target/'parent').mkdir()
   m._copy_one=copy
  if case=='checker_expected_count_fake':
   def fake_load():
    ns=old_load();ns['check_fd']=lambda fd,mode,entries:len(entries);return ns
   m._load_checker=fake_load
   def corrupt(*args):
    old_copy(*args)
    if not trigger[0]:
     trigger[0]=True;fd=os.open(args[3],os.O_WRONLY,dir_fd=args[2]);os.write(fd,b'BAD');os.close(fd)
   m._copy_one=corrupt
  try:n=m.copy_scripts_body(src,dst,doc)
  except Exception as e:
   if case in ('rename_parent_replace','rename_ancestor_replace'):assert 'destination ancestor identity mismatch' in str(e),(case,str(e))
   elif case=='rename_parent_symlink':assert 'non-directory or symlink component: parent' in str(e),(case,str(e))
   else:raise
   assert trigger[0];results.append(dict(case=case,outcome='rejected',exception=type(e).__name__,error=str(e)))
  else:
   assert n==7
   if case=='baseline':assert (dst/'base').read_bytes()==b'abc';results.append(dict(case=case,outcome='pass',entries=n))
   elif case=='checker_expected_count_fake':
    assert trigger[0] and (dst/'base').read_bytes()==b'BAD';results.append(dict(case=case,outcome='expected_acceptance_of_corruption_under_monkeypatch',entries=n))
   else:raise AssertionError((case,'wrong success'))
 finally:m._copy_one=old_copy;m._load_checker=old_load
(work/'RESULTS.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS',len(results),'cases; retained fixtures',work)
