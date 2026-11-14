"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root data-only fixed selected-source export. No tool/guard/Docker/resource work.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil
D=Path(__file__).resolve().parent
def require(ok,message):
 if not ok:raise ValueError(message)
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(row):
 require(ref(row['path'])==row,'exact Root/source reference');return json.loads(Path(row['path']).read_bytes())
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root-bindings',required=True);a.add_argument('--root-bindings-sha256',required=True);args=a.parse_args();qpath=Path(args.root_bindings).resolve();require(ref(qpath)['sha256']==args.root_bindings_sha256,'Root binding exactbytes');q=json.loads(qpath.read_bytes());require(q['author']=='/root','Root authored source-only action')
 planref=ref(D/'CURRENT-SOURCE-EXPORT-PLAN.NOT-AUTHORITY.json');plan=checked(planref);adoption=checked(q['source_adoption'])
 require(adoption['author']=='/root' and adoption['adopted'] is True and adoption['source_export_plan']==planref,'genuine exact Root selective adoption required')
 changes=checked(plan['selective_write_set'])['changes']
 for row in changes:
  canonical=Path('/home/holden/mckernel')/row['relative'];r=ref(canonical);require(r['bytes']==row['postimage']['bytes'] and r['sha256']==row['postimage']['sha256'],'actual current four-path selective adoption')
 root=Path(plan['export_root']);require(not os.path.lexists(root),'fresh private closed export only')
 require(q['source_export_root']==str(root),'literal planned export root')
 for row in plan['records']:
  rel=Path(row['relative']);require(not rel.is_absolute() and '..' not in rel.parts,'exact relative source path')
  if row['type']=='file':require(ref(row['source']['path'])==row['source'],'source bytes changed before materialization')
 root.mkdir(mode=0o700)
 for row in plan['records']:
  out=root/row['relative'];out.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
  if row['type']=='directory':out.mkdir(mode=0o755,exist_ok=True)
  elif row['type']=='symlink':os.symlink(row['link_target'],out)
  else:
   with out.open('xb') as f:f.write(Path(row['source']['path']).read_bytes())
   os.chmod(out,row['mode'])
 require({str(p.relative_to(root)) for p in root.rglob('*')}=={r['relative'] for r in plan['records']},'complete exact source closure')
 for row in plan['records']:
  p=root/row['relative']
  if row['type']=='file':
   r=ref(p);require(r['bytes']==row['source']['bytes'] and r['sha256']==row['source']['sha256'],'readback exact file');os.chmod(p,row['mode']&0o555)
  elif row['type']=='symlink':require(os.readlink(p)==row['link_target'],'literal link readback')
 for p in sorted([p for p in root.rglob('*') if p.is_dir() and not p.is_symlink()],key=lambda p:len(p.parts),reverse=True):os.chmod(p,0o555)
 os.chmod(root,0o555)
 result=dict(scope=plan['scope'],author='/root',status='ACTUAL_DATA_ONLY_CURRENT_BFD_SOURCE_EXPORTED_NOT_RUNTIME_AUTHORITY',runtime_authority=None,source_export_plan=planref,source_adoption=q['source_adoption'],export_root=str(root),records=len(plan['records']),exact_closed_map=True,source_binding=ref(qpath))
 with (D/'ROOT-ACTUAL-CURRENT-SOURCE-EXPORT.json').open('x') as out:json.dump(result,out,indent=2);out.write('\n')
 print(json.dumps(result))
if __name__=='__main__':main()
