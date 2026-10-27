"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixed existing global32 qualification preparation. No compile/CPP/executable/guard.
"""
from pathlib import Path
import hashlib,json,re,difflib,importlib.util
P=Path(__file__).resolve().parent;E=P.parent;R=next(x for x in P.parents if (x/'kernel/process.c').exists())
N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,s):
 p=P/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def js(n,x):save(n,json.dumps(x,indent=2)+'\n')
assert ref(N/'READY.SOURCE-ONLY.json')['sha256']=='e7d77b16826fb96189c35a07f444157eadbc75e3290b618bbd4c24451c0cbd9c'
rows=json.loads((N/'EXACT46-SLOT78-MAP.json').read_text());globalrows=[x for x in rows if not x['local']];locals=[x for x in rows if x['local']];assert len(globalrows)==32 and sum(x['slots'] for x in globalrows)==64 and len(locals)==14
# Exact existing Rust representation, not reimplementation of storage or bodies.
debug=(N/'references/kernel/rust/debug.rs')
if not debug.exists():debug=R/'kernel/rust/debug.rs'
shape=re.search(r'#\[repr\(C\)\]\npub struct Ddebug \{.*?\n\}',debug.read_text(),re.S).group()
provider='#![no_std]\nmod debug {\n'+shape+'\n}\n#[path="'+str(N/'postimage/kernel/rust/process_verbose_data.rs')+'"] mod process_verbose_data;\n'
save('fixture/provider.rs',provider)
abi='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <ihk/debug.h>
_Static_assert(sizeof(struct ddebug)==32,"Ddebug32");
_Static_assert(__alignof__(struct ddebug)==8,"Ddebugalign8");
_Static_assert(__builtin_offsetof(struct ddebug,file)==0,"file0");
_Static_assert(__builtin_offsetof(struct ddebug,func)==8,"func8");
_Static_assert(__builtin_offsetof(struct ddebug,fmt)==16,"fmt16");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ddebug*)0)->file),const char *),"file pointer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ddebug*)0)->func),const char *),"func pointer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ddebug*)0)->fmt),const char *),"fmt pointer ABI");
const struct ddebug f02_genuine_bitfield_witness={.file=0,.func=0,.fmt=0,.line=0x123456,.flags=1};
'''
save('fixture/genuine_abi.c',abi)
# Selective four-insertion rebase onto actual current112 CMake; no configure.
cm=R/'kernel/CMakeLists.txt';assert ref(cm)['sha256']=='7f808fcd791cb1a96c06976faeb5313cf991e6e7aa50c38e49d8bb4d60676b69'
base=(N/'base/kernel/CMakeLists.txt').read_text().splitlines(True);target=(N/'postimage/kernel/CMakeLists.txt').read_text().splitlines(True);current=cm.read_text();composed=current;ops=[]
for tag,i,j,k,l in difflib.SequenceMatcher(a=base,b=target,autojunk=False).get_opcodes():
 if tag=='equal':continue
 assert tag=='insert' and i==j
 anchor=''.join(base[max(0,i-3):i]);addition=''.join(target[k:l]);assert composed.count(anchor)==1
 composed=composed.replace(anchor,anchor+addition,1);ops.append(dict(anchor=anchor,addition=addition))
assert len(ops)==4
save('cmake-proposal/current112.CMakeLists.txt',current);save('cmake-proposal/composed.CMakeLists.txt',composed)
save('cmake-proposal/current112-to-verbose32.diff',''.join(difflib.unified_diff(current.splitlines(True),composed.splitlines(True),fromfile='a/kernel/CMakeLists.txt',tofile='b/kernel/CMakeLists.txt')))
js('CMAKE-ENV-BINDING-PROPOSAL.json',dict(scope=__doc__.splitlines()[0],status='SELECTIVE_CURRENT112_SOURCE_COMPOSITION_ONLY_UNCONFIGURED',current112=ref(cm),foreground_base=ref(N/'base/kernel/CMakeLists.txt'),foreground_post=ref(N/'postimage/kernel/CMakeLists.txt'),composed=ref(P/'cmake-proposal/composed.CMakeLists.txt'),insertions=ops,selected='Rust-enabled supported x86; option ENABLE_RUST_PROCESS_VERBOSE_DATA defaultON',flags_default='ENABLE_PROCESS_DEBUG_PRINT defaultOFF maps0; ON maps1 and same CDEBUG_PRINT_PROCESS',file_input='Actual ${CMAKE_CURRENT_SOURCE_DIR}/process.c; Rust env plus C __FILE__ assertion; supported literal path regex; no prefix map assumed',local14='Never selected by CMake; original explicit compile_error unchanged',stamp='Generated stable selected/file/flags input is a Rust dependency; process C + debug header + new module explicit dependencies'))
prior=json.loads((E/'m14-f02-next-readonly-data-new12h-1/successor-host-profile-2/PROFILE.NOT-GRANTED.json').read_text());oldrecipe=json.loads((E/'m14-f02-next-readonly-data-new12h-1/EXACT-SEVEN-COMMAND-HOST-RECIPE.NOT-ADMITTED.json').read_text())['commands'];c=oldrecipe[0]['argv'][:-2];c=c+['-DMCKERNEL_RUST_PROCESS_GLOBAL_STORAGE'];rustc=oldrecipe[1]['argv'][0];source=N/'postimage/kernel/process.c';out=P/'HOST-output-proposed-1'
assert not out.exists()
rbase=[rustc,'--edition=2021','--crate-type=lib','--emit=obj','--crate-name','f02_verbose32_host','-C','panic=abort','-C','opt-level=1','-C','codegen-units=1','-C','relocation-model=static','--cfg','process_verbose_data']
rustargs=rbase+[str(P/'fixture/provider.rs')]
def env(mode):return ['/usr/bin/env','MCKERNEL_PROCESS_C_FILE='+str(source),'MCKERNEL_PROCESS_DDEBUG_FLAGS='+str(mode)]
def cselect(mode,file=None):return c+['-DMCKERNEL_RUST_PROCESS_VERBOSE_DATA','-DMCKERNEL_PROCESS_DDEBUG_FLAGS='+str(mode),'-DMCKERNEL_PROCESS_DDEBUG_FILE="'+str(source if file is None else file)+'"']+(['-DDEBUG_PRINT_PROCESS'] if mode else [])
commands=[('00-genuine-Ddebug-ABI-bitfield-object',c+['-c',str(P/'fixture/genuine_abi.c'),'-o',str(out/'abi.o')])]
for mode in [0,1]:commands.append(('0'+str(mode+1)+'-existing-Rust-global32-flags'+str(mode),env(mode)+rustargs+['-o',str(out/('rust'+str(mode)+'.o'))]))
for mode in [0,1]:commands.append(('0'+str(mode+3)+'-actual-selected-process-TU-flags'+str(mode),cselect(mode)+['-c',str(source),'-o',str(out/('selected'+str(mode)+'.o'))]))
commands.append(('05-actual-fallback-process-TU',c+['-c',str(source),'-o',str(out/'fallback.o')]))
for mode in [0,1]:commands.append(('0'+str(mode+6)+'-partial-link-flags'+str(mode),['/usr/bin/ld','-r',str(out/('selected'+str(mode)+'.o')),str(out/('rust'+str(mode)+'.o')),'-o',str(out/('joint'+str(mode)+'.o'))]))
commands.append(('08-exact32-global14local78slots-ELF-and-retained-consumers',['/usr/bin/python3','-B',str(P/'qualify_metadata.py'),str(out)]))
# Fixed negative controls run only after Root grants the whole HOST profile.
negative=[]
def case(name,argv,envv,diagnostic):negative.append(dict(name=name,argv=argv,environment=envv,diagnostic=diagnostic))
baseenv={'PATH':'/usr/bin:/bin','LC_ALL':'C','RUST_BACKTRACE':'0'}
for name,extra,diagnostic in [('missing-file',{'MCKERNEL_PROCESS_DDEBUG_FLAGS':'0'},'MCKERNEL_PROCESS_C_FILE'),('missing-flags',{'MCKERNEL_PROCESS_C_FILE':str(source)},'MCKERNEL_PROCESS_DDEBUG_FLAGS'),('bad-flags',{'MCKERNEL_PROCESS_C_FILE':str(source),'MCKERNEL_PROCESS_DDEBUG_FLAGS':'2'},'process debug flags must match'),('empty-file',{'MCKERNEL_PROCESS_C_FILE':'','MCKERNEL_PROCESS_DDEBUG_FLAGS':'0'},'process C filename must not be empty')]:case(name,rustargs+['-o',str(out/('negative-'+name+'.o'))],dict(baseenv,**extra),diagnostic)
case('local14-disabled',rustargs+['--cfg','process_verbose_local_companions','-o',str(out/'negative-local14.o')],dict(baseenv,MCKERNEL_PROCESS_C_FILE=str(source),MCKERNEL_PROCESS_DDEBUG_FLAGS='0'),'C-local debug storage requires coordinated companion config migration')
case('C-filename-mismatch',cselect(0,'/wrong/process.c')+['-fsyntax-only',str(source)],baseenv,'process debug C filename mismatch')
# DEBUG_PRINT_PROCESS is absent but expected DDEBUG_DEFAULT input is intentionally1.
mismatch=cselect(0);mismatch=[x.replace('MCKERNEL_PROCESS_DDEBUG_FLAGS=0','MCKERNEL_PROCESS_DDEBUG_FLAGS=1') for x in mismatch]
case('C-flags-mismatch',mismatch+['-fsyntax-only',str(source)],baseenv,'process debug flags mismatch')
js('NEGATIVE-CONTROLS.NOT-ADMITTED.json',dict(scope=__doc__.splitlines()[0],cases=negative,output=str(out),expected_stdout='VERBOSE32 PASS 7 bounded missing/mismatch/local14 controls\n'))
commands.append(('09-fixed7-negative-build-input-controls',['/usr/bin/python3','-B',str(P/'negative_controls.py'),str(P/'NEGATIVE-CONTROLS.NOT-ADMITTED.json')]))
js('COMMAND-RECIPE.NOT-ADMITTED.json',dict(scope=__doc__.splitlines()[0],status='SOURCE_ONLY_NOT_GRANTED',commands=[dict(name=n,argv=a,purpose=__doc__.splitlines()[0]+' '+n) for n,a in commands],output=str(out),expected_stdout='VERBOSE32 PASS 7 bounded missing/mismatch/local14 controls\n'))
js('SOURCE-CONTEXT.json',dict(scope=__doc__.splitlines()[0],foreground_ready=ref(N/'READY.SOURCE-ONLY.json'),foreground_module=ref(N/'postimage/kernel/rust/process_verbose_data.rs'),foreground_C=ref(source),original_metadata=ref(N/'RETAINED-ELF-READBACK.json'),map=ref(N/'EXACT46-SLOT78-MAP.json'),focused_Ddebug_source=ref(debug),CMake_composition=ref(P/'CMAKE-ENV-BINDING-PROPOSAL.json'),positive_compiler_commands=8,negative_controls=7,LOCAL14_C_owned=True,readonly_config_changes=0,native_delta=0,whole_file_delta=0))
print('PASS fixed32 source recipe and four selective current112 CMake insertions generated; compiler/workloads0')
