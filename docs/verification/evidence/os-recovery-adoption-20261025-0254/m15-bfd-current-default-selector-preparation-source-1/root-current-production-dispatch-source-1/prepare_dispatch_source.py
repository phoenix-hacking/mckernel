"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow three-command BFD successor of reviewed A4 holder/container mechanics.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json,os,re,shutil
D=Path(__file__).resolve().parent;B=D.parent;E=B.parent;R=Path('/home/holden/mckernel');F=B/'final-execution-preparation-source-1';A=E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-4'
S=E/'bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-cxx-bound-retained11-suffix10-source-2'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def put(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
assert ref(F/'READY.json')['sha256'].startswith('f5d43acb')
oldprofile=read(F/'BOUND-TWO-TARGET-PROFILE.NOT-GRANTED.json');sourcebank=read(S/'BFD-INPUTS.json');write_set=read(B/'ROOT-SELECTIVE-WRITE-SET.NOT-AUTHORITY.json')['changes'];replacements={x['relative']:x['postimage'] for x in write_set}
# Exact bounded roots from the accepted BFD source role, with current contents.
# No repository-wide enumeration; add literal current-CMake dependencies only.
paths=set(sourcebank['source']);cm=(R/'executer/user/CMakeLists.txt').read_text()
for match in re.findall(r'\$\{CMAKE_CURRENT_SOURCE_DIR\}/([^"\n]+)',cm):
 if '$' not in match and (R/'executer/user'/match).is_file():paths.add('executer/user/'+match)
paths.update(replacements)
planned_parents=set()
for relative in list(paths):
 for parent in Path(relative).parents:
  if str(parent)!='.':planned_parents.add(str(parent))
paths.update(planned_parents)
rows=[]
for relative in sorted(paths):
 p=R/relative
 if relative in replacements:rows.append(dict(relative=relative,type='file',source=replacements[relative],mode=0o644));continue
 if p.is_symlink():rows.append(dict(relative=relative,type='symlink',link_target=os.readlink(p)));continue
 if p.is_dir() or (relative in planned_parents and not p.exists()):rows.append(dict(relative=relative,type='directory',mode=0o755));continue
 assert p.is_file(),('missing required accepted source role path',relative)
 rows.append(dict(relative=relative,type='file',source=ref(p),mode=0o644 if not os.stat(p).st_mode&0o111 else 0o755))
plan=dict(scope=__doc__.splitlines()[0],schema='m15.bfd.current-bounded-source-export-plan.v1',status='SOURCE_ONLY_EXACT_CURRENT_CONTENTS_PLUS_FOUR_SELECTIVE_POSTIMAGES',runtime_authority=None,source_roots=sourcebank['source_roots'],accepted_source_role=ref(S/'BFD-INPUTS.json'),current_user_CMake_preimage=ref(R/'executer/user/CMakeLists.txt'),selective_write_set=ref(B/'ROOT-SELECTIVE-WRITE-SET.NOT-AUTHORITY.json'),export_root=str(D/'source-export-1'),records=rows,source_adoption_required_before_materialization=True)
put('CURRENT-SOURCE-EXPORT-PLAN.NOT-AUTHORITY.json',plan)
# Container assets are a finite readonly directory, no old whole qualifier main.
assets=D/'assets';(assets/'tool-project').mkdir(parents=True,exist_ok=True)
for src,dest in [(B/'tool-project/CMakeLists.txt',assets/'tool-project/CMakeLists.txt'),(B/'inspect_project_objects.py',assets/'inspect_project_objects.py'),(B/'retained_elf.py',assets/'retained_elf.py')]:shutil.copyfile(src,dest)
put('ASSET-CLOSED-MAP.json',dict(scope=__doc__.splitlines()[0],root=str(assets),readonly=True,files=[dict(relative=str(p.relative_to(assets)),reference=ref(p)) for p in sorted(assets.rglob('*')) if p.is_file()]))
root53=E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER53.json';l53=read(root53);assert len(l53['consumed_nonces'])==64 and l53['latest_accepted_free_boundary']['sha256'].startswith('270a')
# Reuse exact A4 resource/control functions, with only source/mount/three-command
# producer predicates replaced. No historical four-command verifier is called.
run=(A/'run_build_only.py').read_text();originalrun=run
start=run.index('def mounts(');end=run.index('\ndef docker_prefix(',start)
run=run[:start]+'''def mounts(profile,export,output):
    require(export['source_export_plan']==profile['inputs']['source_export_plan'],'exact source-export plan')
    require(export['readable_source_export']==profile['inputs']['source_export_root'],'exact private closed export path')
    verify_bfd_source_export(profile)
    rows=[dict(host=export['readable_source_export'],target='/src',readonly=True),dict(host=profile['inputs']['assets_root'],target='/candidate',readonly=True)]
    rows += [dict(host=r['host_path'],target=r['container_path'],readonly=True) for r in profile['inputs']['toolchain_mounts']]
    rows += [dict(host=str(D/'build_only_worker.py'),target='/build-only-worker.py',readonly=True),dict(host=str(output/'plan.json'),target='/build-only-plan.json',readonly=True)]
    return rows

'''+run[end:]
run=run.replace("'--workdir','/work/output/build/kernel'","'--workdir','/work'")
start=run.index('def source_directory_postimages(');end=run.index('\ndef current_operation_guard(',start)
run=run[:start]+'''def verify_bfd_source_export(profile):
    plan=read(auth(profile['inputs']['source_export_plan']));root=strict_parent(profile['inputs']['source_export_root'])
    require(root.is_dir() and str(root)==plan['export_root'],'actual source export exists at exact bound path')
    for row in plan['records']:
        relative=Path(row['relative']);require(not relative.is_absolute() and '..' not in relative.parts,'normalized exact selected source path')
        p=root/relative
        if row['type']=='directory':require(p.is_dir() and not p.is_symlink(),'ordinary selected source directory')
        elif row['type']=='symlink':require(p.is_symlink() and os.readlink(p)==row['link_target'],'exact selected source symlink')
        else:
            require(p.is_file() and not p.is_symlink(),'ordinary selected source file')
            actual=reference(p);require(actual['bytes']==row['source']['bytes'] and actual['sha256']==row['source']['sha256'],'exact selected current source bytes')
    # Materializer created only this finite map; a closed exported snapshot is mandatory.
    expected={r['relative'] for r in plan['records']}
    actual={str(p.relative_to(root)) for p in root.rglob('*')}
    require(actual==expected,'exact closed selected source export, no extras')
    asset=read(auth(profile['inputs']['asset_map']));assets=Path(profile['inputs']['assets_root'])
    require({str(p.relative_to(assets)) for p in assets.rglob('*') if p.is_file()}=={r['relative'] for r in asset['files']},'exact three readonly assets')
    for row in asset['files']:auth(row['reference'])
    return plan

def commands_for_plan(profile):
    require(profile['request_sha256']==reference(D/'REQUEST.SOURCE-ONLY.json')['sha256'],'exact finite BFD request')
    request=read(D/'REQUEST.SOURCE-ONLY.json');require(request['runtime_authority'] is None,'request supplies no runtime authority')
    require(profile['exact_commands']==request['commands'],'exact three current BFD commands')
    commands=profile['exact_commands'];require(len(commands)==3,'exact configure/build/readback commands only')
    require([c['new_output'] for c in commands]==['/work/current-bfd-build/CMakeCache.txt','/work/current-bfd-build/executer/user/mcinspect','/work/BFD-CURRENT-PROJECT-OBJECTS.json'],'exact fresh current BFD products')
    require(all(c['cwd']=='/work' for c in commands),'literal three-command CWD')
    require(commands[1]['argv']==['/usr/bin/cmake','--build','/work/current-bfd-build','--target','mcinspect','eclair','--parallel','1'],'only two genuine targets/jobs1')
    require(profile['inputs']['image']=='sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5','same accepted SDK image')
    return commands

'''+run[end:]
run=run.replace("require(len(export['container_tool_files'])>=4", "require(export['container_tool_files']==profile['inputs']['container_tool_files'] and export['container_sha256_pins']==profile['inputs']['container_sha256_pins'],'exact accepted tool/library/header pins')\n    require(len(export['container_tool_files'])>=4")
run=run.replace("require(read(profile['reuse_descriptor']).get('runtime_authority') is None,'readonly descriptor supplies no runtime authority')\n    require(export['SDK21_recompiled'] is False and export['source6153_entries']==6153,'preserve exact source and SDK reuse scope')", "require(export['SDK21_recompiled'] is False,'no SDK21/eight-pair replay')\n    require(export['source_adoption']==profile['actual_source_adoption'],'same actual Root selective adoption')\n    adoption=read(auth(profile['actual_source_adoption']));require(adoption['author']=='/root' and adoption['adopted'] is True and adoption['source_export_plan']==profile['inputs']['source_export_plan'],'genuine Root exact four-path adoption')")
start=run.index("    originals=[profile['inputs']['source6153']");end=run.index('    for original in originals:',start)
run=run[:start]+"    originals=[profile['inputs']['source_export_root'],profile['inputs']['assets_root']]+[x['host_path'] for x in profile['inputs']['toolchain_mounts']]\n"+run[end:]
start=run.index('    # Check only qualified file identities');end=run.index('    rows=mounts(profile,export,output)',start)
run=run[:start]+'''    verify_bfd_source_export(profile)
    require(export['qualified_readonly_files']==profile['inputs']['qualified_readonly_files'],'exact source/toolchain/helper closure')
    for row in profile['inputs']['qualified_readonly_files']:auth(row)
    require(os.access(export['readable_source_export'],os.R_OK|os.X_OK),'UID1000 readable/traversable closed source')
    output.mkdir(mode=0o700);(output/'work').mkdir(mode=0o700);(output/'work/evidence').mkdir(mode=0o700)
    (output/'plan.json').write_text(json.dumps(dict(runtime_authority=None,deadline_epoch=DEADLINE,commands=commands,tool_files=export['container_tool_files'],tool_sha256_pins=export['container_sha256_pins'],producer_contract=profile['producer_contract'],source_profile=reference(D/'PROFILE.SOURCE-ONLY.json')),indent=2)+'\\n')
'''+run[end:]
run=run.replace("name='current115-build-only-'","name='bfd-current-two-target-'")
ast.parse(run);(D/'run_build_only.py').write_text(run)
# Holder control-flow and all quarantine/release rules copied byte-for-byte.
shutil.copyfile(A/'hold_and_run_build_only.py',D/'hold_and_run_build_only.py')
worker=(A/'build_only_worker.py').read_text();oldworker=worker
worker=worker.replace("len(plan['commands'])==4,'exact four selected build commands'","len(plan['commands'])==3,'exact three current BFD producer commands'")
worker=worker.replace('    records=[]','''    for row in plan['tool_sha256_pins']:
        require(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],'qualified SDK CXX/BFD header/library bytes')
    records=[]''',1)
worker=worker.replace("'ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER'","'ACTUAL_CURRENT_BFD_THREE_COMMAND_PRODUCER'").replace('configuration_reuse_not_fresh_configure=True','fresh_genuine_two_target_configure=True').replace("'first failed compiler/link stops suffix'","'first failed configure/build/readback stops suffix'")
worker=worker.replace("row['output']=reference(target)","row['output']=reference(target)\n            if index==1:\n                other=Path('/work/current-bfd-build/executer/user/eclair');require(other.is_file() and not other.is_symlink() and other.stat().st_size>0,'both selected tools produced');row['second_output']=reference(other)")
ast.parse(worker);(D/'build_only_worker.py').write_text(worker)
(D/'run_build_only.A4-to-BFD.diff').write_text(''.join(difflib.unified_diff(originalrun.splitlines(True),run.splitlines(True),fromfile=str(A/'run_build_only.py'),tofile=str(D/'run_build_only.py'))));(D/'build_only_worker.A4-to-BFD.diff').write_text(''.join(difflib.unified_diff(oldworker.splitlines(True),worker.splitlines(True),fromfile=str(A/'build_only_worker.py'),tofile=str(D/'build_only_worker.py'))))
exportA=read(A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json');toolmanifest=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/image-toolchain.json');tools=read(toolmanifest)
sha_pins=[dict(path=tools['image_tools']['clang']['path'],sha256=tools['image_tools']['clang']['sha256']),dict(path='/usr/include/bfd.h',sha256='de900a9fe4ac94543ee1382cebc3063c3d7e20d16bc934fc816133dd55fe2432'),dict(path='/usr/lib64/libbfd.so',sha256='6cfd31804974c248c9512879e7b77a94862f92150c2171d901140464ea936ab3')]
commands=copy.deepcopy(oldprofile['commands']);outputs=['/work/current-bfd-build/CMakeCache.txt','/work/current-bfd-build/executer/user/mcinspect','/work/BFD-CURRENT-PROJECT-OBJECTS.json']
for c,out in zip(commands,outputs):c['new_output']=out
request=dict(scope=__doc__.splitlines()[0],status='SOURCE_ONLY_FINITE_CURRENT_BFD_REQUEST_NOT_AUTHORITY',runtime_authority=None,commands=commands,source_export_plan=ref(D/'CURRENT-SOURCE-EXPORT-PLAN.NOT-AUTHORITY.json'),asset_map=ref(D/'ASSET-CLOSED-MAP.json'),accepted_SDK21=ref(E/'ACTUAL-BFD-SDK21-INDEPENDENT-ARTIFACT-AND-BEHAVIOR-ACCEPTANCE.json'),SDK21_eightpairs_prefix_replays=0)
put('REQUEST.SOURCE-ONLY.json',request)
qualified=[ref(F/'READY.json'),ref(F/'independent-source-review-1/REVIEW.json'),ref(A/'run_build_only.py'),ref(A/'hold_and_run_build_only.py'),ref(A/'build_only_worker.py'),ref(toolmanifest),ref(D/'CURRENT-SOURCE-EXPORT-PLAN.NOT-AUTHORITY.json'),ref(D/'ASSET-CLOSED-MAP.json'),ref(D/'REQUEST.SOURCE-ONLY.json'),ref(B/'ROOT-SELECTIVE-WRITE-SET.NOT-AUTHORITY.json'),request['accepted_SDK21']]
profile=dict(scope=__doc__.splitlines()[0],status='SOURCE_ONLY_EXACT_THREE_COMMAND_BFD_DISPATCH_ROOT_AUTHORITY_NULL',runtime_authority=None,request_sha256=ref(D/'REQUEST.SOURCE-ONLY.json')['sha256'],exact_commands=commands,inputs=dict(image=oldprofile['tool_image'],source_export_plan=request['source_export_plan'],source_export_root=plan['export_root'],assets_root=str(assets),asset_map=request['asset_map'],toolchain_mounts=[dict(host_path=x['host'],container_path=x['container']) for x in oldprofile['mounts'] if x['container'] in ['/out','/nightly']],container_tool_files=exportA['container_tool_files'],container_sha256_pins=sha_pins,qualified_readonly_files=qualified),producer_contract=dict(source='Current closed bounded BFD source roots plus exactly four selective postimages; current mcexec preserved',new_operation='Fresh genuine current configure; only mcinspect/eclair/jobs1; exact2/3 project Rust objects and four BFD bridge exports/259B layout',SDK21_replayed=False,eight_CLI_pairs_replayed=False,valid_native_diagnostic=False),docker_client_prefix=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock'],deadline_epoch=1793165769,fixed_three_clock_cutoffs=oldprofile['fixed_cutoffs'],CPU='2-5',memory_bytes=12884901888,pids=512,aggregate_memory_budget_bytes=23259332608,maximum_wall_seconds=19800,source_preparation_boundary=dict(ledger=ref(root53),consumed_count=64,current_free=l53['latest_accepted_free_boundary']),native_custody_clearance=None,actual_source_adoption=None,actual_nonce=None,actual_execution_review=None,actual_resource_authority=None,actual_output_root=None,full_growth_including_source_temp_capture_bytes=4294967296,output_budget_bytes=536870912,capture_budget_bytes=67108864)
put('PROFILE.SOURCE-ONLY.json',profile)
put('ROOT-ACTUAL-BINDINGS.TEMPLATE.NOT-AUTHORIZED.json',dict(scope=__doc__.splitlines()[0],author=None,source_adoption=None,source_export=None,current_clearance=None,current_ledger=None,current_free=None,nonce=None,fresh_handshake_root=str(D/'HOLDER'),fresh_output_root=str(D/'OUTPUT'),grant=None,resource_authority=None,independent_review=None,runtime_authority=None))
put('A4-REUSE-AND-EXACT-DELTA.json',dict(scope=__doc__.splitlines()[0],A4_runner=ref(A/'run_build_only.py'),A4_holder=ref(A/'hold_and_run_build_only.py'),A4_worker=ref(A/'build_only_worker.py'),holder_byteexact=ref(A/'hold_and_run_build_only.py')['sha256']==ref(D/'hold_and_run_build_only.py')['sha256'],unchanged_runner_functions=['resource_guards','docker_prefix','current_operation_guard','auth','strict_parent','reference'],changed_runner_functions=['mounts','commands_for_plan','verify_bfd_source_export(new source-specific closed-map predicate)','docker_argv(CWD only)','execute(producer-input/output setup only)'],same_control_guards=['independent exact execution PASS','fresh_root_grant','actual27:4holder_and_CPUreservation','CPU2-5/12GiB/512tasks/networknone','currentaccount/deadlineboot','oneheavy/aggregate/floors','positivecontainerterminal/quarantine','noautocleanup'],new_worker_exact3_not4=True,SDK_or_old21_replay=False,source_map_records=len(rows),source_regular_file_bytes=sum(x['source']['bytes'] for x in rows if x['type']=='file')))
print('PASS source-only fixed3producer A4 successor, closed bounded current export plan, exact readonly SDK mounts/toolpins; Rootauthorityslots NULL')
