"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source/ABI/provider/origin and bounded warning seal for actual116; no runtime calls.
"""
from pathlib import Path
import ast,collections,hashlib,json,struct,re,importlib.util
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('base116seal',D/'review_actual116.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);globals().update({k:v for k,v in vars(m).items() if not k.startswith('__')})
def extract_current(path,names):
 nodes=[n for n in ast.parse(Path(path).read_bytes()).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+':FINITE_READERS','exec'),globals())
extract_current(auth(accepted['reader_sources']['review_consumers115.py']),{'literal','relocated_function'})
host=None;HOST_FILE=b'';PROD_FILE=b'';HOST_X86_FILE=b'';PROD_X86_FILE=b'';finite_sections=set()
source_review=read(auth(profile['qualified116_source_review']));auth(profile['qualified116_source_ready']);adoption=read(auth(profile['actual_root_adoption']));assert profile['actual_root_adoption']['sha256']=='ef82f32879b49729b985ba78bb4cf5bcb6f58bb66126185a8237419366aadde2'
for r in adoption['source_changes']:auth(r['retained_candidate'])
assert read(auth(source_review['production_recipe']))['ordered_commands']==profile['exact_commands']
closure=read(auth(profile['inputs']['source_directory_exports'][0]['manifest']));assert len(closure['files'])==121 and profile['inputs']['source_directory_exports'][0]['readonly'] is True
origin=profile['origin_source_materialization'];alias=read(auth(origin['actual_origin_producer']));original=read(auth(alias['source_receipt']));assert alias['source_receipt']['sha256']=='fa9c08cdd8bc382a13582b6b06c830f68879d831e4bb81cb4f5d0c2989874264'
assert original['returncode']==0 and alias['direct_child_joined'] is True and alias['streams_closed'] is True and alias['compiler_executed'] is False
for key,r in origin.items():
 if isinstance(r,dict):auth(r)
binding=read(auth(origin['actual_origin_binding']));assert binding['composed_arch_source']['sha256']==source_review['source_sha256']['arch/x86_64/kernel/syscall.c'] if 'composed_arch_source' in binding else True
prefix=read(auth(accepted['proofs']['ACTUAL-STORAGE-REGISTRY-PRODUCER-PREFIX.json']));inherited=[r['name'] for r in prefix['selected_providers']];assert len(inherited)==60 and not set(inherited)&set(providers)
for n in inherited+providers:
 s=own(new,n);f=image.sym(n);assert (s['bind'],s['type'],s['size'])==(f['bind'],f['type'],f['size']) and s['bind']==1 and s['type']==2
 assert not any(z['name']==n and z['shndx'] for r,e in objects if e is not new for z in e.symbols),n
wake_review=read(auth(source_review['qualification']['WAKE4_actual']));wake=elf(auth(wake_review['retained_two_Rust_artifacts'][0]));wakeproof=[]
for n in ['ptrace_wakeup_clear_saved_bridge','ptrace_wakeup_set_single_step_bridge','ptrace_wakeup_trace_syscall_bridge','ptrace_wakeup_pending_take_bridge']:
 a,ab,ar,_=relocated_function(wake,n);b,bb,br,rr=relocated_function(new,n,image);assert (a['size'],a['type'],a['bind'])==(b['size'],b['type'],b['bind']) and ab==bb and ar==br
 wakeproof.append(dict(name=n,input=b,final=image.sym(n),qualified_HOST_equal=True,full_current_final_bytes=True))
shm=own(new,'arch_do_shmget_bridge');raw=data(new,shm);rr=rels(new,shm);assert raw.hex()=='554889e548b800000000000000005dffe0' and len(rr)==1 and rr[0]['offset']==6 and rr[0]['type']==1 and rr[0]['addend']==0 and rr[0]['target']['name']=='do_shmget'
provider=own(new,'do_shmget');consumer=own(new,'sys_shmget');assert provider['size']==2993 and consumer['size']==338
sysedge=[r for r in rels(new,consumer) if r['target']['name']=='arch_do_shmget_bridge'];assert len(sysedge)==1 and sysedge[0]['offset']==104 and sysedge[0]['type']==1 and sysedge[0]['addend']==0
for n in ['arch_do_shmget_bridge','do_shmget','sys_shmget']:relocated_function(new,n,image)
# Enumerate all current linked allocated consumers of eight new providers.
edges=[]
for r,e in objects:
 for s in e.symbols:
  if not (0<s['shndx']<len(e.sections) and s['type'] in (1,2) and e.sections[s['shndx']]['flags']&2):continue
  for rel in rels(e,s):
   if rel['target']['name'] not in providers:continue
   assert rel['type']==1
   value=struct.unpack_from('<Q',image.bytes(image.sym(s['name'])),rel['offset'])[0];assert value==image.sym(rel['target']['name'])['value']+rel['addend']
   edges.append(dict(input=r['link_token'],consumer=s['name'],offset=rel['offset'],target=rel['target']['name'],final_address=hex(value)))
active=[s for s in pc.sections if s['flags']&2 and s['size']];assert len(active)==1 and (active[0]['name'],active[0]['type'],active[0]['flags'],active[0]['size'],active[0]['align'])==('.note.gnu.property',7,2,48,8)
for n in ['arch_start','main','monitor_init','init_host_ikc2linux','init_host_ikc2mckernel','prepare_process_ranges_args_envs','mcexec_v10_trace_enter_user']:assert image.sym(n)['shndx']
assert struct.unpack_from('<16sHHIQQQIHHHHHH',image.raw)[4]==image.sym('arch_start')['value']
newimports={s['name'] for s in new.symbols if s['name'] and not s['shndx']};oldimports={s['name'] for s in old.symbols if s['name'] and not s['shndx']}
def warnings(p):return re.findall(r'^.*?warning(?:\[[^\]]+\])?: (.*)',p.read_text(),re.M)
oldP=Path(accepted['tuple']['Rust']['path']).parents[6]
# Use exact known completed producer directories, never replay a compiler.
prior115=E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-4';prior114=E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'
rwnew=warnings(P/'OUTPUT/work/evidence/00.stderr');rwold=warnings(prior115/'OUTPUT/work/evidence/00.stderr');cwnew=warnings(P/'OUTPUT/work/evidence/01.stderr');cwold=warnings(prior114/'OUTPUT/work/evidence/01.stderr')
report=dict(scope=__doc__.splitlines()[0],source_review=profile['qualified116_source_review'],source_adoption=profile['actual_root_adoption'],closed_source_manifest=profile['inputs']['source_directory_exports'][0]['manifest'],source_closure=121,origin_alias=origin['actual_origin_producer'],original_origin=alias['source_receipt'],actual_origin_refs=origin,focused_selected_Rust_providers=68,retained_process_note_bytes=48,process_runtime_ALLOC_bytes=0,WAKE4HOST_and_final=wakeproof,SHM=dict(actual_bytes=17,historical_expectation_bytes=12,frame_pointer_delta_bytes=5,raw_hex=raw.hex(),provider='do_shmget',provider_bytes=2993,current_consumer='sys_shmget',consumer_bytes=338,consumer_relocation=sysedge,same_low32_key_and_size_flags_register_ABI=True,full_final_bytes_readback=True),new_provider_current_edges=edges,imports_added=sorted(newimports-oldimports),imports_removed=sorted(oldimports-newimports),Rust_warning_messages_added=list((collections.Counter(rwnew)-collections.Counter(rwold)).elements()),Rust_warning_messages_removed=list((collections.Counter(rwold)-collections.Counter(rwnew)).elements()),C_warning_messages_added=list((collections.Counter(cwnew)-collections.Counter(cwold)).elements()),C_warning_messages_removed=list((collections.Counter(cwold)-collections.Counter(cwnew)).elements()),arch_C_stderr_empty=(P/'OUTPUT/work/evidence/02.stderr').stat().st_size==0,ld_warning_equal115=(P/'OUTPUT/work/evidence/03.stderr').read_bytes()==(prior115/'OUTPUT/work/evidence/03.stderr').read_bytes(),C_object_deltas={key:dict(before=len(allocated(a,1)),after=len(allocated(b,1)),removed=sorted(set(allocated(a,1))-set(allocated(b,1))),added=sorted(set(allocated(b,1))-set(allocated(a,1)))) for key,a,b in [('generic',oldkc,kc),('arch',oldac,ac)]},Rust_data_added=sorted(set(allocated(new,1))-set(allocated(old,1))),Rust_data_removed=sorted(set(allocated(old,1))-set(allocated(new,1))),required_startup_and_ELF_entry=True,runtime_authority=None)
p=D/'ACTUAL-SOURCE-ABI-ORIGIN-EDGE-SEAL.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':ref(p),'focused_Rust':68,'edges':len(edges),'Rustwarnings_added':report['Rust_warning_messages_added'],'Cwarnings_added':report['C_warning_messages_added'],'imports_added':report['imports_added'],'imports_removed':report['imports_removed'],'Cdata':report['C_object_deltas'],'Rustdataadded':report['Rust_data_added']}))
