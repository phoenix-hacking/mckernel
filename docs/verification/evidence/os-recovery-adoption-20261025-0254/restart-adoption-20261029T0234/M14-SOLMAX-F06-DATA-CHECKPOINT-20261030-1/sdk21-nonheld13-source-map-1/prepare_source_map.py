#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One-shot source-map construction. No validator, compiler, Docker, native or owner call.
"""
import hashlib,json,os,stat,sys,traceback
from pathlib import Path,PurePosixPath
B=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
OUT=B/'sdk21-nonheld13-source-map-1'; PROFILE=B/'sdk21-nonheld13-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json'
P_SHA='3e6d2491c509790cea3f2de035e2171858d5efbcb9cc0dca8cc3aaea15007926'; Q_SHA='6cce26d01ae0810160a8964262b6dd5bf8aca09bf88ff8f56cae3b3e42eb40dd'
VALIDATOR=B/'sdk21-nonheld13-input-validation-source-1/sdk13_input_validation.py'
LOCK=Path('/home/holden/mckernel/host-kernel/rocky/toolchain-lock.json')
JOURNAL=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/source-materialization-current290-ihk3114-attempt-1/materialization-journal.jsonl')
RESULT=JOURNAL.parent/'MATERIALIZATION-RESULT.json'; MANIFEST=JOURNAL.parent.parent/'source-inputs.CURRENT290-QUALIFIED-IHK3114.json'

def ident(s):return {'device':s.st_dev,'inode':s.st_ino,'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'nlink':s.st_nlink,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
def read_file(path):
 p=Path(path); fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode):raise ValueError('not regular: '+str(p))
  dig=hashlib.sha256()
  while True:
   b=os.read(fd,1048576)
   if not b:break
   dig.update(b)
  after=os.fstat(fd);named=os.lstat(p)
  if ident(before)!=ident(after) or ident(before)!=ident(named):raise ValueError('file changed: '+str(p))
  return {'path':str(p),'bytes':before.st_size,'sha256':dig.hexdigest(),'identity':ident(before)}
 finally:os.close(fd)
def output(name,obj):
 p=OUT/name
 with p.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def no_symlink_parents(p):
 for part in (p,*p.parents):
  if stat.S_ISLNK(os.lstat(part).st_mode):raise ValueError('symlink path component: '+str(part))
def actual_tree(root,target):
 root=Path(root);no_symlink_parents(root); rs=os.lstat(root)
 if not stat.S_ISDIR(rs.st_mode):raise ValueError('root not directory')
 entries=[]; ledger=[]
 for current,dirs,files in os.walk(root,topdown=True,followlinks=False):
  dirs.sort();files.sort()
  for name in dirs+files:
   path=Path(current)/name; rel=path.relative_to(root).as_posix(); st=os.lstat(path)
   if stat.S_ISLNK(st.st_mode):
    dest=os.readlink(path);resolved=path.resolve(strict=True)
    if resolved!=root and root not in resolved.parents:raise ValueError('escaping symlink: '+str(path))
    row={'relative':rel,'kind':'symlink','target':dest}; ledger.append({'target':target+'/'+rel,'physical':str(path),'kind':'symlink','link_target':dest,'identity':ident(st)})
   elif stat.S_ISDIR(st.st_mode):
    row={'relative':rel,'kind':'dir'};ledger.append({'target':target+'/'+rel,'physical':str(path),'kind':'dir','identity':ident(st)})
   elif stat.S_ISREG(st.st_mode):
    ref=read_file(path);row={'relative':rel,'kind':'file','bytes':ref['bytes'],'sha256':ref['sha256']};ledger.append({'target':target+'/'+rel,'physical':str(path),'kind':'file',**ref})
   else:raise ValueError('unsupported: '+str(path))
   entries.append(row)
 if ident(rs)!=ident(os.lstat(root)):raise ValueError('root changed during scan: '+str(root))
 return {'root':str(root),'entries':entries}, {'target':target,'physical':str(root),'kind':'root','identity':ident(rs)},ledger

def source_from_retained(root):
 # Reuse retained source hashes/sizes and symlink targets without rehashing or
 # re-inventorying the 6,153 individual files. Directory traversal only adds dirs.
 sr=read_file(MANIFEST)
 if sr['sha256']!='3a0653623cc1cdb7ebb0e217274ded31ea8fea5068140af4884c273b493b5018':raise ValueError('retained manifest changed')
 mr=read_file(RESULT);jr=read_file(JOURNAL);m=json.loads(MANIFEST.read_bytes());receipt=json.loads(RESULT.read_bytes())
 if receipt['source_manifest_sha256']!=sr['sha256'] or receipt['source_root']!=root or receipt['source_entries']!=6153:raise ValueError('retained materialization binding differs')
 rootp=Path(root);no_symlink_parents(rootp);rs=os.lstat(rootp); rows=[]; seen=set(); syms=0
 for raw in JOURNAL.read_bytes().splitlines():
  e=json.loads(raw);rel=e['path']; p=PurePosixPath(rel)
  if p.is_absolute() or str(p)!=rel or rel in seen or '..' in p.parts:raise ValueError('retained source path invalid')
  seen.add(rel)
  if e['kind']=='file':
   expected=m['materialized_repository_files'].get(rel)
   if expected is None:expected=m['retained_ihk_git_metadata'].get(rel,{}).get('sha256')
   if expected!=e['sha256'] or m['materialized_kinds'].get(rel)!='file':raise ValueError('retained source file evidence mismatch: '+rel)
   rows.append({'relative':rel,'kind':'file','bytes':e['size'],'sha256':e['sha256']})
  elif e['kind']=='symlink':
   if m['materialized_symlinks'].get(rel,{}).get('target')!=e['target']:raise ValueError('retained symlink mismatch')
   path=rootp/rel
   if not path.is_symlink() or os.readlink(path)!=e['target']:raise ValueError('current symlink differs')
   resolved=path.resolve(strict=True)
   if resolved!=rootp and rootp not in resolved.parents:raise ValueError('escaping symlink')
   rows.append({'relative':rel,'kind':'symlink','target':e['target']});syms+=1
  else:raise ValueError('bad retained kind')
 if len(rows)!=6153 or syms!=49:raise ValueError('retained source cardinality')
 dirs=set()
 for row in rows:
  p=PurePosixPath(row['relative']).parent
  while str(p)!='.':dirs.add(str(p));p=p.parent
 # Empty directories are not in retained file manifest. Read directory topology,
 # never file bytes or individual file metadata in this tree.
 for current,names,_ in os.walk(rootp,topdown=True,followlinks=False):
  for name in names:
   path=Path(current)/name
   if not path.is_symlink():dirs.add(path.relative_to(rootp).as_posix())
 if dirs & seen:raise ValueError('source dir and retained entry collide')
 rows.extend({'relative':x,'kind':'dir'} for x in sorted(dirs))
 if ident(rs)!=ident(os.lstat(rootp)):raise ValueError('source root changed')
 return {'root':root,'entries':rows},{'target':'/src','physical':root,'kind':'root','identity':ident(rs)}, {'manifest':sr,'materialization_result':mr,'journal':jr,'note':'Historical retained 6153 file/symlink rows reused; current individual source-file identities/bytes not revalidated here.'}

def main():
 pr=read_file(PROFILE)
 if pr['sha256']!=P_SHA:raise ValueError('SDK13 profile hash mismatch')
 p=json.loads(PROFILE.read_bytes());rows=p['readonly_shared_inputs']+p['readonly_config_and_eight_objects']
 if len(rows)!=29:raise ValueError('expected 29 read-only profile mounts')
 roots={r['container']:r['host'] for r in rows if 'sha256' not in r}
 if set(roots)!={'/src','/src/kernel/rust','/nightly'}:raise ValueError('unexpected tree roots')
 rust=next(c['argv'] for c in p['commands'] if any('mckernel_rust' in a for a in c['argv']) and any('rustc' in a for a in c['argv']))
 if 'f06_debug_constants_candidate' in rust or any('MCKERNEL_RUST_F06_DEBUG_CONSTANTS' in a for c in p['commands'] for a in c['argv']):raise ValueError('frozen SDK13 data selector unexpectedly on')
 source,source_root,provenance=source_from_retained(roots['/src']); rusttree,rustroot,rustledger=actual_tree(roots['/src/kernel/rust'],'/src/kernel/rust')
 if sum(1 for x in rusttree['entries'] if x['kind']=='file')!=156:raise ValueError('Rust mounted file count differs')
 by={r['relative']:r for r in rusttree['entries']}
 for rel,ref in p['source_bindings']['overlay_hashes'].items():
  if rel.startswith('kernel/rust/'):
   sub=rel[len('kernel/rust/'):]
   if by.get(sub,{}).get('sha256')!=ref['sha256']:raise ValueError('Rust overlay mismatch: '+rel)
 output('PARTIAL-SOURCE-RUST.json',{'source':source,'rust':rusttree,'source_root':source_root,'rust_root':rustroot,'rust_identities':rustledger,'provenance':provenance})
 nightly,nightroot,nightledger=actual_tree(roots['/nightly'],'/nightly')
 mountledger=[];inodes=set()
 for row in rows:
  path=Path(row['host']);no_symlink_parents(path);st=os.lstat(path); inode=(st.st_dev,st.st_ino)
  if inode in inodes:raise ValueError('mount inode alias: '+row['container'])
  inodes.add(inode)
  if 'sha256' in row:
   ref=read_file(path)
   if ref['sha256']!=row['sha256'] or ('bytes'in row and ref['bytes']!=row['bytes']):raise ValueError('mount mismatch: '+row['container'])
   mountledger.append({'target':row['container'],'physical':str(path),'readonly':True,'kind':'file',**ref})
  else:mountledger.append({'target':row['container'],'physical':str(path),'readonly':True,'kind':'dir','identity':ident(st)})
 lock=read_file(LOCK)
 if lock['sha256']!=p['image_and_tools']['toolchain_lock_sha256']:raise ValueError('toolchain lock mismatch')
 tool=read_file(p['image_and_tools']['retained_image_tool_manifest']['path'])
 if tool['sha256']!=p['image_and_tools']['retained_image_tool_manifest']['sha256']:raise ValueError('tool manifest mismatch')
 validator=read_file(VALIDATOR)
 data={'schema':'mckernel.sdk13.source-map.v1','profile_sha256':P_SHA,'proposal_sha256':Q_SHA,
       'toolchain_lock':{'path':str(LOCK),'sha256':lock['sha256']},
       'trees':{'/src':source,'/src/kernel/rust':rusttree,'/nightly':nightly}}
 output('SDK13-SOURCE-MAP.PROPOSED.json',data)
 identities={'scope':__doc__.splitlines()[0],'status':'POINT_IN_TIME_SOURCE_DATA_NOT_REVIEW_OR_RELEASE','profile':pr,'validator':validator,'source_provenance':provenance,'root_identities':[source_root,rustroot,nightroot],'rust_tree_identities':rustledger,'nightly_tree_identities':nightledger,'readonly_mount_identities':mountledger,'toolchain_lock':lock,'retained_image_tool_manifest':tool,'source_6153_current_individual_identities':'NOT_COLLECTED_BY_REQUEST; retained file/symlink manifest reused; validator will require current revalidation','image_internal_tools_current':'UNOBSERVED','authority':None}
 output('POINT-IN-TIME-IDENTITIES.json',identities)
 print('SDK13 source map prepared; Rust files',sum(x['kind']=='file' for x in rusttree['entries']),'nightly files',sum(x['kind']=='file' for x in nightly['entries']),'mounts',len(mountledger),'no validator or SDK work executed.')
try:main()
except BaseException as exc:
 try:output('PREPARATION-FAILURE.json',{'result':'FAIL_SOURCE_MAP_NOT_AUTHORITY','error':repr(exc),'traceback':traceback.format_exc()})
 except Exception:pass
 raise
