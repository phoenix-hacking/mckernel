"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only postcompiler check. Never executes the fixture.
"""
import importlib.util,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('existing_owner_checker',P.parent/'f02-idle-layout-values-next-current-source-1/check_idle_owners.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=json.loads((P/'SOURCE-ONLY.json').read_text());s=a['symbol']
rust,fallback,selected,exe,mapfile,out=map(Path,sys.argv[1:]);r,f,c,e=map(m.module.Elf,(rust,fallback,selected,exe))
expected=dict(name=s,bytes=208,minimum_alignment=8,bytes_hex=a['bytes_hex'])
rows=[m.data_record(elf,expected) for elf in (r,f,e)]
assert not c.definitions(s)
refs=c.allocated_references(s);assert refs and all(x['relocation_type']==1 for x in refs)
origin=m.exact_origin(r,e,m.map_entries(mapfile),s)
Path(out).write_text(json.dumps(dict(scope=a['scope'],decision='PASS_FOCUSED_HOST_STORAGE_ONLY',data=rows,selected_references=refs,origin=origin,native_delta=0,whole_file_delta=0),indent=2)+'\n')
