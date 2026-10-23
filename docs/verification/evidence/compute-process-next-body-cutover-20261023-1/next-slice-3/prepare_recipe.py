# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,ast,shutil
P=Path(__file__).resolve().parent;F=P/'fixture';O=P/'leaf-output-1';R=Path('/home/holden/mckernel')
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
oldrecipe=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-1/production-abi-layout-1/EXACT-LAYOUT-WITNESS-RECIPE.GRANTED.json';old=json.loads(oldrecipe.read_text());cflags=old['C_argv'][1:old['C_argv'].index('-c')];gcc='/usr/bin/gcc-9';rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
original=(P/'ORIGINAL-SELECTED-C.c').read_text();data=(F/'declarative-data.c').read_text()
selection='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Extracted selected fragment only. */
#include <ihk/debug.h>
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
#define PROCESS_SCHED_PUBLIC_BRIDGE
'''+data+'''#else
#define PROCESS_SCHED_PUBLIC_BRIDGE static
'''+original+'void (*const leaf_fallback_consumer)(unsigned long,int,int) = process_sched_migrate_log_bridge;\n#endif\n'
(F/'selected-fragment.c').write_text(selection)
cmds=[dict(name='00-actual-Rust',argv=[rust,'--edition=2021','--crate-type=lib','--emit=obj','-C','panic=abort','-C','opt-level=2','-C','codegen-units=1','-C','relocation-model=static',str(F/'actual.rs'),'-o',str(O/'actual.o')])]
for name,src,out in [('01-original-selected-macro-and-actual-data','original-and-data.c','original.o'),('02-real-descriptor-control','control.c','control.o'),('05-selected-PUBLIC-fragment','selected-fragment.c','public.o'),('06-fallback-fragment','selected-fragment.c','fallback.o')]:
 flags=cflags if 'fallback' not in name else [x for x in cflags if x!='-DMCKERNEL_RUST_PROCESS_HELPERS']
 cmds.append(dict(name=name,argv=[gcc,*flags,'-Werror','-c',str(F/src),'-o',str(O/out)]))
cmds.insert(3,dict(name='03-host-fixture-link',argv=[gcc,'-std=gnu11','-Wall','-Wextra','-Werror','-O2','-fno-pie','-no-pie',str(F/'main.c'),str(O/'original.o'),str(O/'control.o'),str(O/'actual.o'),'-o',str(O/'equivalence')]))
cmds.insert(4,dict(name='04-functional-diagnostic-equivalence',argv=[str(O/'equivalence')]))
cmds.append(dict(name='07-selected-fragment-partial-link',argv=['/usr/bin/ld','-r',str(O/'public.o'),str(O/'actual.o'),'-o',str(O/'selected.o')]))
for name in ['actual','public','fallback','selected']:
 cmds.append(dict(name=name+'-nm',argv=['/usr/bin/nm','-a',str(O/(name+'.o'))]))
 cmds.append(dict(name=name+'-readelf',argv=['/usr/bin/readelf','--wide','--syms','--section-headers',str(O/(name+'.o'))]))
for x in ['prepare_source.py','prepare_recipe.py']:ast.parse((P/x).read_text())
for row in old['actual_header_config_closure'].values():assert pin(Path(row['path']))==row
bindings=json.loads((P/'SOURCE-BINDINGS.json').read_text())
for rel,row in bindings['changes'].items():assert pin(R/rel)==row['before'] and pin(P/'source'/rel)==row['after']
r=dict(scope=bindings['scope'],status='SOURCE_READY_NOT_EXECUTED_REQUEST_CPU6_ORDINARY_GRANT',profile=dict(CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=120,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,RUST_MIN_STACK=2097152),profile_authority='Reuse accepted Rust1.92/GCC9 ordinary leaf and existing actual-header fixture flags; request root grant before any compiler. ld-r selected fragment only, not kernel link.',header_profile=pin(oldrecipe),tools={x:pin(Path(x)) for x in [rust,gcc,'/usr/bin/ld','/usr/bin/nm','/usr/bin/readelf']},source_files={str(x.relative_to(P)):pin(x) for x in [*F.iterdir(),P/'PRIVATE-PRODUCTION.patch',P/'SOURCE-BINDINGS.json',P/'source/kernel/process.c',P/'source/kernel/rust/sched_helpers.rs'] if x.is_file()},actual_header_config_closure=old['actual_header_config_closure'],commands=cmds,tests=dict(pairs=32000,flag_states=256,int_boundaries=[0,1,-1,-2147483648,2147483647],thread_addresses=['0','1','ULONG_MAX','bit63','0x123456789abcdef0'],real_descriptor_layout_words=6,metadata_selector_identity=['actual C __FILE__=/src/kernel/process.c from retained compile-db','func=process_sched_migrate_log_bridge','line422 original selected callsite','fmtNULL','defaultflags0'],meaningful_behaviors=['allflagsnonzero emit exactlysameformat+name+Cint bytes; zero flags emitsnothing','allthree caller arguments evaluated evenwhen disabled; never dereference threadaddr','kprintfreturn ignored acrosssignedboundaries','existing Rust sysfs setter preserves24linebits andsets8flagbits','original C macro descriptor and Cdata/Rust actualDdebug equality','PUBLIC has descriptor data/noCfunction; fallback exactCbody; actualRust suppliesuniqueT; partiallinkresolvesdescriptor']),source_bindings=pin(P/'SOURCE-BINDINGS.json'),expected_production_object_delta='Same78input fullcrate later: Tprocess_sched_migrate_log_bridge; Ulog removed/Uprocess_sched_migrate_debug added. Default C noTlog/newDdescriptor. OtherRust/C behavior unchanged.',exact_GCC14_wholeTU_defaultlink_native='OPEN',canonical_changed=False)
(P/'EXACT-NEXT-LEAF-RECIPE.NOT-EXECUTED.json').write_text(json.dumps(r,indent=2)+'\n')
(P/'READINESS.md').write_text('''Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private next-slice-3 retires the current process_sched_migrate_log_bridge C runtime body into Rust, reusing the existing crate::debug::Ddebug registry ABI, existing Rust logging pattern and existing kprintf. C fallback body stays byte-exact. The default retains DECLARATIVE C __verbose descriptor data only, with current C __FILE__, samefunction, original source-bound callsite422, fmtNULL and DDEBUG_DEFAULT. This preserves existing file/function/line control selectors instead of silently replacing them with Rust source selectors. No new compute C function, layout or logging subsystem.

Rust reads the existing flag byte through the current Ddebug line_flags representation and emits exactly the same format/name/tid/cpu for any nonzero flags. Arguments are evaluated at the caller even when disabled; thread_addr is ignored and never dereferenced; kprintf result is ignored. Existing Rust syscall control continues to own descriptor mutation. The actual C macro/types/real-header fixture and actual Rust descriptor type/setter/function are prepared for32000 pairs across all256flags and integer/address/return boundaries,6layoutwords, exact selector identity, default/fallback symbols and selected fragment partial link.

No compiler has executed. Root ordinary CPU6 grant requested: onejob2GiBAS/60CPU/120wall+6/32MiBFSIZE/NOFILE256/core0 Rust1.92/GCC9/CGU1/2MiBstack, existing accepted real-header profile; exact16commands/source/tool/header hashes in recipe. No unsafe host-state instructions, kernel/guest/root/Docker/fullcrate here. Canonical/candidate11 untouched; GCC14wholeTU/defaultlink/native remainOPEN.

One source preparation failure is retained: it assumed a /work/source filename; actual retained compile-db uses /src/kernel/process.c. The bounded correction binds the unique exact process entry and uses that filename only in controlled fixture #line. No compiler was attempted during that failure.
''')
D=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1/next-slice-3';D.mkdir(exist_ok=True)
for x in P.iterdir():
 if x.is_file():shutil.copyfile(x,D/x.name)
 elif x.name in ['source','fixture']:shutil.copytree(x,D/x.name,dirs_exist_ok=True)
print(json.dumps(dict(recipe=pin(P/'EXACT-NEXT-LEAF-RECIPE.NOT-EXECUTED.json'),patch=pin(P/'PRIVATE-PRODUCTION.patch'),commands=len(cmds),compiler_executed=False,CPU_held=False)))
