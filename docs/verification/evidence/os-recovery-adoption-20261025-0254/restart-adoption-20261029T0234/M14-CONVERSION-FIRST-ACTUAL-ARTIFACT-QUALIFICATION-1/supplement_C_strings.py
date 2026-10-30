"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded readback of exact C mergeable readonly .rodata.str1.8 strings.
Original reader and all original failures remain unchanged.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('context.py').read_text(),str(Path(__file__).with_name('context.py')),'exec'))
row=next(r for r in template['validator_nodes']if r['name']=='relocated_function');text=auth(row['source']).read_text();node=next(n for n in ast.parse(text).body if getattr(n,'name','')=='relocated_function');segment=ast.get_source_segment(text,node)
assert segment.count("('.lrodata.str1.1','.rodata.str1.1')")==1
adapted=segment.replace("('.lrodata.str1.1','.rodata.str1.1')","('.lrodata.str1.1','.rodata.str1.1','.rodata.str1.8')").replace('def relocated_function(', 'def strict_C_string_readback(')
exec(compile(adapted,__file__+':EXACT_ONE_SECTION_LITERAL_EXTENSION','exec'))
names=['do_execveat','do_fork','do_mmap','do_syscall','interrupt_syscall','ptrace_wakeup_log_bridge','terminate','util_thread'];proofs=[];failures=[]
for n in names:
 try:
  s,raw,tokens,records=strict_C_string_readback(kc,n,image);proofs.append(dict(name=n,input=s,final=image.sym(n),all_final_bytes=True,records=records))
 except Exception as exc:failures.append(dict(name=n,error=repr(exc)))
result=dict(scope=__doc__.splitlines()[0],exact_frozen_reader=row,change="Only eight explicit C functions: accept .rodata.str1.8 via identical literal() proving PROGBITS/MERGE/STRINGS/ALLOC/readonly flags, in-range terminated source string, exact final literal bytes and whole function reconstruction. No address masking or metadata normalization.",proofs=proofs,failures=failures)
(D/'EIGHT-C-CONSUMER-STRING-SUPPLEMENT.ACTUAL.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(functions=len(proofs),failures=failures)))
