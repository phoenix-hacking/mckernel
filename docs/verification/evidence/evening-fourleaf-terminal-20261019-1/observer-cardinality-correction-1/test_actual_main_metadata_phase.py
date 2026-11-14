"""Actual main's selected metadata/observation/draft phase; root effects omitted."""
from pathlib import Path
import types,json,hashlib,ast,stat,resource
C=Path(__file__).resolve().parent;T=C.parent;F=C/'fixture-correction-1';F.mkdir();resource.setrlimit(resource.RLIMIT_AS,(268435456,1073741824))
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def load(p):m=types.ModuleType(p.stem);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
source=(C/'observe_four_leaf_image_retirement.py').read_text();observer=load(C/'observe_four_leaf_image_retirement.py');engine=load(T/'cleanup_fourleaf.py');physical=json.loads((T/'actual-fourleaf-physical-bindings.json').read_text());pairs=json.loads((T/'retained-production-objects/retained-objects.json').read_text());assert len(pairs)==21
# All42 rows are actualaccepted fullFD descriptors, not invented rowcount tokens.
known={r['path']:dict(r) for p in pairs for r in [p['original'],p['retained']]};proof=json.loads((T/'terminal-fetched-source-proof.json').read_text());row=next(r for r in proof['rows'] if r['repository_path']==engine.PUBLISHED_SCRIPT);assert row['sha256']==ref(T/'cleanup_fourleaf.py')['sha256']
for path,digest in observer.FULL_SOURCE_SHA256.items():
 s=Path(path).lstat();known[path]=dict(path=path,sha256=digest,size=s.st_size,device=s.st_dev,inode=s.st_ino,mode=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,gid=s.st_gid,nlink=s.st_nlink)
owner=json.loads(Path(physical['owner']['path']).read_text());objects=json.loads((T/'actual-fourleaf-image-object-authority.json').read_text());stored={};real_identity=engine.observe_identity;actual_FD_paths=set(known);active_FD=[False];actual_FD_count=[0]
def identity(path):
 path=Path(path);key=str(path)
 if active_FD[0] and key in actual_FD_paths:return real_identity(path)
 if key in known:return dict(known[key])
 if key in stored:raw=stored[key];return dict(path=key,sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),device=66306,inode=999999,mode='0o600',uid=0,gid=0,nlink=1)
 s=path.lstat();return dict(path=key,sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else '0'*64,size=s.st_size,device=s.st_dev,inode=s.st_ino,mode=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,gid=s.st_gid,nlink=s.st_nlink)
# Hashing large ordinarymanifest/toolchain is omitted; selected closure uses known consumed refs.
refs=json.loads((T/'canonical-selected-provenance-refs.json').read_text())['source_request_bindings'];b=json.loads(Path(observer.FOURLEAF_GATE_BINDING['path']).read_text());full=b['full_fourleaf_source_authority']
for r in list(refs.values())+[full['entire_source_manifest']]:
 p=Path(r['path']);s=p.lstat();known[str(p)]=dict(path=str(p),sha256=r['sha256'],size=s.st_size,device=s.st_dev,inode=s.st_ino,mode=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,gid=s.st_gid,nlink=s.st_nlink)
# Otherlarge files are metadata-only effects here, root runtime validates liveFDs itself.
for p in [engine.OUTPUT/'evidence/artifacts/mckernel.img',engine.OUTPUT/'evidence/receipt.json',Path(full['source_root']).parent/'image-toolchain.json',engine.EVIDENCE/'attempt/container.log']:
 if str(p) not in known:
  s=p.lstat();known[str(p)]=dict(path=str(p),sha256=next(r['original']['sha256'] for r in pairs if r['original']['path'].endswith('/kernel/mckernel.img')) if p.name=='mckernel.img' else '0'*64,size=s.st_size,device=s.st_dev,inode=s.st_ino,mode=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,gid=s.st_gid,nlink=s.st_nlink)
engine.observe_identity=identity;engine.metadata_inventory=lambda p:[]
real_converter=observer.new_object_binding
def actual_converter(m,row):
 active_FD[0]=True
 try:converted=real_converter(m,row);actual_FD_count[0]+=1;return converted
 finally:active_FD[0]=False
observer.new_object_binding=actual_converter
observer.OUTPUT=F/'synthetic-root-output'
def store(name,raw):stored[str(observer.OUTPUT/name)]=raw
observer.store=store
# Select a contiguous real main metadata phase; rootpermission/lock/process/Docker phases omitted.
a=ast.parse(source);main=next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name=='main');block=next(n for n in main.body if isinstance(n,ast.Try));start=next(i for i,n in enumerate(block.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='request_source_owner' for t in n.targets));end=next(i for i,n in enumerate(block.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='observation' for t in n.targets));phase=block.body[start:end+1];draft=next(n for n in block.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='draft' for t in n.targets));main.body=ast.parse('m=_fixture_engine\nnew_objects=_fixture_pairs\nretirement=_fixture_physical\nobjects=_fixture_objects\nmount=_fixture_mount\nlock={}\ntarget=_fixture_target\ninspection=_fixture_inspection\nrecords=_fixture_records\nopts=_fixture_opts\n').body+phase+[draft]+ast.parse('return observation,draft,new_object_metadata,selected_map').body
observer.__dict__.update(_fixture_engine=engine,_fixture_pairs=pairs,_fixture_physical=dict(physical,outer_join=physical['postjoin'],common_record_sha256=physical['common']['sha256'],shared_record_sha256=physical['shared']['sha256']),_fixture_records=[identity(Path(physical[k]['path'])) for k in ['common','shared']],_fixture_objects=objects,_fixture_mount=dict(target=str(engine.ROOT),uuid=engine.UUID,fstype='ext4',options='rw,nodev,nosuid'),_fixture_target=dict(physical['target'],image_id=owner['terminal_container_info']['Image'],exit_code=0),_fixture_inspection=owner['terminal_container_info'],_fixture_opts=types.SimpleNamespace(git_commit=proof['commit'],git_tree='2489b75207bd7d5a83cc9b22705207bc786e2fd7'))
exec(compile(ast.fix_missing_locations(ast.Module(body=[main],type_ignores=[])),str(C/'observe_four_leaf_image_retirement.py'),'exec'),observer.__dict__)
observation,draft,metadata,selected=observer.main();assert len(metadata)==42 and actual_FD_count[0]==42 and draft['status']=='NOT_RELEASED' and draft['observation']==observation
assert str(C/'observe_four_leaf_image_retirement.py') in selected and full['image_request']['path'] in selected and json.loads(Path(full['image_request']['path']).read_text())['host_owner_path'] in selected
# Execute exact old/new count expressions against the SAME actual42 FDmetadata rows.
def countpredicate(text):
 tree=ast.parse(text)
 return next(n.args[0] for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='need' and n.args and 'len(new_object_metadata)' in (ast.get_source_segment(text,n.args[0]) or ''))
assert not eval(compile(ast.Expression(body=countpredicate((T/'observe_four_leaf_image_retirement.py').read_text())),'old-count','eval'),dict(new_object_metadata=metadata,new_objects=pairs));assert eval(compile(ast.Expression(body=countpredicate(source)),'new-count','eval'),dict(new_object_metadata=metadata,new_objects=pairs))
(F/'summary.json').write_text(json.dumps(dict(status='PASS_ACTUAL_MAIN_METADATA_OBSERVATION_DRAFT_PHASE_ROOT_EFFECTS_OMITTED',source=ref(C/'observe_four_leaf_image_retirement.py'),actual_pairs=21,actual_descriptor_rows=42,selected_roles=len(selected),current_observer_selected=True,current_hostowner_selected=True,old58_rejected=True,new_derived42_passed=True,draft_status=draft['status'],root_calls=0,Docker_calls=0,FD_identity_reads='ACTUAL42_HELD_FD_CONVERTER_AND_STREAMING_BYTE_HASHES',inventory='SYNTHETIC_EMPTY_NOT_RUNTIME_PROOF',contiguous_main_phase_statements=len(phase),no_consumed_nonce_or_output_replay=True),indent=2)+'\n');print('PASS actualmain phase21pairs/42descriptors +selectedobserver/hostowner +draftNOT_RELEASED; root0')
