#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only two-slot actual ELF identity check. Reuses pinned existing readers only.
No compilation, runtime, resource observation or execution authority.
"""
import argparse, ast, hashlib, json, struct
from pathlib import Path
D=Path(__file__).resolve().parent
PROOF_SHA='6e34d56e818f3bd063d789515dbc1d92e0dc218fa7851acbae98d53d651a17cf'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def helpers():
 p=D/'ACTUAL-C-DESCRIPTOR-IDENTITY.json';assert sha(p)==PROOF_SHA
 proof=json.loads(p.read_bytes());ns={'struct':struct,'Path':Path}
 for key,names in [('existing_reader',('_ReuseElf','_reuse_elf_owning_relocations','_reuse_elf_object_bytes')),('existing_input_string_reader',('input_string',))]:
  row=proof[key];path=Path(row['path']);assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
  tree=ast.parse(path.read_text());nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
  assert {n.name for n in nodes}==set(names)
  exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
 return proof,ns
def actual(path,expected,ns):
 assert len(expected)==64 and sha(path)==expected
 pre=path.stat();elf=ns['_ReuseElf'](path);assert hashlib.sha256(elf.raw).hexdigest()==expected
 post=path.stat();assert (pre.st_dev,pre.st_ino,pre.st_size,pre.st_mtime_ns)==(post.st_dev,post.st_ino,post.st_size,post.st_mtime_ns)
 return elf
def records(elf,ns):
 result=[]
 for s in elf.symbols:
  if s['type']!=1 or s['size']!=32 or not 0<s['shndx']<len(elf.sections):continue
  sec=elf.sections[s['shndx']]
  if sec['name']!='__verbose':continue
  rels=ns['_reuse_elf_owning_relocations'](elf,s)
  fs=[r for r in rels if r['offset']==8 and r['type']==1]
  if len(fs)!=1 or ns['input_string'](elf,fs[0])!=b'obtain_clone_cpuid\0':continue
  assert sec['flags']&3==3 and sec['align']>=8 and s['value']%8==0
  assert len(rels)==2 and {(r['offset'],r['type']) for r in rels}=={(0,1),(8,1)}
  raw=ns['_reuse_elf_object_bytes'](elf,s);file,func,fmt,bits,padding=struct.unpack('<QQQII',raw)
  assert (file,func,fmt,padding)==(0,0,0,0)
  lit=lambda offset:ns['input_string'](elf,next(r for r in rels if r['offset']==offset))
  result.append(dict(file_utf8=lit(0)[:-1].decode(),function_utf8=lit(8)[:-1].decode(),fmt=None,line=bits&0xffffff,flags=bits>>24,line_flags=bits,bytes=32,alignment=8))
 return sorted(result,key=lambda r:r['line_flags'])
def wanted(proof):
 keys=('file_utf8','function_utf8','fmt','line','flags','line_flags','bytes','alignment')
 return [{k:r[k] for k in keys} for r in proof['records']]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--retained-c-selfcheck',action='store_true')
 p.add_argument('--rust-object',type=Path);p.add_argument('--rust-sha256');p.add_argument('--selected-c-object',type=Path);p.add_argument('--selected-c-sha256');a=p.parse_args()
 proof,ns=helpers();base=proof['object'];old=actual(Path(base['path']),base['sha256'],ns);assert records(old,ns)==wanted(proof)
 if a.retained_c_selfcheck:
  assert not any((a.rust_object,a.rust_sha256,a.selected_c_object,a.selected_c_sha256));decision='PASS_RETAINED_C_TWO_SLOT_READER_SELFCHECK_ONLY'
 else:
  assert all((a.rust_object,a.rust_sha256,a.selected_c_object,a.selected_c_sha256))
  rust=actual(a.rust_object,a.rust_sha256,ns);c=actual(a.selected_c_object,a.selected_c_sha256,ns)
  assert records(rust,ns)==wanted(proof) and records(c,ns)==[]
  defined=lambda e:[s for s in e.symbols if s['name']=='obtain_clone_cpuid' and 0<s['shndx']<len(e.sections) and s['type']==2 and e.sections[s['shndx']]['flags']&2]
  assert len(defined(rust))==1 and defined(c)==[]
  decision='PASS_EXACT_TWO_RUST_SLOTS_C_DESELECTION_AND_RUST_PROVIDER_OBJECT_ONLY'
 print(json.dumps(dict(decision=decision,slots=2,native_acceptance=False,final_link_and_registry_acceptance=None),sort_keys=True))
if __name__=='__main__':main()
