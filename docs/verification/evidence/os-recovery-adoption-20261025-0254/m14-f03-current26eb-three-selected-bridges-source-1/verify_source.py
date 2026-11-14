"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite exact source/selected-object/fixture/argv checks; no compiler or runtime.
"""
from pathlib import Path
import ast,hashlib,json,re,struct
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel')
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(p.read_text())
def logical_tail(tail,dispatch):
 active=True;line=0
 for s in tail.splitlines():
  if s.startswith('#if '):active=dispatch;line+=1
  elif s=='#else':active=not dispatch;line+=1
  elif s=='#endif':active=True;line+=1
  elif s.startswith('#line ') and active:line=int(s.split()[1])
  else:line+=1
 return line
def main():
 x=read(D/'THREE-SOURCE-SLICES.json');plan=read(D/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json')
 for rel,row in x['source_preimages'].items():assert ref(R/rel)==row
 for rel,row in x['source_postimages'].items():assert ref(Path(row['path']))==row
 current=read(Path(x['cursor']['path']));assert ref(Path(x['cursor']['path']))==x['cursor'];assert ref(Path(x['actual_selected_object']['path']))==x['actual_selected_object']
 driver=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py';raw=driver.read_bytes();assert hashlib.sha256(raw).hexdigest()=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd';ns={'struct':struct};exec(compile(ast.Module(body=[n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf'],type_ignores=[]),'accepted readonly metadata parser','exec'),ns)
 elf=ns['_ReuseElf'](Path(x['actual_selected_object']['path']));funcs={s['name']:s for s in elf.symbols if s['type']==2 and 0<s['shndx']<len(elf.sections) and elf.sections[s['shndx']]['flags']&2};assert len(funcs)==75 and set(funcs)==set(current['rows']['F03']['defined_FUNC_names'])
 C=(R/'kernel/syscall.c').read_text();CC=(D/'candidate/kernel/syscall.c').read_text();policy=(R/'kernel/rust/syscall_policy.rs').read_text();RR=(D/'candidate/kernel/rust/syscall_policy.rs').read_text()
 body='unsafe extern "C" fn f03_exit_notify_wake(waitq: *mut c_void) {';promotion='#[cfg_attr(f03_exit_waitq_wake_selected_candidate,no_mangle)]\n'+body;assert RR==policy.replace(body,promotion,1)
 restored=CC;metadata=[]
 for row in x['slices']:
  original=Path(row['original_C']['path']).read_text();selected=Path(row['selected_C']['path']).read_text();rust=Path(row['unchanged_Rust_body']['path']).read_text();leaf=Path(row['unchanged_Rust_body']['path']).parent
  assert CC.count(selected)==1 and C.count(original)==1;restored=restored.replace(selected,original,1)
  assert '#else\n'+original+'#endif\n' in selected
  assert row['declaration'] in selected and '#define '+row['C']+' '+row['Rust'] in selected
  cfg=row.get('existing_export_cfg') or row['new_export_cfg'];assert (leaf/'selected.Rust.inc').read_text()=='#[cfg_attr('+cfg+',no_mangle)]\n'+rust
  assert (leaf/'selected.Rust.inc').read_text() in RR
  assert not any(marker in rust for marker in ['line!','file!','asm!','static mut','refcount','forget('])
  tail=selected.split('#else\n'+original+'#endif\n',1)[1]
  assert logical_tail(tail,True)==row['old_logical_following_line']
  assert logical_tail(tail,False)==row.get('old_logical_following_line_without_dispatch_context',row['old_logical_following_line'])
  metadata.append(dict(name=row['C'],actual_symbol=funcs[row['C']],selected_existing_Rust=row['Rust']))
 assert restored==C, 'all other C bytes and fallback bodies must be exact'
 assert (D/'retained-abi.rs').read_bytes()==(R/'kernel/rust/abi.rs').read_bytes()
 waitq=(R/'kernel/rust/waitq.rs').read_text();expected='\n\n'.join(waitq[waitq.rfind('#[repr(C)]',0,waitq.index('pub(crate) struct '+name)):waitq.index('\n}',waitq.index('pub(crate) struct '+name))+2] for name in ['IhkSpinlock','ListHead','Waitq'])+'\n';assert (D/'retained-waitq-layout.Rust.inc').read_text()==expected
 lib=(D/'lib.fixture.rs').read_text();c=(D/'driver.c').read_text();assert '#[cfg_attr' not in lib and lib.count('selected.Rust.inc')==3
 assert '[crate::abi::CULong;19]' in lib and 'F03_THREE_WAKE_PROVIDER_ABI[19]' in c and 'const unsigned long c[19]' in c
 assert c.count('_Static_assert(__builtin_types_compatible_p')==6
 assert 'n==90' in c and 'for(i=0;i<3;i++)' in c
 assert not any(s in c for s in ['__asm__','syscall(','pthread_','raise(','fork('])
 for row in plan['input_refs'].values():assert ref(Path(row['path']))==row
 for row in plan['tool_refs'].values():assert ref(Path(row['path']))==row
 for row in plan['current_header_refs'].values():assert ref(Path(row['path']))==row
 commands=plan['commands'];assert len(commands)==3
 assert commands[0]['argv'][-1]==str(D/'lib.fixture.rs') and commands[2]['argv']==[str(D/'future-host-output-1/parity')]
 assert '--cfg' in commands[0]['argv'] and 'f03_exit_waitq_wake_selected_candidate' in commands[0]['argv']
 assert all('-D'+row['define'] in commands[1]['argv'] for row in x['slices'])
 assert not (D/'future-host-output-1').exists() and plan['actual_grant'] is None
 for row in commands:assert hashlib.sha256((json.dumps(row['argv'],separators=(',',':'))+'\n').encode()).hexdigest()==row['argv_compact_json_LF_sha256']
 report=dict(scope=__doc__.splitlines()[0],status='PASS_THREE_REAL_CURRENT26EB_REUSED_SOURCE_SLICES_AND_LITERAL_FUTURE_HOST_PLAN',source_slices=ref(D/'THREE-SOURCE-SLICES.json'),HOST_plan=ref(D/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json'),actual_current_metadata=metadata,current_C_FUNCTION_count=75,expected_after_selection_count=72,new_Rust_algorithm_bodies=0,newly_exported_existing_Rust_functions=1,already_exported_Rust_functions_reused=2,logical_following_lines_preserved_for_dispatch_and_fallback_context=True,C_fallback_and_all_other_source_bytes_exact=True,fixture_expected_pairs=96,fixture_expected_ABI_words=19,actual_compile=None,actual_HOST=None,default_acceptance=False,native_acceptance=False,whole_file_retired=False,compiler_Docker_Git_canonical_runtime_actions=0)
 (D/'RESULT.SOURCE-ONLY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
