"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Materialize private source and unrun fixture only. No compiler/workload authority.
"""
from pathlib import Path
import hashlib,json,re,difflib,importlib.util,struct
P=Path(__file__).resolve().parent
R=P.parents[4]
# Resolve through the source marker rather than a caller's working directory.
R=next(x for x in P.parents if (x/'kernel/process.c').exists())
S='process_sched_runqueue_offsets'
def ref(p):
 p=Path(p); b=p.read_bytes(); return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,t):
 q=P/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
helper=P.parent/'f02-source38-next-current-integration-source-1/check_thirteen_storage.py'
spec=importlib.util.spec_from_file_location('retained_elf',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
receipt=json.loads((P.parent/'CURRENT110-INDEPENDENT-DEFAULT-ARTIFACT-ACCEPTANCE.json').read_text())
review=json.loads(Path(receipt['independent_review']['path']).read_text())
o=review['tuple']['process']; assert ref(o['path'])==o
elf=m.Elf(o['path']);sym=elf.definitions(S);assert len(sym)==1 and sym[0]['size']==208
sym=sym[0];sec=elf.sections[sym['ndx']];assert sec['flags']==2
start=sec['off']+sym['value']-sec['addr'];raw=elf.data[start:start+208];values=struct.unpack('<26Q',raw)
c=(R/'kernel/process.c').read_text();rust=(R/'kernel/rust/sched_helpers.rs').read_text()
table=re.search(r'const struct sched_runqueue_offsets '+S+r' = \{.*?\n\};',c,re.S).group()
fields=re.findall(r'\.(\w+)\s*=\s*__builtin_offsetof\(struct (\w+),\s*(\w+)\)',table);assert len(fields)==26
# Preserve exact logical line identities around the inserted conditional.
pos=c.index(table);line=1
for l in c[:pos].splitlines(keepends=True):
 z=re.match(r'#line (\d+)',l);line=int(z[1]) if z else line+1
endline=line+table.count('\n')+1
replacement='#ifdef MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE\nextern const struct sched_runqueue_offsets '+S+';\n#else\n#line '+str(line)+'\n'+table+'\n#endif\n#line '+str(endline)+'\n'
newc=c[:pos]+replacement+c[pos+len(table)+1:]
oldfn='fn sched_runqueue_offsets() -> SchedRunqueueOffsets {'
assert rust.count(oldfn)==1
newfn='const fn sched_runqueue_offsets() -> SchedRunqueueOffsets {'
owner='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Paired with MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE in process.c. Reuse the
// existing typed constructor; no scheduler body or callback/lifetime change.
#[cfg(process_global_storage_candidate)]
#[no_mangle]
pub static process_sched_runqueue_offsets: SchedRunqueueOffsets = sched_runqueue_offsets();

const _: () = {
    assert!(core::mem::size_of::<SchedRunqueueOffsets>() == 208);
    assert!(core::mem::align_of::<SchedRunqueueOffsets>() == 8);
};

'''
newrust=rust.replace(oldfn,owner+newfn)
for name,old,new in [('process.c',c,newc),('sched_helpers.rs',rust,newrust)]:
 write('preimages/'+name,old);write('candidate/'+name,new)
 write(name+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/kernel/'+('rust/' if name.endswith('.rs') else '')+name,tofile='b/kernel/'+('rust/' if name.endswith('.rs') else '')+name)))
write('runqueue_storage.FRAGMENT.rs',owner)
# Focused provider uses the exact existing type+constructor and real ABI module.
typ=re.search(r'#\[repr\(C\)\]\npub struct SchedRunqueueOffsets \{.*?\n\}',rust,re.S).group()
fn=re.search(r'fn sched_runqueue_offsets\(\) -> SchedRunqueueOffsets \{.*?\n\}',rust,re.S).group().replace(oldfn,newfn)
provider='#![no_std]\nuse core::mem::offset_of;\n#[path="'+str(R/'kernel/rust/abi.rs')+'"] mod abi;\nuse abi::{Thread, Process, CpuLocalVar, SigCommon};\n'+typ+'\n'+owner+fn+'\n'
write('fixture/provider.rs',provider)
headers='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <sched_helpers.h>
#include <cls.h>
#include <cpulocal.h>
'''
abi=headers+'_Static_assert(sizeof(struct sched_runqueue_offsets)==208,"size");\n_Static_assert(__alignof__(struct sched_runqueue_offsets)==8,"alignment");\n'
for i,((field,structname,member),value) in enumerate(zip(fields,values)):
 abi+=f'_Static_assert(offsetof(struct sched_runqueue_offsets,{field})=={i*8},"{field} position");\n'
 abi+=f'_Static_assert(__builtin_types_compatible_p(__typeof__(((struct sched_runqueue_offsets*)0)->{field}),unsigned long),"{field} type");\n'
 abi+=f'_Static_assert(offsetof(struct {structname},{member})=={value},"{field} accepted current110 value");\n'
write('fixture/genuine_abi.c',abi)
original=table.replace(S,'original_C_runqueue_offsets')
# Per-field reads avoid violating strict aliasing; every C initializer is untouched.
fixture=headers+original+'\nextern const struct sched_runqueue_offsets '+S+';\nextern int printf(const char *, ...);\nint main(void) {\n'
for field,_,_ in fields:fixture+=f' if ({S}.{field} != original_C_runqueue_offsets.{field}) return {1+fields.index((field,_,_)) if False else 1};\n'
fixture+=' printf("RUNQUEUE208 PASS 26 exact fields\\n"); return 0;\n}\n'
write('fixture/oracle.c',fixture)
write('fixture/c_owner.c',headers+'#ifdef MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE\nextern const struct sched_runqueue_offsets '+S+';\n#else\n'+table+'\n#endif\nconst struct sched_runqueue_offsets *const fixture_consumer = &'+S+';\n')
manifest=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='SOURCE_ONLY_UNRUN',baseline=o,acceptance=ref(P.parent/'CURRENT110-INDEPENDENT-DEFAULT-ARTIFACT-ACCEPTANCE.json'),helper=ref(helper),source_bases=[ref(R/'kernel/process.c'),ref(R/'kernel/rust/sched_helpers.rs'),ref(R/'kernel/rust/abi.rs')],symbol=S,size=208,alignment=8,readonly_flags=sec['flags'],bytes_hex=raw.hex(),fields=[dict(field=f,original_struct=t,member=n,actual_current110_value=v) for (f,t,n),v in zip(fields,values)],logical_line_start=line,logical_line_after=endline,selected_C_objects_before=68,proposed_removed_objects=1,selected_C_objects_after_expected=67,whole_file_credit=0,native_credit=0)
write('SOURCE-ONLY.json',json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(status='private source generated',fields=26,bytes=208,logical_lines=[line,endline])))
