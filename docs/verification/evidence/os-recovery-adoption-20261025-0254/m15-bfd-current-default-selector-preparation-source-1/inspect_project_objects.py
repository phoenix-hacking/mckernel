"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixed two-target changed-producer readback. No behavior/native acceptance.
"""
from pathlib import Path
import importlib.util,json,hashlib,shlex,sys
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('existing_ELF',D/'retained_elf.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def ref(p):
 b=Path(p).read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def function(elf,name):
 rows=elf.definitions(name);assert len(rows)==1,(name,elf.path,rows)
 s=rows[0];assert s['kind']==2 and s['bind']==1 and s['size']>0 and elf.sections[s['ndx']]['flags']&4
 return dict(name=name,size=s['size'],section=elf.sections[s['ndx']]['name'])
def main():
 build=Path(sys.argv[1]);output=Path(sys.argv[2]);assert not output.exists();root=build/'executer/user';reports=[]
 layout=ref(root/'rust/bfd_layout.rs');assert layout['sha256']=='e21b4d9975984b7c14e13760c232dda4e755c5955f1649df77ebdc38e065530b' and layout['bytes']==259
 bridges=['mcinspect_bfd_get_symtab_upper_bound_bridge','mcinspect_bfd_canonicalize_symtab_bridge','eclair_bfd_get_symtab_upper_bound_bridge','eclair_bfd_canonicalize_symtab_bridge']
 bfd=m.Elf(root/'rust/bfd_accessors.o');[function(bfd,x) for x in bridges]
 for tool in ['mcinspect','eclair']:
  link=root/f'CMakeFiles/{tool}.dir/link.txt';tokens=shlex.split(link.read_text());objects=[x for x in tokens if x.endswith('.o')]
  expected=['bfd_accessors.o',tool+'_helpers.o']+(['arch_eclair_x86_64.o'] if tool=='eclair' else [])
  assert sorted(Path(x).name for x in objects)==sorted(expected),(tool,objects)
  assert not any('bfd_shim' in x or Path(x).name in ['mcinspect.c.o','eclair.c.o','arch-eclair.c.o'] for x in tokens)
  resolved=[Path(x) if Path(x).is_absolute() else root/x for x in objects];[m.Elf(x) for x in resolved]
  binary=m.Elf(root/tool);symbols=[function(binary,'main')]+[function(binary,x) for x in bridges if x.startswith(tool+'_')]
  # ELF64 e_type3 is the genuine PIE target, not a synthetic helper executable.
  assert int.from_bytes(binary.data[16:18],'little')==3
  reports.append(dict(tool=tool,actual_link=ref(link),actual_objects=[ref(x) for x in resolved],actual_binary=ref(root/tool),Rust_main_and_bridge_definitions=symbols))
 result=dict(scope=__doc__.splitlines()[0],status='PASS_CURRENT_DEFAULT_TWO_TARGET_PROJECT_OBJECT_SELECTION_ONLY',layout=layout,bfd_actual_object=ref(root/'rust/bfd_accessors.o'),targets=reports,SDK21_replayed=False,new_valid_diagnostics_run=0,installation_default_native_whole_file_C_retirement_acceptance=False)
 with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print('PASS current two-tool genuine project objects and Rust BFD providers; valid-native-diagnostic OPEN')
if __name__=='__main__':main()
