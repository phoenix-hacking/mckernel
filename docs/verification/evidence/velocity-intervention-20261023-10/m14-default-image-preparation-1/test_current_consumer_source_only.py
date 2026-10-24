"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure offline regressions against the actual successor consumer functions. No
compiler, subprocess, Docker, root, object hashing or workload execution.
"""
from pathlib import Path
import ast,copy,hashlib,unittest
D=Path(__file__).resolve().parent;DRIVER=D/'native_rust_exact_mckernel_image_offline.py'
BASE=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-15/default-image-preparation-1/native_rust_exact_mckernel_image_offline.py')
tree=ast.parse(DRIVER.read_bytes());selected_functions={'_m14_check_current_provider_symbols','_m14_cpu_abi_stderr_allowed','_m14_completion_reference_encoding'}
selected_constants={'M14_CURRENT_RUST_PROVIDERS','M14_CURRENT_CPU_ABI_WARNINGS'}
body=[]
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in selected_functions:body.append(n)
 elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in selected_constants for t in n.targets):body.append(n)
def fail(ok,message):
 if not ok:raise RuntimeError(message)
ns={'_fail':fail,'ImageBuildError':RuntimeError};exec(compile(ast.Module(body=body,type_ignores=[]),str(DRIVER),'exec'),ns)
check=ns['_m14_check_current_provider_symbols'];warning=ns['_m14_cpu_abi_stderr_allowed'];encoding=ns['_m14_completion_reference_encoding'];providers=ns['M14_CURRENT_RUST_PROVIDERS'];warnings=ns['M14_CURRENT_CPU_ABI_WARNINGS']

def model():
 texts={p:'' for p in providers};names=sorted(set(x for names in providers.values() for x in names));rust=''.join('00000000 00000010 T '+name+'\n' for name in names);return texts,rust,rust

class CurrentConsumer(unittest.TestCase):
 def test_current_Rust_model_passes(self):
  self.assertEqual(check(*model()),providers)
 def test_old_C_callback_model_rejected(self):
  c,r,i=model();name='mem_tlb_rdtsc_bridge';c['kernel/mem.c']='00000000 00000010 T '+name+'\n';r=r.replace('00000000 00000010 T '+name+'\n','                 U '+name+'\n')
  with self.assertRaises(RuntimeError):check(c,r,i)
 def test_missing_Rust_provider_rejected(self):
  c,r,i=model();name='mem_tlb_atomic_dec_bridge';r=r.replace('00000000 00000010 T '+name+'\n','')
  with self.assertRaises(RuntimeError):check(c,r,i)
 def test_duplicate_Rust_provider_rejected(self):
  c,r,i=model();r+='00000000 00000010 T mem_tlb_atomic_dec_bridge\n'
  with self.assertRaises(RuntimeError):check(c,r,i)
 def test_missing_final_provider_rejected(self):
  c,r,i=model();i=i.replace('00000000 00000010 T clear_range_l3\n','')
  with self.assertRaises(RuntimeError):check(c,r,i)
 def test_duplicate_final_provider_rejected(self):
  c,r,i=model();i+='00000000 00000010 T clear_range_l3\n'
  with self.assertRaises(RuntimeError):check(c,r,i)
 def test_local_C_body_rejected(self):
  c,r,i=model();c['kernel/process.c']='00000000 00000010 t vm_range_insert_log_bridge\n'
  with self.assertRaises(RuntimeError):check(c,r,i)
 def test_exact_current_packed_warning_only(self):
  self.assertTrue(warning('successor-real-ABI-arch-x86_64-kernel-cpu-c',warnings));self.assertTrue(warning('another-site',b''))
 def test_changed_warning_rejected(self):
  self.assertFalse(warning('successor-real-ABI-arch-x86_64-kernel-cpu-c',warnings+b'warning: extra\n'));self.assertFalse(warning('successor-real-ABI-arch-x86_64-kernel-cpu-c',warnings.replace(b':3732:',b':3733:')))
 def test_warning_at_wrong_observer_rejected(self):
  self.assertFalse(warning('successor-symbols-arch-x86_64-kernel-cpu-c',warnings))
 def test_exact_completion_encodings(self):
  row=dict(symbol='mem_tlb_atomic_dec_bridge',binding=1,shndx=0,addend=0,allocated=True,type=27)
  self.assertIn('GOT64',encoding(row));row['type']=1;self.assertIn('direct',encoding(row))
 def test_wrong_completion_reference_rejected(self):
  row=dict(symbol='mem_tlb_atomic_dec_bridge',binding=1,shndx=0,addend=0,allocated=True,type=27)
  for key,value in [('symbol','wrong_provider'),('binding',0),('shndx',1),('addend',8),('allocated',False),('type',8)]:
   bad=dict(row);bad[key]=value
   with self.assertRaises(RuntimeError):encoding(bad)
 def test_production_wires_actual_checks(self):
  funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
  calls={n.func.id for n in ast.walk(funcs['_validate_m14_successor_contract']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
  self.assertTrue({'_m14_check_current_provider_symbols','_m14_allocated_provider_relocations','_m14_l4_callback_object'}<=calls)
  observe_calls={n.func.id for n in ast.walk(funcs['_m14_observe']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)};self.assertIn('_m14_cpu_abi_stderr_allowed',observe_calls)
  unchanged={n.name:n for n in ast.parse(BASE.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  for name,node in unchanged.items():
   if name not in {'_m14_observe','_validate_m14_successor_contract'}:self.assertEqual(ast.dump(node,include_attributes=False),ast.dump(funcs[name] if isinstance(node,ast.FunctionDef) else next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name),include_attributes=False),name)

if __name__=='__main__':unittest.main(verbosity=2)
