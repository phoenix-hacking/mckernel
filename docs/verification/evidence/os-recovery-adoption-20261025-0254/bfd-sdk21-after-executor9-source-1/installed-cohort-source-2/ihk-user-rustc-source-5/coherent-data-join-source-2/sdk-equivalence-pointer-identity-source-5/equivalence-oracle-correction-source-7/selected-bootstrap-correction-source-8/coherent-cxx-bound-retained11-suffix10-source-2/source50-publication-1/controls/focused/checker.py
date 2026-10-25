#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused real function bodies with explicit synthetic receipt/artifact-check mock;
compiler-free LANGUAGES NONE CMake bootstrap cases. Never an SDK/ABI result.
"""
from pathlib import Path
import argparse,ast,copy,hashlib,json,shutil,subprocess,tempfile
from types import SimpleNamespace
BASE=Path(__file__).resolve().parent
ROWS=[{'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/READY.COHERENT-BOOTSTRAP-ROLE-RETAINED11-SUFFIX10.SOURCE-ONLY.json', 'bytes': 15042, 'sha256': '4a792e0c505890372d65b91cca415970b3bbdede4fe60edc3367223c913052bd'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/bfd_retained11_suffix10_owner.py', 'bytes': 94477, 'sha256': '5c67cda6fe87fe371a660a9f13a4546c27b7106a5b74ccb3f2cd1b7bd3fd9f47'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/bfd_retained11_suffix10_driver.py', 'bytes': 4592, 'sha256': 'e5b6cf80b7b8ffaf30c3159f52e745e39f1317ad3689b79226ccf065e631f08a'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/BFD-PREPARATION.json', 'bytes': 16560, 'sha256': 'ca046f789f8bd87363494f159e51dd2a2b5446c5dedd53c113ccfacd4d9ed655'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/REQUEST.PENDING-NO-AUTHORITY.json', 'bytes': 5390, 'sha256': '8d643a6e11f19d7acb1770a307ad3a476dcdaf399aedcf9c6eb6ea2730d29b69'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/candidate/EXACT-RETAINED-SDK-PREFIX-8-OF-9.json', 'bytes': 16148, 'sha256': '3f8ea371280dd5e9f33ac042b15ee92f459bd63d2226c6ab0f67ef898127224d'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/candidate/EXACT-RETAINED-SEMANTIC-SDK-PREFIX-3.json', 'bytes': 8893, 'sha256': '9d7096d7a16f487030800e7c2286787eb8abe3d18bd7c7e0d2c8face742d18da'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/focused-consumer-controls-source-1/CMakeLists.PINNED-SDK-CLANG-CXX.txt', 'bytes': 1565, 'sha256': 'af282395510242ca69aeffaf7950b429ca4027b9d09e52b5feed5028bb4450d0'}, {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/focused-consumer-controls-source-1/EXACT-EXISTING-SDK-CXX-TOOL-BINDING.SOURCE-ONLY.json', 'bytes': 3537, 'sha256': '439e9ef27729f4ce85aeb6c5c0a376d614e7411b98df469b4021c13e92dcdf49'}]
OWNER=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/bfd_retained11_suffix10_owner.py')
PREP=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/BFD-PREPARATION.json')
REQUEST=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/REQUEST.PENDING-NO-AUTHORITY.json')
DRIVER=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-retained11-suffix10-source-1/bfd_retained11_suffix10_driver.py')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,why):
    if not ok:raise ValueError(why)
def js(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-once',required=True);args=parser.parse_args()
    assert sha(__file__)==args.check_once
    for row in ROWS:assert Path(row['path']).stat().st_size==row['bytes'] and sha(row['path'])==row['sha256']
    source=OWNER.read_text();tree=ast.parse(source);functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('mounts','validate_library_receipt')]
    assert len(functions)==2
    prep=json.loads(PREP.read_bytes());request=json.loads(REQUEST.read_bytes())
    constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('ROOT','BASIS','NIGHTLY_ROOT','DRIVER','PREPARATION','PREPARATION_SHA','COMMANDS_PATH'):
            constants[node.targets[0].id]=eval(compile(ast.Expression(node.value),'<constant>','eval'),dict(Path=Path,**constants))
    namespace=dict(Path=Path,json=json,need=need,LIBRARY_PREPARATION=prep,**constants)
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(OWNER),'exec'),namespace)
    records=[]
    def positive(name,fn):fn();records.append(dict(case=name,status='PASS'))
    def negative(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError) as error:records.append(dict(case=name,status='EXPECTED_REFUSAL',error=str(error)))
        else:raise AssertionError('unexpected acceptance '+name)
    def mount_check(rows):
        targets={dst:(src,ro) for src,dst,ro in rows}
        need(len([row for row in rows if row[1]=='/prefix'])==1 and targets['/prefix']==(prep['control_prefix']['path'],True),'original prefix RO')
        need(len([row for row in rows if row[1]=='/semantic-prefix'])==1 and targets['/semantic-prefix']==(prep['semantic_prefix']['path'],True),'semantic prefix RO')
        driver_tree=ast.parse(DRIVER.read_text());config=next(node.value for node in driver_tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PREPARATION' for t in node.targets))
        config=eval(compile(ast.Expression(config),'<driver-config>','eval'),{'Path':Path})
        need(targets[str(config)]==(str(config),True) and config==PREP,'driver CONFIG exact owner bind')
    mounts=namespace['mounts'](request)
    positive('actual-mounts-and-driver-CONFIG',lambda:mount_check(mounts))
    for label,changed in [('missing-semantic',[r for r in mounts if r[1]!='/semantic-prefix']),('semantic-RW',[(a,b,False if b=='/semantic-prefix' else c) for a,b,c in mounts]),('semantic-wrong-source',[(a+'/wrong' if b=='/semantic-prefix' else a,b,c) for a,b,c in mounts]),('missing-original',[r for r in mounts if r[1]!='/prefix']),('missing-CONFIG',[r for r in mounts if r[1]!=str(PREP)])]:negative(label,lambda rows=changed:mount_check(rows))
    reused=json.loads(Path(prep['retained_prefix_manifest']['path']).read_bytes());semantic=json.loads(Path(prep['retained_semantic_manifest']['path']).read_bytes())
    qtree=ast.parse((Path(prep['candidate_root'])/'orchestration/qualify.py').read_text());order=ast.literal_eval(next(n.value for n in qtree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LOGICAL_NAMES' for t in n.targets)))
    retained=[dict(row,execution_provenance='RETAINED_PREVIOUS_SDK_SUCCESS') for row in reused['retained_commands']]+[dict(row,execution_provenance='RETAINED_SEMANTIC_SDK_SUCCESS') for row in semantic['retained_commands']];retained.sort(key=lambda row:order.index(row['log']))
    actual=[dict(log=name,argv=['EXPLICIT-MODEL',name],cwd='/work/qualification-1',rc=0,execution_provenance='CURRENT_SDK_SUFFIX') for name in order if name not in {row['log'] for row in retained}];actual[0]['argv']=semantic['preserved_failure']['argv']
    logical=sorted(retained+actual,key=lambda row:order.index(row['log']))
    result=dict(retained_prefix_manifest_sha256=prep['retained_prefix_manifest']['sha256'],retained_prefix_count=11,retained_original_prefix_count=8,retained_semantic_prefix_count=3,actual_suffix_count=10,logical_contract_count=21)
    with tempfile.TemporaryDirectory(prefix='bfd-focused-controls-') as temporary:
        root=Path(temporary);out=root/'qualification-1';out.mkdir();local_request=dict(request,candidate_root=str(root))
        for name,pin in reused['retained_files'].items():shutil.copy2(Path(prep['control_prefix']['path'])/name,out/name)
        for name,pin in semantic['streams'].items():shutil.copy2(Path(prep['semantic_prefix']['path'])/name,out/name)
        js(out/'PREFIX-REUSE.json',reused);js(out/'SEMANTIC-PREFIX-REUSE.json',semantic)
        for stream in ('stdout','stderr'):(root/'evidence').mkdir(exist_ok=True);(root/'evidence'/stream).write_bytes(b'')
        def support_check(*args):
            # Explicit mocked artifact checker; verify actual owner invokes the
            # unchanged support boundary. No fake SDK artifact acceptance.
            need(args[0]==out and args[1]==out,'original artifact checker boundary')
            support.calls+=1
        support=SimpleNamespace(COMPILE_PROFILE={},_validate_driver_result=support_check,calls=0)
        namespace.update(host=SimpleNamespace(digest=sha),safe_path=lambda p,*args:Path(p),bfd_support=lambda:support)
        capture=dict(returncode=0,direct_child_joined=True,group_absent=True,closed_streams=True,error=None,retirement_error=None,timed_out=False,captures={key:dict(path='/work/evidence/'+key,size=0,sha256=sha(root/'evidence'/key)) for key in ('stdout','stderr')})
        receipt=dict(schema='mckernel.bfd-retained-prefix-sdk-suffix-receipt.v1',status='PASS_BFD_PREFIX_REUSED_SUFFIX_CAPTURE',scope=prep['scope'],preparation_sha256=constants['PREPARATION_SHA'],command=json.loads(constants['COMMANDS_PATH'].read_bytes())['command'],native_acceptance=False,M15_file_closure=False,capture=capture)
        def evaluate(ret=retained,act=actual,res=result):
            js(out/'retained-commands.json',ret);js(out/'actual-commands.json',act);js(out/'commands.json',sorted(ret+act,key=lambda row:order.index(row['log'])));js(out/'RESULT.json',res)
            namespace['validate_library_receipt'](dict(receipt,qualifier_result_sha256=sha(out/'RESULT.json')),local_request)
        positive('actual-receipt-8plus3plus10-boundary',evaluate);need(support.calls==1,'unchanged support checker invoked')
        negative('old8plus13-counts',lambda:evaluate(res=dict(result,retained_prefix_count=8,actual_suffix_count=13)))
        negative('missing-semantic-row',lambda:evaluate(ret=retained[:-1]))
        negative('extra-semantic-row',lambda:evaluate(ret=retained+[retained[-1]]))
        wrong=copy.deepcopy(retained);wrong[-1]['execution_provenance']='CURRENT_SDK_SUFFIX';negative('retained-provenance',lambda:evaluate(ret=wrong))
        wrong=copy.deepcopy(actual);wrong[0]['argv']=['wrong'];negative('configure-argv',lambda:evaluate(act=wrong))
        wrong=copy.deepcopy(actual);wrong[-1]['rc']=1;negative('actual-failure-preserved',lambda:evaluate(act=wrong))
        wrong=copy.deepcopy(retained);wrong[-1]['argv']=['wrong'];negative('semantic-argv',lambda:evaluate(ret=wrong))
        stream=out/'equivalence-run.stdout';saved=stream.read_bytes();stream.write_bytes(b'changed');negative('retained-stream-hash',evaluate);stream.write_bytes(saved)
        positive('restored-receipt',evaluate)
        bootstrap=(BASE/'CMakeLists.PINNED-SDK-CLANG-CXX.txt').read_text()
        need('project(m15_bfd_selected_tools C CXX ASM)' in bootstrap,'real CXX language selected')
        prefix=bootstrap[:bootstrap.index('project(')]
        selected=bootstrap[bootstrap.index('set(ENABLE_RUST_USER_TOOLS'):bootstrap.index('set(ENABLE_QLMPI')]
        # GNUInstallDirs body and option() are real; LANGUAGES NONE deliberately
        # suppresses compiler discovery. CMAKE_SIZEOF_VOID_P fixture avoids its
        # unknown-architecture warning; this is not a native ABI observation.
        probe='cmake_minimum_required(VERSION 3.11)\n'+prefix+'\nproject(bfd_bootstrap_model LANGUAGES NONE)\nset(CMAKE_SIZEOF_VOID_P 8)\ninclude(GNUInstallDirs)\n'+selected+'\noption(ENABLE_RUST_USER_TOOLS "actual consumer option" ON)\nif(NOT ENABLE_RUST_USER_TOOLS)\n message(FATAL_ERROR "selected Rust lost")\nendif()\nforeach(key BINDIR LIBDIR INCLUDEDIR MANDIR)\n if(NOT CMAKE_INSTALL_${key})\n message(FATAL_ERROR "missing install ${key}")\n endif()\nendforeach()\nget_property(kind CACHE CMAKE_CXX_COMPILER PROPERTY TYPE)\nif(NOT kind STREQUAL "FILEPATH")\n message(FATAL_ERROR "CXX FILEPATH type")\nendif()\n'
        project=root/'cmake-project';project.mkdir();(project/'CMakeLists.txt').write_text(probe)
        cases=[('bootstrap-good',[],0),('bootstrap-RustOFF',['-DENABLE_RUST_USER_TOOLS:BOOL=OFF'],1),('bootstrap-wrong-CXX',['-DCMAKE_CXX_COMPILER:FILEPATH=/usr/bin/g++'],1),('bootstrap-relative-CXX',['-DCMAKE_CXX_COMPILER:FILEPATH=clang'],1),('bootstrap-wrong-CXX-mode',['-DCMAKE_CXX_COMPILER_ARG1:STRING=--driver-mode=gcc'],1)]
        for index,(name,flags,expected) in enumerate(cases):
            command=['/usr/bin/cmake','-S',str(project),'-B',str(root/('cmake-'+str(index))),*flags]
            process=subprocess.run(command,capture_output=True,timeout=10)
            (BASE/('actual-'+name+'.stdout')).write_bytes(process.stdout);(BASE/('actual-'+name+'.stderr')).write_bytes(process.stderr)
            need(process.returncode==(0 if expected==0 else 1),'bootstrap unexpected result '+name)
            if expected:
                diagnostic=b'requires ENABLE_RUST_USER_TOOLS=ON' if name=='bootstrap-RustOFF' else b'pinned SDK clang CXX driver'
                need(diagnostic in process.stderr,'bootstrap exact expected failure '+name)
            records.append(dict(case=name,status='PASS' if expected==0 else 'EXPECTED_REFUSAL',argv=command,rc=process.returncode))
    print(json.dumps(dict(status='PASS_FOCUSED_ACTUAL_FUNCTION_MODEL_AND_COMPILER_FREE_BOOTSTRAP_ONLY',records=records,SDK_native_or_ABI_acceptance=False),indent=2))
if __name__=='__main__':main()
