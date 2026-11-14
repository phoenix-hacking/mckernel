"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Tiny directory-shape/readonly namespace model; no actual mount, Docker or source edit.
"""
import hashlib,importlib.util,json,os,stat,tempfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('mountpoint_once',HERE/'repair_mountpoint_once.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def reject(fn):
    try:fn()
    except (ValueError,OSError):return
    raise AssertionError('negative shape control accepted')
def namespace_target_ready(source,target):
    # Existing /src is read-only. runc must find nested target already present;
    # creating an absent descendant under this RO source would require a write.
    path=source/target.relative_to('/src')
    if not path.is_dir():raise ValueError('missing target under readonly /src')
    return dict(parent_source_readonly=True,nested_vendor_readonly=True,mkdir_under_readonly_source=False)
def main():
    begin=time.monotonic();checks=[]
    with tempfile.TemporaryDirectory(prefix='mountpoint-fixture-',dir=HERE) as d:
        root=Path(d)/'source';root.mkdir(mode=0o700);parent=root/'executer/user/lib/libdwarf';parent.mkdir(parents=True,mode=0o700);target=parent/'libdwarf';f=root/'runtime.rs';f.write_bytes(b'fn functional() {}\n');f.chmod(0o644);s=f.stat();rows=[dict(relative='runtime.rs',kind='file',size=s.st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),mode=0o644)]
        before=m.inventory(root,rows);rootmeta=m.meta(root.lstat());original_parent=m.node(parent)
        reject(lambda:namespace_target_ready(root,Path('/src/executer/user/lib/libdwarf/libdwarf')));checks.append('original_missing_target_rejected_in_readonly_namespace_model')
        wrong=dict(original_parent,inode=original_parent['inode']+1);reject(lambda:m.create_exact_empty(root,target,wrong));checks.append('wrong_parent_identity_rejected')
        reject(lambda:m.create_exact_empty(root,root/'other',original_parent));checks.append('different_target_path_rejected')
        made=m.create_exact_empty(root,target,original_parent);assert made['mode']==0o700 and made['uid']==made['gid']==1000 and not list(target.iterdir());checks.append('exact_owned_empty_directory_created')
        assert namespace_target_ready(root,Path('/src/executer/user/lib/libdwarf/libdwarf'))==dict(parent_source_readonly=True,nested_vendor_readonly=True,mkdir_under_readonly_source=False);checks.append('readonly_parent_and_readonly_nested_vendor_shape_model_pass')
        assert before==m.inventory(root,rows) and rootmeta==m.meta(root.lstat()) and f.stat().st_mtime_ns==s.st_mtime_ns;checks.append('file_bytes_modes_mtime_ctime_and_source_root_metadata_preserved')
        reject(lambda:m.create_exact_empty(root,target,original_parent));checks.append('existing_target_replay_rejected')
        badroot=Path(d)/'badsource';badroot.mkdir(mode=0o700);lp=badroot/'executer/user/lib';lp.mkdir(parents=True);(lp/'libdwarf').symlink_to(parent,target_is_directory=True);reject(lambda:m.create_exact_empty(badroot,lp/'libdwarf/libdwarf',original_parent));checks.append('symlink_parent_rejected')
        hard=root/'extra';os.link(f,hard);reject(lambda:m.inventory(root,rows));checks.append('extra_file_inventory_rejected');hard.unlink()
        f.write_bytes(b'changed source\n');reject(lambda:m.inventory(root,rows));checks.append('changed_source_file_rejected')
    p=json.loads(m.PLAN.read_bytes());assert m.ref(m.PLAN)['sha256']==m.PLAN_SHA;assert not os.path.lexists(p['target']);checks.append('actual_target_still_absent_no_protected_mutation')
    result=dict(status='PASS_TINY_MOUNTPOINT_SHAPE_FIXTURE_ONLY',scope=p['scope'],checks=checks,seconds=time.monotonic()-begin,actual_source_mutation=False,actual_mount_or_Docker=False,actual_guard_or_resource_query=False,execution_authority=False)
    (HERE/'PURE-TEST-RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
