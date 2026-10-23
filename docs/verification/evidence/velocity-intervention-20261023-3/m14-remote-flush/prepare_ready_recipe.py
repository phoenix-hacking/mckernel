# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,ast,shutil
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');F=P/'fixture';O=P/'output-1'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
b=json.loads((P/'SOURCE-AND-FIXTURE-PREPARATION.json').read_text());c=(R/'kernel/mem.c').read_text();current=F/'actual_declarations.h';decl=current.read_text();at=decl.index('typedef ');prefix=c[c.index('#include <kmsg.h>'):c.index('static unsigned long pa_start')];oldheader=decl;newheader='/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n'+prefix+decl[at:];current.write_text(newheader)
for name in ['actual_original_vs_export.c','actual_selected_region.c','actual_header_abi.c']:
 q=F/name;s=q.read_text();assert s.startswith(oldheader);s=newheader+s[len(oldheader):]
 if name=='actual_original_vs_export.c':s=s.replace('#include <assert.h>\n#include <stdio.h>\n#include <string.h>','extern int printf(const char *, ...);\n#define assert(c) do { if (!(c)) return __LINE__; } while (0)')
 if name=='actual_selected_region.c':s=s.replace('/* Immutable source-header geometry;', 'struct tlb_flush_entry tlb_flush_vector[IHK_TLB_FLUSH_IRQ_VECTOR_SIZE];\n\n/* Immutable source-header geometry;',1)
 q.write_text(s)
# Exact finite previous production mem-TU dependency descriptor, mapped to the
# retained header tree already accepted for the GCC9 header-fixture profile.
D=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/mem.c.o.d');BUILD=D.parents[3];C9=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-9/default-image-preparation-1/source-materialization-attempt-1/materialized-source');headers={}
for name in sorted(set(D.read_text().split(':',1)[1].replace('\\\n',' ').split())):
 if name=='/src/kernel/mem.c':continue
 q=C9/Path(name).relative_to('/src') if name.startswith('/src/') else BUILD/Path(name).relative_to('/work/output/build') if name.startswith('/work/output/build/') else Path(name)
 assert q.is_file(),q;headers[str(q)]=pin(q)
for key in ['lib/include/ihk/mm.h','lib/include/ihk/cpu.h','kernel/include/affinity.h','kernel/include/process.h']:
 assert pin(C9/key)['sha256']==pin(R/key)['sha256'],key
# Reuse the accepted ELF OBJECT data decoder, extend only scalar width4/8.
prior=Path('/home/holden/mckernel-work/host-preparation/compute-process-next-body-cutover-20261023-1/next-slice-1/production-abi-layout-1/run_layout_owned.py');tree=ast.parse(prior.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='object_words');decoder=ast.get_source_segment(prior.read_text(),fn).replace('def object_words(path,name,count):','def object_words(path,name,count,width=8):').replace('count*8','count*width').replace("'Q'*count","('Q' if width==8 else 'I')*count")
observer='''# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# ELF metadata/source observer only; never executes compiled target callbacks.
from pathlib import Path
import struct,json
P=Path(__file__).resolve().parent.parent;O=P/'output-1'
'''+decoder+'''
def symbols(path):
 raw=path.read_bytes();off=struct.unpack_from('<Q',raw,40)[0];ents,n=struct.unpack_from('<HH',raw,58);secs=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*ents) for i in range(n)];rows=[]
 for sec in secs:
  if sec[1]!=2:continue
  strings=secs[sec[6]];tab=raw[strings[4]:strings[4]+strings[5]]
  for at in range(sec[4],sec[4]+sec[5],24):
   ni,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',raw,at);end=tab.find(bytes([0]),ni);assert end>=ni
   rows.append((tab[ni:end].decode(),info>>4,info&15,idx,value,size))
 return rows
def named(rows,name):return [r for r in rows if r[0]==name]
cm=object_words(O/'header-abi.o','M14_C_TLB_LAYOUT',15);rm=object_words(O/'rust-entry.o','M14_RUST_TLB_LAYOUT',15);assert cm==rm,(cm,rm);geometry=object_words(O/'header-abi.o','M14_C_TLB_GEOMETRY',3,4)
r=symbols(O/'rust-entry.o');c=symbols(O/'selected-c.o');f=symbols(O/'fallback-c.o');p=symbols(O/'partial.o')
entry='remote_flush_tlb_array_cpumask';rr=named(r,entry);assert len(rr)==1 and rr[0][1:3]==(1,2) and rr[0][3]!=0
assert len(named(c,entry))==1 and named(c,entry)[0][3]==0
assert len(named(f,entry))==1 and named(f,entry)[0][3]!=0
assert len(named(p,entry))==1 and named(p,entry)[0][3]!=0
names=['mem_tlb_'+n+'_bridge' for n in ['rdtsc','current_cpu','get_vector','interrupt_cpu','noirq_lock','noirq_unlock','atomic_set','atomic_inc','atomic_read','flush_single','flush_all','pause']]
for name in names:
 assert len(named(r,name))==1 and named(r,name)[0][3]==0,name
 assert len(named(c,name))==1 and named(c,name)[0][1:3]==(1,2) and named(c,name)[0][3]!=0,name
 # Unused fallback-only bridges may be optimized away; those retained are local.
 assert all(row[1]==0 for row in named(f,name)),name
for name in ['mem_remote_tlb_geometry','tlb_flush_vector']:
 assert len(named(r,name))==1 and named(r,name)[0][3]==0,name
 assert len(named(c,name))==1 and named(c,name)[0][3]!=0,name
assert object_words(O/'selected-c.o','mem_remote_tlb_geometry',3,4)==geometry
assert named(c,'tlb_flush_vector')[0][5]==geometry[0]*cm[6]
assert len(named(r,'mem_remote_flush_tlb_array_body_result'))==1 and named(r,'mem_remote_flush_tlb_array_body_result')[0][3]==0
result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_FOCUSED_ENTRY_ABI_HEADER_SELECTION_AND_PARTIAL_LINK_ONLY',layout_words=15,geometry_words=3,actual_header_geometry=geometry,actual_layout=cm,callback_identities=12,Rust_entry_one_definition=True,selected_C_no_entry_definition=True,fallback_C_entry_preserved=True,partial_link_one_Rust_entry=True,underlying_Rust_body_algorithm_executed=False,whole_C_TU=False,production_fullcrate=False,default_kernel_link=False,native=False)
(P/'ACTUAL-ABI-SELECTION-OBSERVATION.json').write_text(json.dumps(result,indent=2)+'\\n');print(json.dumps(result))
'''
(F/'observe_actual_artifacts.py').write_text(observer);ast.parse(observer)
base=b['C_header_base'];gcc=base[0];rust=b['Rust_leaf_compiler'];nm='/usr/bin/nm';readelf='/usr/bin/readelf';ld='/usr/bin/ld';py='/home/holden/anaconda3/bin/python3'
commands=[]
def cmd(name,argv):commands.append(dict(name=name,argv=argv,purpose=b['scope']+' Focused ABI/callback binding or inert ELF observation; no kernel/TLB/IRQ execution.'))
cmd('00-Rust-actual-export-compile',[rust,'--edition=2021','--crate-type=lib','--emit=obj='+str(O/'rust-entry.o'),'-C','opt-level=2','-C','panic=abort','-C','codegen-units=1',str(F/'actual_export.rs')])
cmd('01-C-original-wrapper-recorder-compile',base+['-c',str(F/'actual_original_vs_export.c'),'-o',str(O/'recorder.o')])
cmd('02-focused-C-Rust-recorder-link',[gcc,'-no-pie',str(O/'recorder.o'),str(O/'rust-entry.o'),'-o',str(O/'fixture')])
cmd('03-functional-original-C-Rust-entry-pairs',[str(O/'fixture')])
cmd('04-selected-C-callback-region-compile',base+['-DMCKERNEL_RUST_MEM_HELPERS','-c',str(F/'actual_selected_region.c'),'-o',str(O/'selected-c.o')])
cmd('05-fallback-C-region-compile',base+['-c',str(F/'actual_selected_region.c'),'-o',str(O/'fallback-c.o')])
cmd('06-actual-header-ABI-data-compile',base+['-c',str(F/'actual_header_abi.c'),'-o',str(O/'header-abi.o')])
for num,name,obj in [(7,'Rust-symbols','rust-entry.o'),(8,'selected-C-symbols','selected-c.o'),(9,'fallback-C-symbols','fallback-c.o')]:cmd('%02d-'%num+name,[nm,'-a',str(O/obj)])
for num,name,obj in [(10,'Rust-ELF','rust-entry.o'),(11,'selected-C-ELF','selected-c.o'),(12,'header-ABI-ELF','header-abi.o')]:cmd('%02d-'%num+name,[readelf,'-SWrs',str(O/obj)])
cmd('13-inert-partial-link',[ld,'-r',str(O/'selected-c.o'),str(O/'rust-entry.o'),'-o',str(O/'partial.o')])
cmd('14-partial-link-symbols',[nm,'-a',str(O/'partial.o')])
cmd('15-functional-ABI-selection-observer',[py,'-I','-B',str(F/'observe_actual_artifacts.py')])
# No compilation or execution here: just finite identities/preimages and recipe.
tools={x:pin(Path(x)) for x in [rust,gcc,nm,readelf,ld,py]};assert tools[rust]['sha256']=='028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1';assert tools[gcc]['sha256']=='6cb2d84ccd9fd3485d4e47ba032e626be65692601c38fad46866a6b565f3100f'
b['fixture_sources']={q.name:pin(q) for q in F.iterdir()};b['header_config_closure']=headers;b['retained_actual_mem_TU_dependency_descriptor']=pin(D);b['C_recorder_base']=base;b['scope_qualification']='GCC9 focused actual-header/entry recorder scope only; exactGCC14wholememTU/defaultkernel/native OPEN.'
(P/'SOURCE-AND-FIXTURE-PREPARATION.json').write_text(json.dumps(b,indent=2)+'\n')
recipe=dict(scope=b['scope'],status='READY_ROOT_ORDINARY_GRANT_REQUIRED_NOT_EXECUTED',source_binding=pin(P/'SOURCE-AND-FIXTURE-PREPARATION.json'),source_files={str(q):pin(q) for q in [*F.iterdir(),P/'candidate/kernel/mem.c',P/'candidate/kernel/rust/mem_helpers.rs',P/'PRIVATE-REMOTE-FLUSH.patch']},tools=tools,commands=commands,proposed_profile=b['profile_proposed'],prior_profile=b['prior_accepted_header_profile'],header_closure=headers,expected_pairs=1792,expected_layout_words=15,expected_callback_identities=12,compiler_jobs=0,canonical_writes=0,remaining_open=['actualwholeCmemTU/exactGCC14','actualproductionRust78inputconsumer','defaultkernellink','nativeTLBfunctionalproof'],failure_family=dict(first_candidate=True,bounded_corrections_used=0,stop_after='onefailedcandidate+oneboundedcorrection then differentexpert; preserveallfailures'))
Q=P/'EXACT-ORDINARY-FIXTURE-RECIPE.NOT-EXECUTED.json';Q.write_text(json.dumps(recipe,indent=2)+'\n');print(json.dumps(dict(recipe=pin(Q),commands=len(commands),header_files=len(headers),source_binding=pin(P/'SOURCE-AND-FIXTURE-PREPARATION.json'))))
