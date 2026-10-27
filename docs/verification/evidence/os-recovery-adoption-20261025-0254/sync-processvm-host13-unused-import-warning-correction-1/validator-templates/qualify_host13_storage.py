"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact13 immutable owners and real-consumer relocation or explicit folded-code gap.
"""
from pathlib import Path
import hashlib,importlib.util,json,struct
D=Path(__file__).resolve().parent
STATIC=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/qualified-sync-processvm-host13-five-stage-source-1')
EXPECTED=json.loads((STATIC/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text())
s=(D/'qualify_clone_pointer_and_warning_suffix.py').read_text();ctx={'__file__':str(D/'qualify_host13_storage.py')};exec(compile(s[:s.index("\nclone=ns['_reuse_elf_function']")],'accepted strict actual readers','exec'),ctx)
P=ctx['P'];B=ctx['B'];rust=ctx['rust'];process=ctx['process'];ref=ctx['ref'];final=ctx['final'];data=ctx['data'];rels=ctx['ns']['_reuse_elf_owning_relocations'];object_bytes=ctx['ns']['_reuse_elf_object_bytes'];Elf=ctx['Elf']
assert ref(Path(EXPECTED['process_baseline_object']['path']))==EXPECTED['process_baseline_object']
source=STATIC/'check_thirteen_storage.py';assert ref(source)==EXPECTED['HOST13_storage_reader']
spec=importlib.util.spec_from_file_location('unchanged_owner_HOST13_storage_reader',source);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
old=owner.Elf(EXPECTED['process_baseline_object']['path']);changed=owner.Elf(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o');new=owner.Elf(B/'kernel/rust/mckernel_rust.o');image=owner.Elf(B/'kernel/mckernel.img')
C=[(r['link_token'],Elf(B/r['build_relative'] if r['replace'] else Path(r['source']['path']))) for r in P['inputs']['objects'] if r['link_token']!='rust/mckernel_rust.o']
rows=[];opened=[]
for record in EXPECTED['HOST13_records']:
 name,value=record['name'],record['value'];prior=old.readonly_int(name,value);assert not changed.definitions(name);a=new.readonly_int(name,value);b=image.readonly_int(name,value)
 assert not [(key,s) for key,elf in C for s in elf.symbols if s['name']==name and s['shndx']!=0]
 # A relocation must be owned by the named real current Rust consumer, not an
 # arbitrary allocated section. Constant folding is never silently accepted.
 consumer=EXPECTED['HOST13_production_consumer_map'][name];symbols=[s for s in rust.symbols if s['name']==consumer and s['shndx']!=0];assert len(symbols)==1 and symbols[0]['type']==2
 fn=symbols[0];f=final(consumer);owned=[r for r in rels(rust,fn) if r['target']['name']==name]
 if not owned:opened.append(dict(data=name,value=value,consumer=consumer,required='Independent exact current final argument-instruction proof of this value at its original controlled provider call; source/HOST parity alone is insufficient',object_code_hex=object_bytes(rust,fn).hex(),final_code_hex=data(f).hex()))
 rows.append(dict(data=name,value=value,baseline=prior,Rust=a,final=b,source_consumer=record['Rust_consumer']['name'],production_consumer=consumer,consumer_object_symbol=fn,consumer_final_symbol=f,exact_consumer_owned_relocations=owned))
report=dict(scope=__doc__.splitlines()[0],status='OPEN_STORAGE13_FINAL_CONSUMER_BINDINGS' if opened else 'PASS_STORAGE13_REAL_CONSUMER_RELOCATIONS_PENDING_INDEPENDENT_FINAL_MAP_REVIEW',records=rows,open_consumer_instruction_proofs=opened,baseline=EXPECTED['process_baseline_object'],new_process=ref(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o'),Rust=ref(B/'kernel/rust/mckernel_rust.o'),image=ref(B/'kernel/mckernel.img'),HOST13_actual=EXPECTED['HOST13_actual'],all13_readonly_CInt4_align4_exact_values_and_unique_Rust_owners=True,final_consumer_bindings_complete=not opened,independent_final_map_review=False,default_retirement=False,native_acceptance=False,Source38_GNU_RETAIN_hold='OPEN_UNCHANGED')
(D/'HOST13-STORAGE-AND-CONSUMERS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],records=13,open_consumers=len(opened))))
