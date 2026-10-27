"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One current-default executor preparation/mount/receipt specialization; no controller.
"""
import hashlib,json,os,re,stat
from pathlib import Path
import validate_mcexec_default_batch as v
import elf_install_contract as elf
HERE=Path(__file__).resolve().parent
PREPARATION=HERE/'PREPARATION.json'
PROFILE=dict(uid=1000,gid=1000,cpus='2-5',jobs=1,memory_bytes=12*2**30,memory_swap_bytes=12*2**30,pids=512,network='none')
COMMANDS_SHA256='e19ce35d21a08293896cf34ff365647b42c3918eb98afc2d3754322c981a2176'
LABELS=['current-configure','producer-context','current-link','current-ELF-imports','current-install','installed-ELF']

def need(ok,why):
    if not ok:raise ValueError(why)
def canonical(value):return v.canonical(value)
def file_ref(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def document(path):return json.loads(Path(path).read_bytes())
def prep():return document(PREPARATION)
def configuration_api(p,require_adopted=True):
    need(p['schema']=='mckernel.mcexec-current-default-build-only-preparation.v1' and p['scope']==v.SCOPE,'exact executor preparation/schema')
    need(p['profile']==PROFILE and p['inner_capture_limits']==dict(address_space_bytes=2*2**30,CPU_seconds=60,operation_wall_seconds=90,file_bytes=32*2**20,nofile=256,core=0,stack_bytes=2*2**20),'preserved SDK profile/limits')
    need(p['timeout']==19800 and p['output_budget_bytes']==512*2**20 and p['capture_budget_bytes']==64*2**20,'preserved owner workload bounds')
    need(p['image_id']=='sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5','pinned SDK image')
    need([row['label'] for row in p['commands']]==LABELS and all(isinstance(row['argv'],list) and row['argv'] and row['cwd'].startswith('/work') for row in p['commands']),'exact six executor phases/cwd')
    need(hashlib.sha256(canonical(p['commands'])).hexdigest()==COMMANDS_SHA256,'exact reviewed literal executor argv/cwd/purpose')
    args=p['commands'][0]['argv']
    need(args[0]=='/usr/bin/cmake' and args[args.index('-B')+1]==v.BUILD and args[args.index('-S')+1]=='/src'
         and '-DMCEXEC_USER_RUSTC:FILEPATH=/nightly/bin/rustc' in args and '-DMCEXEC_ALLOW_C_REFERENCE=OFF' in args
         and not any(x.startswith('-DRUSTC:') for x in args),'independent user compiler and preserved alias')
    need(p['runtime']['current_typed_admission_required'] is True,'typed current controls cannot be disabled')
    if require_adopted:
        r=p['runtime'];need(r['adopted'] is True and all(r.get(k) is not None for k in ('source_root','source_identity','materialization','retained_prefix_root','retained_prefix_identity','vendor_source','vendor_identity','preserved_compute_RUSTC')),'Root source/adoption bindings required')
        v.validate_preconfigure_compute(dict(RUSTC=r['preserved_compute_RUSTC']))
        need(r['expected_BUILDID']=='3114d9e','this no-replay batch requires exact F4D BUILDID; changed context requires a new exact compile release')
    return dict(schema=p['schema'],labels=LABELS,profile=PROFILE,execution_authority=False)

def validate_preparation(p,api):
    configuration_api(p)
    path=api['safe_path'];digest=api['host'].digest;node=api['node'];r=p['runtime']
    source=path(r['source_root']);prefix=path(r['retained_prefix_root']);vendor=path(r['vendor_source'])
    need(node(source)==r['source_identity'] and node(prefix)==r['retained_prefix_identity'] and node(vendor)==r['vendor_identity'],'actual source/prefix/vendor node identities')
    for row in p['closure']:
        f=path(row['path'],False);need(f.stat().st_size==row['bytes'] and digest(f)==row['sha256'],'exact executor input/support closure')
    materialization=v.bound(r['materialization'])
    need(materialization['status']=='PASS_FINITE_TARGET_SOURCE_MATERIALIZATION_ONLY' and materialization['source_root']==r['source_root'],'genuine current source materialization')
    old=document(HERE/'RETAINED-F4D-EXACT-PRODUCER-CONTEXT.json')
    expected=dict(old['runtime_sources'])
    expected.update({'executer/user/CMakeLists.txt':dict(bytes=27799,sha256='1208a097f57f5b9d3deee4d23fc55c7c598d8a88aab9002d4c65ae13a36cea57'),
      'ihk/linux/user/CMakeLists.txt':dict(bytes=13474,sha256='a21e1cfbb064a03458201bfbea520d2f04e87ea287f58451d65031e74d728369'),
      'ihk/linux/user/rust/ihkmond.rs':dict(bytes=23095,sha256='0c0b4b6d286e9f0fdbdacf1d32c3cd33ec96d4d2420550771a0dc732dd84d86e')})
    expected.update(p['build_producer_sources'])
    expected.update({'executer/user/rust/'+name:row for name,row in p['qualification_only_inputs'].items()})
    for relative,row in expected.items():
        f=path(str(source/relative),False);need(f.stat().st_size==row['bytes'] and digest(f)==row['sha256'],'exact selected source '+relative)
    for row in p['retained_prefix_files']:
        f=path(str(prefix/row['relative']),False);need(f.stat().st_size==row['bytes'] and digest(f)==row['sha256'],'exact retained F4D prefix input')
    return dict(selected_sources=len(expected),source_identity=r['source_identity'],prefix_identity=r['retained_prefix_identity'])

def mounts(p,request,api):
    r=p['runtime'];rows=[(str(api['BASIS']),'/out',True),(str(api['NIGHTLY_ROOT']),'/nightly',True),
      (request['candidate_root'],'/work',False),(r['source_root'],'/src',True),
      (r['retained_prefix_root'],'/retained-f4d',True),(str(HERE),str(HERE),True),
      (str(api['DRIVER']),'/driver.py',True),(request['request_path'],'/request.json',True),
      (r['vendor_source'],p['libdwarf_vendor']['container_root'],True)]
    rows += [(row['path'],'/proposal/qualified-inputs/'+name,True) for name,row in p['qualification_only_inputs'].items()]
    rows += [(row['path'],row['path'],True) for row in p['closure']]
    return list(dict.fromkeys(rows))

def imports(text):
    result=[];active=False
    for line in text.splitlines():
        if line.startswith('Symbol table '):active="'.dynsym'" in line
        fields=line.split()
        if active and len(fields)>=8 and fields[6]=='UND':result.append(fields[3:8])
    return result

def elf_proof(text,binary,link):
    qualified=document(HERE/'QUALIFIED-F4D-ELF-TUPLE.json')
    needed=re.findall(r'Shared library: \[([^]]+)\]',text)
    interp=re.findall(r'Requesting program interpreter: ([^]]+)\]',text)
    main=[line for line in text.splitlines() if re.search(r'\bFUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+main$',line)]
    header=(Path(v.BUILD)/'config.h').read_text();ids=re.findall(r'^#define BUILDID "([^"\n]+)"$',header,re.M);need(len(ids)==1,'actual BUILDID')
    old=document(HERE/'RETAINED-F4D-EXACT-PRODUCER-CONTEXT.json')
    need((ids[0].encode()+b'\0') in Path(binary).read_bytes(),'binary BUILDID bytes')
    return dict(current_generated_link_command=link,actual_link_command=link,linked_objects=[v.RUST_OBJECT,v.ASM_ARCHIVE],project_C_objects=[],Rust_main_unique=len(main)==1,
      ELF64_x86_64_PIE='DYN (Position-Independent Executable file)' in text and 'Advanced Micro Devices X86-64' in text,
      BUILDID_in_ELF=ids[0],generated_BUILDID=ids[0],DT_NEEDED=needed,qualified_DT_NEEDED=qualified['DT_NEEDED'],PT_INTERP=interp[0] if len(interp)==1 else None,qualified_PT_INTERP=qualified['PT_INTERP'],dynamic_imports=imports(text),qualified_dynamic_imports=qualified['dynamic_imports'])

def validate_receipt(receipt,request,p,root,api):
    need(receipt['schema']=='mckernel.mcexec-default-target-link-install.v1' and receipt['status']=='PASS_MCEXEC_DEFAULT_TARGET_LINK_INSTALL_ONLY','exact executor result/status')
    need(len(receipt['commands'])==len(p['commands']) and all(actual['label']==wanted['label'] and actual['command']==dict(argv=wanted['argv'],purpose=wanted['purpose']) for actual,wanted in zip(receipt['commands'],p['commands'])),'exact reviewed executor command receipts')
    def load(reference,doc=True):
        logical=Path(reference['path']);need(logical.is_absolute() and logical.parts[:2]==('/','work') and '..' not in logical.parts,'durable executor output namespace')
        actual=api['safe_path'](str(Path(root)/logical.relative_to('/work')),False)
        need(actual.stat().st_size==reference['bytes'] and api['host'].digest(actual)==reference['sha256'],'durable executor output bytes')
        raw=actual.read_bytes();return json.loads(raw) if doc else raw
    # Source-only retained context is an authenticated runtime source member, not a
    # current output. Preserve its original evidence location/scope separately.
    def evidence(reference,doc=True):
        if reference['path']==str(HERE/'RETAINED-F4D-EXACT-PRODUCER-CONTEXT.json'):return v.bound(reference,doc)
        return load(reference,doc)
    expected=dict(sha256=api['PREPARATION_SHA'],retained_context=file_ref(HERE/'RETAINED-F4D-EXACT-PRODUCER-CONTEXT.json'),stage=p['stage'])
    actual_request=dict(nonce=request['nonce'],reference=dict(path=request['request_path'],sha256=api['host'].digest(api['safe_path'](request['request_path'],False))))
    need(receipt['request']==actual_request['reference'],'actual owner request identity')
    result=v.validate_batch_receipt(receipt,actual_request,expected,evidence)
    before=load(receipt['current_build_ELF'],False);after=load(receipt['actual_installed_ELF'],False)
    wanted,_=elf.installed_bytes(before,'/usr/local');need(after==wanted,'only exact CMake RPATH install mutation allowed')
    return result
