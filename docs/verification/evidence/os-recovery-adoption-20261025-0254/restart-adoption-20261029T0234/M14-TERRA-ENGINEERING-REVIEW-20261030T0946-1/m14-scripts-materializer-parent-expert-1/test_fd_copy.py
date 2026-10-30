#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,importlib.util,json,os,pathlib,tempfile
O=pathlib.Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('fdmaterializer',O/'materializer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
work=pathlib.Path(tempfile.mkdtemp(prefix='fixtures-',dir=O));h=lambda b:hashlib.sha256(b).hexdigest();results=[]
def fixture(name):
 d=work/name;d.mkdir();src=d/'src';src.mkdir();src.chmod(0o751);sub=src/'sub';sub.mkdir();sub.chmod(0o750)
 f=src/'base';f.write_bytes(b'old');f.chmod(0o640);g=sub/'x';g.write_bytes(b'nested');g.chmod(0o644);inputs=d/'inputs';inputs.mkdir();add=[]
 for i in range(6):
  v=('x'+str(i)).encode();p=inputs/('candidate'+str(i));p.write_bytes(v);p.chmod(0o644);add.append({'path':'new'+str(i),'type':'file','mode':'0644','bytes':len(v),'sha256':h(v),'source_candidate':str(p)})
 doc={'base_root_mode':'0751','base_members':[{'path':'base','type':'file','mode':'0640','bytes':3,'sha256':h(b'old')},{'path':'sub','type':'directory','mode':'0750'},{'path':'sub/x','type':'file','mode':'0644','bytes':6,'sha256':h(b'nested')}],'additions':add};return d,src,d/'dest',doc
cases={'success':None,'wrong_hash':'source content mismatch: new1','wrong_mode':'mode mismatch sub','existing':'destination already exists','extra_source':'unexpected path unlisted','collision':'duplicate path','addition_symlink':'source file type/mode/size: new0','five':'exact six top-level file additions','source_parent_symlink':'non-directory or symlink component','source_intermediate_symlink':'non-directory or symlink component: sub','source_intermediate_replace':'directory identity mismatch: sub','dest_intermediate_replace':'directory identity mismatch: sub','checker_hash':'checker hash or stability mismatch','checker_noop':'checker success semantics mismatch'}
for name,expected in cases.items():
 d,src,dst,doc=fixture(name);old_walk=m._relative_dir;old_load=m._load_checker;old_sha=m._FD_CHECKER_SHA
 try:
  if name=='wrong_hash':doc['additions'][1]['sha256']='0'*64
  if name=='wrong_mode':doc['base_members'][1]['mode']='0700'
  if name=='existing':dst.mkdir()
  if name=='extra_source':(src/'unlisted').write_bytes(b'x')
  if name=='collision':doc['additions'][0]['path']='base'
  if name=='addition_symlink':
   x=pathlib.Path(doc['additions'][0]['source_candidate']);alias=x.parent/'alias';os.symlink(x,alias);doc['additions'][0]['source_candidate']=str(alias)
  if name=='five':doc['additions'].pop()
  if name=='source_parent_symlink':alias=d/'source-link';os.symlink(src,alias);src=alias
  if name in ('source_intermediate_symlink','source_intermediate_replace','dest_intermediate_replace'):
   source_id=os.stat(src).st_ino;triggered=[False]
   def altered(rootfd,parts,pins):
    if parts==['sub'] and pins is not None and not triggered[0] and ((os.fstat(rootfd).st_ino==source_id)==(name!='dest_intermediate_replace')):
     triggered[0]=True;tree=src if name!='dest_intermediate_replace' else dst;os.rename(tree/'sub',tree/'sub-saved')
     if name=='source_intermediate_symlink':os.symlink('sub-saved',tree/'sub')
     else:
      (tree/'sub').mkdir();(tree/'sub').chmod(0o750)
      if name=='source_intermediate_replace':(tree/'sub'/'x').write_bytes(b'nested');(tree/'sub'/'x').chmod(0o644)
    return old_walk(rootfd,parts,pins)
   m._relative_dir=altered
  if name=='checker_hash':m._FD_CHECKER_SHA='0'*64
  if name=='checker_noop':
   def fake():
    ns=old_load();ns['check_fd']=lambda fd,mode,entries:None;return ns
   m._load_checker=fake
  try:n=m.copy_scripts_body(src,dst,doc)
  except Exception as e:
   assert expected is not None and expected in str(e),(name,type(e).__name__,str(e),expected)
   if name in ('source_intermediate_symlink','source_intermediate_replace','dest_intermediate_replace'):assert triggered[0]
   results.append({'case':name,'outcome':'rejected','type':type(e).__name__,'error':str(e),'destination_retained':dst.exists()})
  else:
   assert expected is None and n==9,(name,n);assert dst.stat().st_mode&0o7777==0o751 and (dst/'sub').stat().st_mode&0o7777==0o750
   results.append({'case':name,'outcome':'pass','entries':n})
 finally:m._relative_dir=old_walk;m._load_checker=old_load;m._FD_CHECKER_SHA=old_sha
(work/'RESULTS.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS',len(results),'actual body cases with exact failure-family checks; fixtures retained at',work)
