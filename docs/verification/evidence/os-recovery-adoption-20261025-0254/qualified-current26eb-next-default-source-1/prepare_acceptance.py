"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare current26eb+six-functions+timer120 exact observers before any compiler.
"""
from pathlib import Path
import ast,copy,hashlib,json,struct
D=Path(__file__).resolve().parent;E=D.parent;B=E/'ROOT-SYNC-PROCESSVM-HOST13-FIVE-BUILD-ADMISSION-1';PREV=E/'sync-processvm-host13-validator-import-suffix-1';TEMPLATES=E/'sync-processvm-host13-unused-import-warning-correction-1/validator-templates';Q=E/'qualified-sync-processvm-host13-five-stage-source-1'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(p.read_text())
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
def once(s,a,b):
 assert s.count(a)==1,(a[:90],s.count(a));return s.replace(a,b,1)
plan=read(D/'COHERENT-NEXT-DEFAULT-SOURCE-PLAN.NOT-GRANTED.json');P=read(D/'PROFILE.SOURCE-ONLY.json');old=read(Q/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json');providers=read(PREV/'actual-qualification-1/NEXT-PROVIDERS-RESULT.json');carry=[r['name'] for r in providers['phases']['actual_thirty_five_Rust_exports']];assert len(carry)==35
new=plan['new_public_Rust_function_exports'];assert len(set(carry+new))==39
source=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py';raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd';ns={'struct':struct};exec(compile(ast.Module(body=[n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf'],type_ignores=[]),'accepted exact metadata parser','exec'),ns);Elf=ns['_ReuseElf']
f3=read(Path(plan['F03_source']['path']));removed3=f3['expected_removed_C_names'];removed6=[r['leaf'] for r in []]+['arch_copy_to_user_bridge','arch_copy_from_user_bridge','arch_syscall_forward_context_bridge'];baseline={};expected={}
for token,removed in [('CMakeFiles/mckernel.img.dir/syscall.c.o',removed3),('CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o',removed6)]:
 path=B/'OUTPUT/work/output/build/kernel'/token;elf=Elf(path);fs={s['name']:s for s in elf.symbols if s['type']==2 and 0<s['shndx']<len(elf.sections) and elf.sections[s['shndx']]['flags']&2};assert set(removed)<=set(fs);baseline[token]=dict(object=ref(path),allocated_FUNC_count=len(fs),all_names=sorted(fs),selected_metadata=[fs[n] for n in removed]);expected[token]=dict(remove=removed,expected_remaining_names=sorted(set(fs)-set(removed)),unexplained_compiler_elisions_allowed=[])
U={s.split(None,1)[1] for s in (PREV/'actual-qualification-1/production-rust-undefined.nm').read_text().splitlines()};removed=removed6+['process_timer_runtime_offsets'];assert set(removed)<=U
x=copy.deepcopy(old);x.update(status='STATIC_CURRENT26EB_SIX_FUNCTION_TIMER120_EXACT_ACCEPTANCE_BEFORE_COMPILER',source_plan=ref(D/'COHERENT-NEXT-DEFAULT-SOURCE-PLAN.NOT-GRANTED.json'),profile_template=ref(D/'PROFILE.SOURCE-ONLY.json'),prior_accepted_artifact=ref(E/'FIVE-DEFAULT-INDEPENDENT-ARTIFACT-ACCEPTANCE.json'),prior_accepted_producer=ref(B/'OUTPUT/work/evidence/producer-contract.json'),prior_first_compiler_epoch=read(B/'OUTPUT/work/evidence/producer-contract.json')['commands'][0]['started_at_epoch'],all_Rust_exports=carry+new,carried_forward_Rust_exports=carry,new_unique_Rust_exports=new,baseline_C_objects=baseline,expected_C_function_sets=expected,expected_new_undefined=sorted(U-set(removed)),baseline_undefined=ref(PREV/'actual-qualification-1/production-rust-undefined.nm'),exact_undefined_delta=dict(removed=removed,added=[],all_other_provider_witnesses_exact=True),cumulative_seed_undefined_removed=sorted(set(old['cumulative_seed_undefined_removed'])|set(removed)),process_current_object=ref(B/'OUTPUT/work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o'),process_current_OBJECT_count=71,process_expected_OBJECT_count=70,process_expected_FUNC_count=0,new_timer120=dict(actual_HOST=plan['timer_actual_result'],implementation=plan['timer_implementation'],only_new_data_owner='process_timer_runtime_offsets',size=120,alignment=8,words=15),current_accepted_13_argument_disposition=ref(E/'FIVE-HOST13-INDEPENDENT-FINAL-CONSUMER-ARGUMENTS.json'),process_compile_disposition=P['unchanged_completed_process_prefix']['Root_decision'],actual_final_consumer13_bindings=None,HOST13_default_retirement=False)
process=Elf(Path(x['process_current_object']['path']));timer=process.sym('process_timer_runtime_offsets');sec=process.sections[timer['shndx']];data=process.payload(sec)[timer['value']:timer['value']+120];assert timer['type']==1 and timer['size']==120 and sec['flags']&2 and not sec['flags']&5;x['new_timer120'].update(expected_bytes_hex=data.hex(),expected_words=list(struct.unpack('<15Q',data)))
x['warning_policy'].update(baseline_Rust_count=142,baseline_Rust_stderr=ref(B/'OUTPUT/work/evidence/00.stderr'),baseline_process_C_stderr=ref(B/'OUTPUT/work/evidence/01.stderr'),baseline_kernel_C_stderr=ref(B/'OUTPUT/work/evidence/02.stderr'),baseline_arch_C_stderr=ref(B/'OUTPUT/work/evidence/03.stderr'),baseline_ld_stderr=ref(B/'OUTPUT/work/evidence/04.stderr'),new_ld_warning_must_equal=(B/'OUTPUT/work/evidence/04.stderr').read_text(),new_warning_disposition='Current142 including exact fixture-import and typed-pointer debt retained. Compare exact new headers; new unknowns block and declarations need exact ABI disposition. No suppression/recompile.')
(D/'check_thirteen_storage.py').write_bytes((Q/'check_thirteen_storage.py').read_bytes());x['HOST13_storage_reader']=ref(D/'check_thirteen_storage.py');save('ACCEPTANCE-INPUTS.SOURCE-ONLY.json',x)
T=D/'validator-templates';T.mkdir(mode=0o700,exist_ok=True);manifest=read(PREV/'VALIDATOR-TEMPLATE-SOURCES.json');changed={}
for p in TEMPLATES.glob('*.py'):
 s=p.read_text().replace(str(Q/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),str(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'))
 if p.name=='qualify_next_providers.py':
  s=s.replace('actual_thirty_five_Rust_exports','actual_thirty_nine_Rust_exports').replace('35_RUST_EXPORTS','39_RUST_EXPORTS');s=once(s,"assert P['unchanged_completed_process_prefix']['Root_decision']=='RECOMPILE_CHANGED_PROCESS_SOURCE_ACTUAL_HOST13_QUALIFIED'","assert P['unchanged_completed_process_prefix']['Root_decision']==EXPECTED['process_compile_disposition']")
  marker=" # Current producer selected only the frozen cfgs, preserving genuine undefined NOCACHE."
  timer_gate=''' # One actual-qualified timer120 owner, distinct from function export counts.
 witness=EXPECTED['new_timer120'];name=witness['only_new_data_owner'];owned=definitions(rust,name);assert len(owned)==1;(a,)=owned;sec=rust.sections[a['shndx']]
 assert (a['bind'],a['type'],a['size'])==(1,1,120) and sec['align']>=8 and a['value']%8==0 and sec['flags']&2 and not sec['flags']&5
 assert object_bytes(rust,a).hex()==witness['expected_bytes_hex']
 assert not [(key,s) for key,elf in C.items() for s in definitions(elf,name)]
 b=final(name);assert (b['bind'],b['type'],b['size'])==(1,1,120) and b['value']%8==0 and sections[b['shndx']]['flags']&2 and not sections[b['shndx']]['flags']&5 and data(b).hex()==witness['expected_bytes_hex']
 table_rels=ns['ns']['_reuse_elf_owning_relocations'](rust,a);assert not table_rels, 'timer offset words cannot contain hidden pointer relocations'
 set_timer=definitions(rust,'set_timer');assert len(set_timer)==1 and set_timer[0]['type']==2
 consumer_rels=[r for r in ns['ns']['_reuse_elf_owning_relocations'](rust,set_timer[0]) if r['target']['name']==name]
 report['phases']['timer120']=dict(Rust_symbol=a,final_symbol=b,exact15_current_words=witness['expected_words'],unique_Rust_provider=True,set_timer_symbol=set_timer[0],set_timer_table_relocations=consumer_rels,real_consumer_binding='DIRECT_RELOCATION' if consumer_rels else 'OPEN_EXACT_FOLDED_TABLE_ARGUMENT_REVIEW',actual_HOST=witness['actual_HOST'])
'''
  s=once(s,marker,timer_gate+marker)
 if p.name=='qualify_retained_f02_owners.py':
  s=once(s,'assert len(oldmeta)==88 and len(newmeta)==71','assert len(oldmeta)==88 and len(newmeta)==70');s=once(s,'set(FOUR+THIRTEEN) and not set(newmeta)-set(oldmeta)',"set(FOUR+THIRTEEN+['process_timer_runtime_offsets']) and not set(newmeta)-set(oldmeta)");s=s.replace('new_allocated_OBJECTs=71,only_removed_objects=FOUR+THIRTEEN,all_71_binding_type_size_initial_bytes_and_relocations_preserved=True',"new_allocated_OBJECTs=70,only_removed_objects=FOUR+THIRTEEN+['process_timer_runtime_offsets'],all_70_binding_type_size_initial_bytes_and_relocations_preserved=True").replace('other_readonly_objects=25','other_readonly_objects=24').replace('71_PROCESS_METADATA','70_PROCESS_METADATA')
 if p.name=='qualify_host13_storage.py':s=s.replace('STATIC=Path('+repr(str(Q))+')','STATIC=Path('+repr(str(D))+')')
 ast.parse(s);(T/p.name).write_text(s)
 if p.name in manifest['templates']:manifest['templates'][p.name]['template_sha256']=hashlib.sha256(s.encode()).hexdigest();changed[p.name]=dict(parent=ref(p),prepared=ref(T/p.name))
# Helpers are never copied to an output tree; the driver authenticates/imports
# the exact already accepted helper paths from unchanged_helpers.
manifest['prepared_current_cohort']=changed;save('VALIDATOR-TEMPLATE-SOURCES.json',manifest)
s=(PREV/'qualify_produced_cohort.py').read_text();s=s.replace(str(TEMPLATES),str(T));s=s.replace('actual_thirty_five_Rust_exports','actual_thirty_nine_Rust_exports')
s=once(s,"parser.add_argument('--admission',required=True);args=parser.parse_args()","parser.add_argument('--admission');parser.add_argument('--preflight-only',action='store_true');args=parser.parse_args()")
needle=" root=Path(args.admission);assert root.is_absolute()"
prefix=''' if args.preflight_only:
  manifest=json.loads((D/'VALIDATOR-TEMPLATE-SOURCES.json').read_text());helpers=bind_validator_dependencies(manifest)
  runpy.run_path(str(D/'literal_import_probe.py'),run_name='__main__')
  for name,row in manifest['templates'].items():
   file=D/'validator-templates'/name;assert hashlib.sha256(file.read_bytes()).hexdigest()==row['template_sha256'];compile(file.read_text(),str(file),'exec')
  if args.admission:
   root=Path(args.admission);assert root.is_absolute() and root.parent==E and root.resolve(strict=True)==root
   adopted=json.loads((root/'PROFILE.SOURCE-ONLY.json').read_text());frozen=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text());assert adopted['exact_commands']==frozen['exact_commands']
   for key in ['objects','configuration','postimages','source_directory_exports']:assert adopted['inputs'][key]==frozen['inputs'][key]
  print(json.dumps(dict(status='PASS_LITERAL_CLI_PINNED_DEPENDENCIES_AND_FROZEN_GATE_IMPORTS',adopted_profile_checked=bool(args.admission),artifact_gates_executed=False,authority=None)));return 0
 assert args.admission, 'actual qualification requires exact adopted admission'
'''
assert needle in s;s=s.replace(needle,prefix+needle,1);ast.parse(s);(D/'qualify_produced_cohort.py').write_text(s)
(D/'literal_import_probe.py').write_text("import profile_clone_witness\nassert callable(profile_clone_witness.validate)\n")
(D/'check_postbuild_current.py').write_bytes((Q/'check_postbuild_current.py').read_bytes())
save('REQUEST-PAYLOAD.DRAFT.NOT-AUTHORITY.json',dict(scope=__doc__.splitlines()[0],status='STATIC_SIX_FUNCTION_TIMER120_REQUEST_NOT_AUTHORITY',runtime_authority=None,request_sha256=None,actual_nonce=None,actual_Root_admission=None,actual_current_physical_clearance=None,actual_resource_authority=None,actual_execution_release=None,source_plan=ref(D/'COHERENT-NEXT-DEFAULT-SOURCE-PLAN.NOT-GRANTED.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),reuse=ref(D/'FROZEN-FIVE-COMMAND-SEVEN-INPUT-REUSE.json'),source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.FIVE.json'),acceptance=ref(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),validator=ref(D/'qualify_produced_cohort.py'),validator_manifest=ref(D/'VALIDATOR-TEMPLATE-SOURCES.json'),postjoin_reader=ref(D/'check_postbuild_current.py')))
print(json.dumps(dict(status=x['status'],function_exports=39,Cfunctions=[72,28],process_metadata=70,timer_data=1,expected_U_removed=4,expected_U_added=0,actual_compiler=0)))
