"""Cheap source/ELF oracle fixture. No SDK/compiler/container/module operation."""
from pathlib import Path
import ast, hashlib, json, struct, tempfile, types
N=Path(__file__).resolve().parent
for name in ('prepare_fullmodule_inputs.py','materialize_request.py','native_running_external_modules_offline.template.py'):
 ast.parse((N/name).read_bytes(),filename=name)
p=json.loads((N/'SOURCE-PLAN.json').read_bytes());assert len(p['rows'])==64
rows={r['relative']:r for r in p['rows']};assert rows['mcctrl.rs']['source']==rows['mcctrl_rust.rs']['source']
assert len(p['mm_compat']['current_route_wrapper_imports'])==3
assert (N/'Kbuild.proposed').read_text().count('mcctrl-y := mcctrl_rust.o mcctrl_vm_write_compat.o')==1
for r in p['rows']:
 raw=Path(r['source']['path']).read_bytes();assert len(raw)==r['source']['bytes'] and hashlib.sha256(raw).hexdigest()==r['source']['sha256']
a=Path(rows['smp_application.rs']['source']['path']).read_text();assert 'with_active_child' not in a
assert 'owner.response.request().cpu()' in a and 'owner.response.request().response()' in a
m=types.ModuleType('composite_fixture');m.__file__=str(N/'native_running_external_modules_offline.template.py');exec(compile(Path(m.__file__).read_bytes(),m.__file__,'exec'),m.__dict__)
def elf(entries):
 strings=b'\0';symbols=b'\0'*24
 for name,ndx in entries:
  offset=len(strings);strings+=name.encode()+b'\0';symbols+=struct.pack('<IBBHQQ',offset,0x12,0,ndx,0,0)
 start=64;ss=start+len(strings);sh=ss+len(symbols)
 header=struct.pack('<16sHHIQQQIHHHHHH',b'\x7fELF\x02\x01\x01'+b'\0'*9,1,62,1,0,0,sh,0,64,0,0,64,3,0)
 sections=b'\0'*64+struct.pack('<IIQQQQIIQQ',0,3,0,0,start,len(strings),0,0,1,0)+struct.pack('<IIQQQQIIQQ',0,2,0,0,ss,len(symbols),1,0,8,24)
 return header+strings+symbols+sections
with tempfile.TemporaryDirectory(prefix='composite-fixture-',dir=N) as tmp:
 d=Path(tmp);names=m.MM_BRIDGES
 (d/'.mcctrl_vm_write_compat.o.cmd').write_text('source_x := /candidate/modules/mcctrl_vm_write_compat.c\nsavedcmd_x := gcc -c /candidate/modules/mcctrl_vm_write_compat.c -o /candidate/modules/mcctrl_vm_write_compat.o\n /candidate/modules/mcctrl_vm_write_compat.h\n')
 (d/'mcctrl.mod').write_text('/candidate/modules/mcctrl_rust.o\n/candidate/modules/mcctrl_vm_write_compat.o\n')
 (d/'.mcctrl.o.cmd').write_text('savedcmd_x := ld -r -o /candidate/modules/mcctrl.o @/candidate/modules/mcctrl.mod\n')
 def reset():
  for f in ('mcctrl_vm_write_compat.o','mcctrl.o','mcctrl.ko'):(d/f).write_bytes(elf([(s,1) for s in names]))
  (d/'mcctrl_rust.o').write_bytes(elf([(s,0) for s in names]))
 reset();assert m.actual_mm_provider_check(d)['status']=='PASS_ACTUAL_COMPOSITE_MM_PROVIDER_SYMBOLS'
 # Optimized-away Rust imports confer no final resolution credit; final defs
 # still must exist exactly once, independently of source declarations.
 (d/'mcctrl_rust.o').write_bytes(elf([]));m.actual_mm_provider_check(d)
 failures=0
 for file,entries in [('mcctrl.o',[(s,1) for s in names]+[(names[0],1)]),('mcctrl.ko',[(s,1) for s in names]+[(names[0],0)]),('mcctrl.ko',[(s,1) for s in names[1:]])]:
  reset();(d/file).write_bytes(elf(entries))
  try:m.actual_mm_provider_check(d)
  except ValueError:failures+=1
  else:raise AssertionError('invalid final provider accepted')
 assert failures==3
 reset();(d/'mcctrl.mod').write_text('/candidate/modules/mcctrl_rust.o\n/candidate/modules/mcctrl_vm_write_compat.o\n/candidate/modules/mcctrl_vm_write_compat.o\n')
 try:m.actual_mm_provider_check(d)
 except (ValueError,RuntimeError):pass
 else:raise AssertionError('duplicate wrapper member accepted')
print(json.dumps({'status':'PASS_SOURCE_AND_SYNTHETIC_ELF_FIXTURE_ONLY','source_files':64,'positive_vectors':2,'negative_vectors':4,'compiler_calls':0}))
