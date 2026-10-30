#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,os,pathlib,stat
A=pathlib.Path(__file__).resolve().parent.parent;O=pathlib.Path(__file__).resolve().parent
f=A/'m14-assembled-source-view-1/ASSEMBLED-VIEW.NOT-RELEASED.json'
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert digest(f)=='311e4a329f97ce9954ef26ab1d4eefe775953f5c6d6e5b0ff0a9b364add99f1d'
j=json.loads(f.read_text());base=pathlib.Path(j['base_source_candidate'])/'scripts';observed=[]
def sig(st):return(st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
def walk(d,rel):
 before=d.lstat();assert stat.S_ISDIR(before.st_mode)
 for ent in sorted(os.scandir(d),key=lambda x:x.name):
  p=pathlib.Path(ent.path);rp=rel/ent.name;st=p.lstat();item={'path':str(rp),'mode':format(stat.S_IMODE(st.st_mode),'04o')}
  if stat.S_ISDIR(st.st_mode):
   item['type']='directory';observed.append(item);walk(p,rp)
  elif stat.S_ISREG(st.st_mode):
   fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
   try:
    x=os.fstat(fd);assert sig(x)==sig(st),str(p);h=hashlib.sha256()
    while chunk:=os.read(fd,1024*1024):h.update(chunk)
    assert sig(os.fstat(fd))==sig(x),str(p)
   finally:os.close(fd)
   assert sig(p.lstat())==sig(st),str(p);item.update(type='file',bytes=st.st_size,sha256=h.hexdigest());observed.append(item)
  elif stat.S_ISLNK(st.st_mode):item.update(type='symlink',link_target=os.readlink(p));assert sig(p.lstat())==sig(st);observed.append(item)
  else:raise ValueError(('unsupported type',str(p)))
 assert sig(d.lstat())==sig(before),str(d)
walk(base,pathlib.PurePosixPath('.'))
assert len({x['path'] for x in observed})==len(observed)
rootmode=format(stat.S_IMODE(base.lstat().st_mode),'04o');children=j['source_overlay_inputs_in_deterministic_order'];added=[x for x in children if x['relative_to_src'].startswith('scripts/')];other=[x for x in children if not x['relative_to_src'].startswith('scripts/')]
assert len(added)==6 and len(other)==8 and all(x['expected_object_type']=='file' and x['observed_old_parent_target_type']=='absent' for x in added)
existing={x['path'] for x in observed}; additions=[]
for x in added:
 rel=x['relative_to_src'].removeprefix('scripts/');p=pathlib.Path(x['candidate_path']);st=p.lstat();assert '/' not in rel and rel not in existing and stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode)
 h=digest(p);assert h==x['historical_content_sha256'];assert sig(p.lstat())==sig(st)
 additions.append({'path':rel,'type':'file','mode':format(stat.S_IMODE(st.st_mode),'04o'),'bytes':st.st_size,'sha256':h,'source_candidate':str(p),'live_identity':None})
assert len({x['path'] for x in additions})==6 and len(existing | {x['path'] for x in additions})==len(existing)+6
src=next(x for x in j['proposed_final_mounts'] if x['target']=='/src');src['host_candidate']=j['base_source_candidate'];src['source_role']='retained historical base, fresh identity required'
mounts=[src,{'target':'/src/scripts','host_candidate':None,'access':'ro','source_role':'fresh complete immutable scripts directory','live_identity':None}]
for x in other:mounts.append({'target':x['target'],'host_candidate':x['candidate_path'],'access':'ro','source_role':'retained exact overlay candidate','historical_content_sha256':x['historical_content_sha256'],'live_identity':None})
mounts.extend(x for x in j['proposed_final_mounts'] if x['target']!='/src');mounts.sort(key=lambda x:(len(pathlib.PurePosixPath(x['target']).parts),x['target']))
ts=[x['target'] for x in mounts];assert len(ts)==14 and len(ts)==len(set(ts));assert all(x['live_identity'] is None for x in mounts);assert all(x['access']==('rw' if x['target']=='/work' else 'ro') for x in mounts)
assert all(not x.startswith('/src/scripts/') for x in ts) and '/src/scripts' in ts and ts.index('/src')<ts.index('/src/scripts')
record={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing','status':'SOURCE_ONLY_NOT_MATERIALIZED_NOT_RELEASED','authority':None,'previous_design_path':str(f),'previous_design_sha256':digest(f),'base_scripts_candidate':str(base),'base_root_mode':rootmode,'live_identity':None,'inventory_scope':'point-in-time read-only full scripts tree; stability checks are not a global atomic snapshot or proof of immutability','base_members':observed,'additions':additions,'future_mounts_parent_first':mounts,'future_scripts_host':None,'future_scripts_identity':None,'future_scripts_materialization':['Obtain independent admission, exclusive fresh owner and storage resources, with source inputs and final path identities bound.','Create a fresh complete directory by copying the exact inventoried base scripts tree preserving each regular-file content and mode, directory mode and approved symlink literal; do not follow symlinks or hard-link to retained input.','Add the six exact source-bound regular files at their names with recorded source modes and hashes, failing on any conflict, missing input or concurrent change.','Re-inventory the complete private result against the exact union of base plus six: compare every name/type/mode/content/link, detect any new/missing entry, alias or escape, and bind the final whole-tree identity and writer quiescence.','Prove no writable inode aliases and exclude mutation by any owner throughout use; mount this result read-only over existing /src/scripts after /src. Verify effective mounted identities, membership and read-only enforcement before source consumer.','Preserve the eight other source overlays and their exact types and identities; review nested mount target existence and realpath/symlink containment with live filesystem state, not only historical observations.'],'remaining':['All recorded identities are null; fresh full source, scripts, toolchain and /out membership/quiescence remain required.','/src and retained sources must be stable and actually mountable; /src/scripts target is historical directory observation, not current availability.','Complete include/producer/runtime source closure and absence of held paths are not implied by scripts preservation.','Adapt disabled owner and validator for the 14-target graph, review no-shadow, inode alias, RO enforcement and /out/work isolation; independent review and fresh operation admission remain mandatory.'],'off_pair':j['off_pair']}
(O/'SCRIPTS-OVERLAY.NOT-RELEASED.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS complete scripts metadata/content point-in-time inventory, exact 6-file union, 8 other overlays, 14 unique ordered proposed mounts and null live identities; no materialization or mount')
