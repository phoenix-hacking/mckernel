"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow58selected-source/Git-layout/preserved21metadata review. No6999/archive rehash.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,os,stat,posixpath
R=Path('/home/holden/mckernel');E=R/'docs/verification/evidence/os-recovery-adoption-20261025-0254';A=E/'ROOT-M15-INSTALLED-CONSUMER-SOURCE-ADOPTION-1';C=E/'m15-installed-consumer-restart-20261028-1';N=C/'next-consumer-ready-1';HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 b=Path(p).read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def exact(v):assert ref(v['path'])=={k:v[k]for k in ('path','bytes','sha256')},v['path']
adoption=read(A/'ACTUAL-SOURCE-ADOPTION.json');assert ref(A/'ACTUAL-SOURCE-ADOPTION.json')['sha256']=='f24b9dbe11483db23b16ab896521d183385ad8e64dc64b03c8f969dc55101b39'and ref(A/'ACTUAL-SOURCE-ADOPTION.json')['bytes']==27676
mount_path=N/'GENUINE-GIT-METADATA-MOUNT-RECIPE.json';mount=read(mount_path);assert ref(mount_path)['sha256']=='1c74ef32b74f1a92bae191a8a87836b522da7a10d9ad98fefabb7aca70648580'
accepted_path=E/'bfd-default-restart-independent-review-20261028-1/INSTALLED-CONSUMER-GIT-REVIEW-1/REVIEW.json';accepted=read(accepted_path);assert ref(accepted_path)['sha256']=='ca6f3ae51bf15fda06dfa743ec0ab0db5102109b0639f8070617723f4110be47'
assert accepted['reviewed_files']['GENUINE-GIT-METADATA-MOUNT-RECIPE.json']==ref(mount_path)
exact(mount['existing_source_contract']);contract=read(mount['existing_source_contract']['path'])
private=Path(adoption['private_root']);assert private==A/'source'
selected=adoption['verified_selected_inputs'];assert len(selected)==len(contract['current_source_files'])==58
assert len({x['relative']for x in selected})==58 and {x['relative']for x in selected}==set(contract['current_source_files'])
for row in selected:
 assert Path(row['actual']['path'])==private/row['relative'];exact(row['actual'])
 assert {k:row['actual'][k]for k in ('bytes','sha256')}==contract['current_source_files'][row['relative']]
exact(adoption['component_postimage']);assert (private/'ihk/linux/user/CMakeLists.txt').read_bytes()==Path(adoption['component_postimage']['path']).read_bytes()
assert adoption['component_postimage']['sha256']=='fd6b395982d4badb2e0574496cae19a7863b2f16d3841659de573ffdb14da4b2'
layout=adoption['private_layout_change'];exact(layout['authentic_gitfile']);exact(mount['source_gitfile']['private_exact_copy']);exact(mount['source_gitfile']['source'])
gitfile=private/'ihk/.git';assert gitfile.is_file()and not gitfile.is_symlink()and gitfile.read_bytes()==b'gitdir: ../.git/modules/ihk\n'
assert gitfile.read_bytes()==Path(mount['source_gitfile']['private_exact_copy']['path']).read_bytes()
assert layout['authentic_gitfile']['sha256']=='65ef4093a321dc17279db76b119a7799140650be7d7dce47dfcf272c68509ded'
assert mount['metadata_mount']==dict(actual_mount=None,destination='/source/.git/modules/ihk',readonly=True,source='/home/holden/mckernel/.git/modules/ihk',type='bind')
assert layout['real_metadata_host_directory']==mount['metadata_mount']['source']and layout['container_readonly_destination']==mount['metadata_mount']['destination']
assert posixpath.normpath('/source/ihk/../.git/modules/ihk')=='/source/.git/modules/ihk'
assert posixpath.normpath('/source/.git/modules/ihk/../../../ihk')=='/source/ihk'
for container in mount['source_directories']:
 target=private/PurePosixPath(container).relative_to('/source');assert target.is_dir()and not target.is_symlink()
assert list((private/'.git/modules/ihk').iterdir())==[]
identity=read(mount['source_git_identity']['path']);exact(mount['source_git_identity'])
for row in identity['metadata'].values():exact(row)
assert identity['local_core_worktree']=='../../../ihk'
# Read finite plan/accepted receipt only. Never read6999member contents or bank archives.
exact(adoption['accepted_bank']['finite_source_plan']);exact(adoption['accepted_bank']['materialization_receipt'])
plan=read(adoption['accepted_bank']['finite_source_plan']['path']);receipt=read(adoption['accepted_bank']['materialization_receipt']['path'])
assert len(plan['entries'])==6999 and receipt['files']==adoption['copied_finite_members']==6999
assert receipt['source_root']==adoption['accepted_bank']['root']
metadata=[row for row in plan['entries']if row['relative'].startswith('ihk/.git/')];assert len(metadata)==layout['preserved_plan_members']==21
preserved=Path(layout['preserved_original_metadata_directory']);assert preserved.parent==A and not preserved.is_symlink()and preserved.is_dir()
actual_members={str(p.relative_to(preserved))for p in preserved.rglob('*')if p.is_file()};expected_members={row['relative'][len('ihk/.git/'):]for row in metadata};assert actual_members==expected_members
checked=[];archive_not_rehashed=[]
for row in metadata:
 rel=row['relative'][len('ihk/.git/'):];p=preserved/rel;st=p.lstat();assert stat.S_ISREG(st.st_mode)and stat.S_IMODE(st.st_mode)==row['mode']and st.st_size==row['size']
 if p.suffix=='.pack':archive_not_rehashed.append(dict(relative=rel,size=row['size'],accepted_plan_sha256=row['sha256'],check='exact regular member/path/size/mode; inherited accepted content hash, no archive read/rehash'))
 else:
  actual=ref(p);assert actual['bytes']==row['size']and actual['sha256']==row['sha256'];checked.append(actual)
assert len(checked)==20 and len(archive_not_rehashed)==1
failure=read(A/'SOURCE-COPY-FAILURE.json');assert failure['tool_session']==63099 and failure['positive_tool_join_exit']==1
assert failure['second_evidence_writer_failure'].startswith('IsADirectoryError')and failure['compiler_configure_native_commands']==0
assert adoption['runtime_authority']is None and not adoption['source_bank_modified']and not adoption['accepted_export_replayed']and not adoption['SDK_rebuilt']and not adoption['runtime_source_quiescence_attested']and not layout['mount_performed']
assert adoption['compiler_commands']==adoption['configure_commands']==adoption['native_cases']==adoption['files_closed']==0
result=dict(scope=__doc__.splitlines()[0],decision='PASS_EXACT_PRIVATE_M15_SOURCE58_AND_GIT_LAYOUT_ADOPTION_ONLY',adoption=ref(A/'ACTUAL-SOURCE-ADOPTION.json'),mount_recipe=ref(mount_path),accepted_mount_review=ref(accepted_path),prelink_contract=ref(Path(mount['existing_source_contract']['path'])),failure_record=ref(A/'SOURCE-COPY-FAILURE.json'),selected_inputs=selected,selected_source_count=58,preserved_metadata_member_count=21,preserved_nonarchive_hashes=checked,unrehashed_metadata_archive=archive_not_rehashed,authentic_gitfile=ref(gitfile),empty_private_mount_target=str(private/'.git/modules/ihk'),current_metadata_identity_refs=identity['metadata'],finite_plan_receipt_only=True,all6999member_rehash=False,archive_rehash=False,reviewer_git_mount_configure_compiler_runtime_queries=0,default_native_file_credit=0,runtime_authority=None)
(HERE/'CHECKS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['selected_inputs','preserved_nonarchive_hashes','current_metadata_identity_refs']}))
