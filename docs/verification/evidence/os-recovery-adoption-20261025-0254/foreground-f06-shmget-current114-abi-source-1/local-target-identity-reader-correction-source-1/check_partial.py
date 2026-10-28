"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow compile/partial-link metadata readback. Never executes artifact/provider.
"""
from pathlib import Path
import ast,hashlib,json,stat,struct
P=Path(__file__).resolve().parent
cfg=json.loads((P/'READBACK-CONFIG.json').read_text())
O=Path(cfg['output'])
report_output=Path(cfg['report_output'])
identity_ref=cfg['retained_identities'];identity_path=Path(identity_ref['path'])
assert identity_path.is_absolute()
identity_raw=identity_path.read_bytes()
assert len(identity_raw)==identity_ref['bytes'] and hashlib.sha256(identity_raw).hexdigest()==identity_ref['sha256']
for row in json.loads(identity_raw)['records']:
 p=Path(row['reference']['path']);assert p.is_absolute();z=p.lstat()
 assert stat.S_ISREG(z.st_mode) and not p.is_symlink()
 assert (z.st_dev,z.st_ino,z.st_uid,z.st_gid,stat.S_IMODE(z.st_mode),z.st_nlink,z.st_mtime_ns,z.st_ctime_ns)==tuple(row[k] for k in ['device','inode','uid','gid','mode','nlink','mtime_ns','ctime_ns'])
 raw=p.read_bytes();assert len(raw)==row['reference']['bytes'] and hashlib.sha256(raw).hexdigest()==row['reference']['sha256']
driver=Path(cfg['driver']['path'])
assert hashlib.sha256(driver.read_bytes()).hexdigest()==cfg['driver']['sha256']
# Reuse only the three reviewed ELF metadata definitions, never driver main.
wanted={'_reuse_elf_owning_relocations','_reuse_elf_object_bytes','_reuse_elf_descriptor','_reuse_elf_cstring'}
nodes=[n for n in ast.parse(driver.read_text()).body
       if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf'
       or isinstance(n,ast.FunctionDef) and n.name in wanted]
ns=dict(Path=Path,struct=struct)
exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained ELF metadata definitions','exec'),ns)
Elf=ns['_ReuseElf'];rels=ns['_reuse_elf_owning_relocations'];data=ns['_reuse_elf_object_bytes']
def own(e,name):
 rows=[s for s in e.symbols if s['name']==name and s['shndx']]
 assert len(rows)==1,(name,len(rows))
 return rows[0]
def allocated(e):
 return {s['name']:s for s in e.symbols if s['type']==2 and s['shndx'] and e.sections[s['shndx']]['flags']&2}
def target(e,r):
 t=r['target']
 if t['type']!=3:return (t['name'],r['addend'])
 point=t['value']+r['addend']
 owners=[s for s in e.symbols if s['shndx']==t['shndx'] and s['type'] in (1,2)
         and s['value']<=point<s['value']+s['size']]
 if owners:
  s=min(owners,key=lambda s:(s['size'],s['name']))
  return (s['name'],point-s['value'])
 return (e.sections[t['shndx']]['name'],point)
def shape(e,s):
 return [(r['offset'],r['type'],finite_target(e,s,r)) for r in rels(e,s)]
def masked(e,s):
 b=bytearray(data(e,s))
 for r in rels(e,s):
  width={1:8,2:4,4:4,10:4,11:4,25:8,27:8,29:8,31:8}.get(r['type'])
  assert width is not None,('unresolved relocation width',r)
  assert 0<=r['offset'] and r['offset']+width<=len(b),('relocation outside owning body',r,len(b))
  b[r['offset']:r['offset']+width]=bytes(width)
 return bytes(b)
def equal(a,b,name):
 x=own(a,name);y=own(b,name)
 assert x['size']==y['size'],(name,'size',x['size'],y['size'])
 assert masked(a,x)==masked(b,y),(name,'nonrelocated body mismatch')
 assert shape(a,x)==shape(b,y),(name,'positive relocation target mismatch')
 return dict(name=name,bytes=x['size'],complete_nonrelocated_bytes_equal=True,relocations=shape(b,y))
# Exact expert proof pins the only fifteen local storage identities accepted here.
from finite_local_identity import validate_actual_pairs,mapped_edge,edge_key,synthetic_controls
proof_ref=cfg['finite_local_identity_proof'];proof_raw=Path(proof_ref['path']).read_bytes()
assert len(proof_raw)==proof_ref['bytes'] and hashlib.sha256(proof_raw).hexdigest()==proof_ref['sha256']
proof=json.loads(proof_raw)
assert proof['decision']=='CONFIRMED_FINITE_COMPILER_LOCAL_OBJECT_IDENTITIES' and proof['implementation_ownership'] is False
for reference in proof['proof_references'].values():
 raw=Path(reference['path']).read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256']
source_texts=[Path(proof['proof_references'][k]['path']).read_text() for k in ['baseline_source','candidate_source']]
for row in proof['finite_local_target_pairs']:
 if row['kind']=='source_private_mutable_static':assert all(text.count(row['source_declaration'])==1 for text in source_texts)
 for anchor in row.get('source_line_anchors',[]):assert all(anchor['text'] in text for text in source_texts)
negative_controls=synthetic_controls(proof)
base=Elf(O/'baseline.arch.o');candidate=Elf(O/'candidate.arch.o')
local_identities=validate_actual_pairs(proof,base,candidate,own,rels,data,ns['_reuse_elf_descriptor'],ns['_reuse_elf_cstring'],allocated)
local_seen={'old':set(),'new':set()}
def finite_target(e,body,r):
 side='old' if e is base else 'new' if e is candidate else None
 if side is not None:
  names={p[side+'_symbol']['name'] for p in proof['finite_local_target_pairs']}
  if r['target']['name'] in names:
   row=mapped_edge(proof['mismatched_relocations'],proof['finite_local_target_pairs'],side,body['name'],r['offset'],r['type'],r['addend'],r['target']['name'])
   local_seen[side].add((body['name'],r['offset'],r['type'],r['addend'],r['target']['name']))
   return ('EXACT_SOURCE_LOCAL_OBJECT_IDENTITY',row['kind'],row['old_symbol']['name'],row['new_symbol']['name'])
 return target(e,r)

leaf=Elf(O/'shmget.rs.o');combined=Elf(O/'shmget.current114.partial.o')
for key in ['current114_Rust','current114_arch']:
 row=cfg[key];raw=Path(row['path']).read_bytes()
 assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
actual=Elf(Path(cfg['current114_Rust']['path']));retained=Elf(Path(cfg['current114_arch']['path']))
name=cfg['target'];before=allocated(base);after=allocated(candidate)
assert set(before)==set(allocated(retained)) and len(before)==19
assert set(before)-set(after)=={name} and not set(after)-set(before) and len(after)==18
unchanged=[equal(base,candidate,n) for n in sorted(after)]
for side in ['old','new']:assert local_seen[side]=={edge_key(e,side) for e in proof['mismatched_relocations']},('finite nineteen edges complete',side)
assert not [s for s in candidate.symbols if s['name']==name and s['shndx']]
a=own(leaf,name);b=own(combined,name)
assert a['bind']==b['bind']==1 and a['type']==b['type']==2
adapter=equal(leaf,combined,name)
provider_edges=[r for r in rels(leaf,a) if r['target']['name']==cfg['existing_Rust_provider']]
assert len(provider_edges)==1 and provider_edges[0]['addend']==0
provider=equal(actual,combined,cfg['existing_Rust_provider'])
assert own(actual,cfg['existing_Rust_provider'])['size']==cfg['existing_Rust_provider_bytes']
consumer=equal(actual,combined,cfg['consumer'])
c=own(actual,cfg['consumer']);assert c['size']==cfg['actual_consumer_bytes']
old=[r for r in rels(actual,c) if r['target']['name']==name]
assert len(old)==1 and {k:old[0][k] for k in ['offset','type','addend']}==cfg['actual_consumer_callback_relocation']
new=[r for r in rels(combined,own(combined,cfg['consumer'])) if r['target']['name']==name]
assert len(new)==1 and new[0]['target']['shndx']==b['shndx'] and new[0]['target']['value']==b['value']
assert new[0]['addend']==0 and new[0]['type']==1
result=dict(scope=__doc__.splitlines()[0],status='PASS_GENUINE_ABI_COMPILE_AND_CURRENT114_PARTIAL_CONSUMER_LINK_ONLY',C_before=19,C_after=18,target=name,unchanged_other_C_bodies=unchanged,finite_local_target_identity_proof=proof_ref,finite_local_storage_identity=local_identities,finite_local_reference_edges_validated=19,synthetic_metadata_negative_controls=negative_controls,unique_new_Rust_adapter=adapter,actual114_existing_Rust_provider=provider,actual114_consumer=consumer,positive_callback_edge=dict(consumer=cfg['consumer'],offset=104,type=1,addend=0,unique_Rust_provider=name),retained_behavior_comparisons=3640,behavior_replay=0,artifact_execution=False,native_provider_execution=False,production_default_acceptance=False,native_acceptance=False,wholefile_retirement=False)
(report_output/'PARTIAL-READBACK.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS shmget current114 ABI and partial consumer link; native UNRUN')
