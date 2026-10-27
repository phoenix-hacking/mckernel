"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run already-prepared read-only gates once after Root's new four-command producer.
No compiler, guest, source mutation, grant, resource release or automatic retry.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,runpy,struct,sys,traceback
D=Path(__file__).resolve().parent;E=D.parent

def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(p,value):
 with p.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--admission',required=True);args=parser.parse_args()
 root=Path(args.admission);assert root.is_absolute() and root.parent==E and str(root.resolve(strict=True))==args.admission and re.fullmatch(r'ROOT-[A-Za-z0-9-]+',root.name)
 inputs=json.loads((D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text());out=D/'actual-qualification-1';assert not out.exists();out.mkdir(mode=0o700)
 report=dict(scope=__doc__.splitlines()[0],status='IN_PROGRESS',static_acceptance_inputs=ref(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json'),actual_admission=str(root),completed=[],native_acceptance=False,whole_file_retirement=False,physical_postjoin='SEPARATE_ROOT_READER',compiler_container_Git_grant_actions=0)
 try:
  producer_path=root/'OUTPUT/work/evidence/producer-contract.json';producer=json.loads(producer_path.read_text());profile=json.loads((root/'PROFILE.SOURCE-ONLY.json').read_text());frozen=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text())
  assert producer['status']=='ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER' and len(producer['commands'])==4 and all(r['returncode']==0 for r in producer['commands'])
  assert producer['source_profile']==ref(root/'PROFILE.SOURCE-ONLY.json') and profile['exact_commands']==frozen['exact_commands']
  for key in ['objects','configuration','postimages','source_directory_exports']:assert profile['inputs'][key]==frozen['inputs'][key],('actual source/retained prefix differs',key)
  templates=json.loads((D/'VALIDATOR-TEMPLATE-SOURCES.json').read_text())['templates']
  for name,row in templates.items():
   file=D/'validator-templates'/name;raw=file.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['template_sha256'],('frozen checker changed',name)
   text=raw.decode().replace('__ACTUAL_ADMISSION_BASENAME__',root.name);(out/name).write_text(text)
  write(out/'ACTUAL-VALIDATOR-CONTEXT.json',dict(runtime_authority=None,admission=str(root),producer=ref(producer_path),profile=ref(root/'PROFILE.SOURCE-ONLY.json'),static_inputs=ref(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json')))
  sys.path.insert(0,str(out))
  for filename in ['qualify_clone_pointer_and_warning_suffix.py','qualify_actual_f02_profile.py','qualify_actual_image_suffix.py','qualify_next_providers.py','qualify_retained_f02_owners.py']:
   runpy.run_path(str(out/filename),run_name='__main__');report['completed'].append(filename)
  # Reuse the unchanged exact two-pair alias predicate on newly produced bytes.
  source=(out/'qualify_clone_pointer_and_warning_suffix.py').read_text();ns={'__file__':str(out/'qualify_next_providers.py')};exec(compile(source[:source.index("\nclone=ns['_reuse_elf_function']")],'accepted current-cohort strict ELF readers','exec'),ns)
  spec=importlib.util.spec_from_file_location('actual_cohort_narrow_alias',out/'narrow_f02_alias_identity.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
  rust=ns['rust'];final=ns['final'];data=ns['data'];rels=ns['ns']['_reuse_elf_owning_relocations'];object_bytes=ns['ns']['_reuse_elf_object_bytes']
  def own(name):
   values=[s for s in rust.symbols if s['name']==name and s['shndx']!=0];assert len(values)==1;v=dict(values[0]);v['other']=rust.raw[rust.table['offset']+v['index']*24+5];return v
  pointers=struct.unpack('<10Q',data(final('process_idle_callbacks')));rows=[]
  for i,(original,rel) in enumerate(zip(gate.TARGETS,rels(rust,own('process_idle_callbacks')))):
   actual=rel['target']['name'];a=own(original);b=own(actual);fa=final(original);fb=final(actual)
   rows.append(dict(offset=rel['offset'],type=rel['type'],addend=rel['addend'],original_name=original,actual_name=actual,original_object_symbol=a,actual_object_symbol=b,original_final_symbol=fa,actual_final_symbol=fb,original_object_code_hex=object_bytes(rust,a).hex(),actual_object_code_hex=object_bytes(rust,b).hex(),original_final_code_hex=data(fa).hex(),actual_final_code_hex=data(fb).hex(),final_table_pointer=pointers[i]))
  alias=gate.validate(rows);write(out/'CURRENT-NARROW-ALIAS-IDENTITY-GATE.json',dict(scope=report['scope'],status=alias['status'],decision=alias,predicate=ref(out/'narrow_f02_alias_identity.py'),general_alias_waiver=False,native_acceptance=False))
  files=['RESULT.json','IMAGE-LINK-RESULT.json','NEXT-PROVIDERS-RESULT.json','RETAINED-F02-DATA-OWNERS-RESULT.json','CURRENT-NARROW-ALIAS-IDENTITY-GATE.json']
  for name in files:assert json.loads((out/name).read_text())['status'].startswith('PASS'),name
  providers=json.loads((out/'NEXT-PROVIDERS-RESULT.json').read_text());warnings=json.loads((out/'CLONE-FINAL-POINTER-AND-WARNINGS.json').read_text())
  report.update(status='PASS_ACTUAL_SYNC_PROCESSVM_PRODUCER_ELF_PROVIDER_LINK_AND_RETAINED_DATA_GATES',producer=ref(producer_path),actual_profile=ref(root/'PROFILE.SOURCE-ONLY.json'),compiled_outputs=[r['output'] for r in producer['commands']],actual_C_function_delta=providers['phases']['actual_selected_C_provider_delta'],actual_Rust_exports=len(providers['phases']['actual_thirty_five_Rust_exports']),exact_expected_undefined=inputs['exact_undefined_delta'],warnings=warnings['Rust_warning_comparison'],evidence=[ref(out/name) for name in files],Source38_different_source_debt_closed=False)
  if report['warnings']['new_warning_disposition_required']:report['status']='PASS_REQUIRED_ARTIFACT_GATES_PENDING_EXACT_NEW_DECLARATION_WARNING_DISPOSITION'
 except BaseException as error:
  report.update(status='FAIL_FIRST_SYNC_PROCESSVM_ACTUAL_QUALIFICATION_PRESERVED',first_failure=repr(error),traceback=traceback.format_exc())
 write(out/'FINAL-ARTIFACT-QUALIFICATION.json',report);print(json.dumps(dict(status=report['status'],result=ref(out/'FINAL-ARTIFACT-QUALIFICATION.json'),first_failure=report.get('first_failure'))))
 if report['status'].startswith('FAIL'):return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
