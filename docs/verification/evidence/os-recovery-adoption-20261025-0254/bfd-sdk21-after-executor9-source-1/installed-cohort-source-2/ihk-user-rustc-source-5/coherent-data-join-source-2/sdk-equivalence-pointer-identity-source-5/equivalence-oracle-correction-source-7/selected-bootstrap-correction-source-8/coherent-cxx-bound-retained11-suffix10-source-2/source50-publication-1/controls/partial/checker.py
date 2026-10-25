#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual incomplete local filesystem with exact declared paths/aliases; no SDK/owner.
Short file bytes are explicit copy-in-progress models, never a completed source claim.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,posixpath,tempfile
BASE=Path(__file__).resolve().parent
ROLE=BASE.parent/'role-inventory-source-1/EXACT-USER-CLONE-ROLE.json'
CORE=BASE.parent/'role-inventory-source-1/measure_role_inventory.SOURCE-ONLY.py'

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-once',required=True);args=parser.parse_args()
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==args.check_once
    assert hashlib.sha256(ROLE.read_bytes()).hexdigest()=='f3296f48a3890f965d931983eff6361e668b6d13ac209bb096bfc6cd8f3c72f1'
    assert hashlib.sha256(CORE.read_bytes()).hexdigest()=='413d329efc4b503cfa34d4e7d56a54eab829a476b6b3b04bcbcda06d70e9bd84'
    role=json.loads(ROLE.read_bytes());role.update(generated_entry_limit=4096,logical_limit=512<<20,allocated_limit=4<<30)
    expected=role['rows'];links={name:row for name,row in expected.items() if row['type']=='symlink'}
    assert len(expected)==3053 and len(links)==72
    assert all(posixpath.normpath(posixpath.join(posixpath.dirname(name),row['target']))==row['resolved'] for name,row in links.items()),'all actual aliases directly normalize to declaredtarget'
    spec=importlib.util.spec_from_file_location('exact_partial_role_core',CORE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    records=[]
    with tempfile.TemporaryDirectory(prefix='bfd-partial-clone-model-') as temporary:
        root=Path(temporary);clone=root/role['clone_relative_root']
        def run(name,limits=None):
            result=module.role_inventory(root,limits or role,role['clone_relative_root'],False)
            records.append(dict(case=name,status='PASS',inventory=result))
        def refuse(name,action,restore,limits=None,complete=False):
            action()
            try:
                try:module.role_inventory(root,limits or role,role['clone_relative_root'],complete)
                except (ValueError,OSError,RuntimeError) as error:records.append(dict(case=name,status='EXPECTED_REFUSAL',error=str(error)))
                else:raise AssertionError('accepted invalid partialclone '+name)
            finally:restore()
        run('empty-output-before-clone')
        clone.mkdir(parents=True);os.chmod(clone,0o700)
        assert 0o700!=expected['']['mode']
        run('missing-declared-entries-and-provisional-directory-mode')
        file_name=next(name for name,pin in expected.items() if pin['type']=='file' and pin['size']>4 and pin['mode']!=0o600)
        pin=expected[file_name];file=clone/file_name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'x');os.chmod(file,0o600)
        assert file.stat().st_size<pin['size'] and file.stat().st_mode&0o777!=pin['mode']
        run('short-copied-bytes-before-copystat')
        alias_name=next(name for name,row in links.items() if row['target_type']=='file');alias_pin=links[alias_name];alias=clone/alias_name;alias.parent.mkdir(parents=True,exist_ok=True);alias.symlink_to(alias_pin['target'])
        assert not (clone/alias_pin['resolved']).exists()
        run('declared-dangling-file-alias-no-target-copied')
        diralias_name=next(name for name,row in links.items() if row['target_type']=='directory');diralias_pin=links[diralias_name];diralias=clone/diralias_name;diralias.parent.mkdir(parents=True,exist_ok=True);diralias.symlink_to(diralias_pin['target'])
        assert not (clone/diralias_pin['resolved']).exists()
        run('declared-dangling-directory-alias-no-traversal')
        refuse('short-file-over-declared-size',lambda:file.write_bytes(b'x'*(pin['size']+1)),lambda:file.write_bytes(b'x'))
        alien=clone/'NOT-DECLARED';refuse('undeclared-partial-entry',lambda:alien.write_bytes(b''),lambda:alien.unlink())
        refuse('changed-alias-escape',lambda:(alias.unlink(),alias.symlink_to('/tmp')),lambda:(alias.unlink(),alias.symlink_to(alias_pin['target'])))
        refuse('file-becomes-directory',lambda:(file.unlink(),file.mkdir()),lambda:(file.rmdir(),file.write_bytes(b'x')))
        refuse('partial-claimed-complete',lambda:None,lambda:None,complete=True)
        refuse('partial-logical-cap',lambda:None,lambda:None,dict(role,logical_limit=0))
        refuse('partial-allocated-cap',lambda:None,lambda:None,dict(role,allocated_limit=0))
        refuse('partial-source-count-cap',lambda:None,lambda:None,dict(role,source_entry_limit=1))
        generated=root/'generated-alias';refuse('generated-unpinned-alias',lambda:generated.symlink_to('/tmp'),lambda:generated.unlink())
        run('restored-incomplete-source-still-accepted')
    assert len(records)==15 and sum(row['status']=='PASS' for row in records)==6
    print(json.dumps(dict(status='PASS_ACTUAL_PARTIAL_FILESYSTEM_MODEL_ONLY',records=records,declared_source_paths=3053,declared_aliases=72,helper_unchanged=True,SDK_or_native_acceptance=False),indent=2))
if __name__=='__main__':main()
