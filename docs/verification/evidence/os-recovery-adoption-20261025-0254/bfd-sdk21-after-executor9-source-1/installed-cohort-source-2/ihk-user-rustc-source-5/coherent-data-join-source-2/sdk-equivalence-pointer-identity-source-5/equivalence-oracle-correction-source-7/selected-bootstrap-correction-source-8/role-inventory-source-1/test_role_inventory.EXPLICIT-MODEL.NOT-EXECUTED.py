#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
UNRUN ordinary local filesystem model. No owner import, process, SDK or query.
Uses exact declared3053-path/72-alias shape; empty model file bytes are explicit.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest import mock
from types import SimpleNamespace

BASE=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-once',required=True)
    args=parser.parse_args()
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==args.check_once
    source=BASE/'measure_role_inventory.SOURCE-ONLY.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='413d329efc4b503cfa34d4e7d56a54eab829a476b6b3b04bcbcda06d70e9bd84'
    declaration=BASE/'EXACT-USER-CLONE-ROLE.json'
    assert hashlib.sha256(declaration.read_bytes()).hexdigest()=='f3296f48a3890f965d931983eff6361e668b6d13ac209bb096bfc6cd8f3c72f1'
    spec=importlib.util.spec_from_file_location('bounded_role_inventory_model',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    role=json.loads(declaration.read_bytes())
    role.update(generated_entry_limit=4096,logical_limit=512<<20,allocated_limit=4<<30)
    expected=role['rows']
    for pin in expected.values():
        if pin['type']=='file':pin.update(size=0,sha256=hashlib.sha256(b'').hexdigest())
    records=[]
    with tempfile.TemporaryDirectory(prefix='bfd-role-model-') as temporary:
        root=Path(temporary); clone=root/role['clone_relative_root'];clone.mkdir(parents=True)
        for name,pin in sorted(expected.items(),key=lambda item:(len(Path(item[0]).parts),item[0])):
            path=clone/name
            if pin['type']=='directory':path.mkdir(exist_ok=True)
            elif pin['type']=='file':path.write_bytes(b'')
            else:path.symlink_to(pin['target'])
        for name,pin in expected.items():
            if pin['type']!='symlink':os.chmod(clone/name,pin['mode'])
        def run(label,limits=None,complete=True):
            value=module.role_inventory(root,limits or role,role['clone_relative_root'],complete)
            records.append(dict(case=label,status='PASS',inventory=value))
        def refuse(label,action,restore,limits=None):
            action()
            try:
                try:module.role_inventory(root,limits or role,role['clone_relative_root'],True)
                except (ValueError,OSError,RuntimeError) as error:records.append(dict(case=label,status='EXPECTED_REFUSAL',error=str(error)))
                else:raise AssertionError('accepted invalid model: '+label)
            finally:restore()
        run('exact3053-path72-alias-complete-model')
        run('declared-partial-model',complete=False)
        file_name=next(name for name,pin in expected.items() if pin['type']=='file')
        file=clone/file_name;file_mode=expected[file_name]['mode']
        refuse('file-size',lambda:file.write_bytes(b'x'),lambda:file.write_bytes(b''))
        bad=copy.deepcopy(role);bad['rows'][file_name]['sha256']='0'*64
        refuse('file-hash',lambda:None,lambda:None,bad)
        refuse('file-mode',lambda:os.chmod(file,file_mode^0o100),lambda:os.chmod(file,file_mode))
        refuse('missing-complete-path',lambda:file.unlink(),lambda:(file.write_bytes(b''),os.chmod(file,file_mode)))
        alien=clone/'UNDECLARED'
        refuse('undeclared-source',lambda:alien.write_bytes(b''),lambda:alien.unlink())
        link_name=next(name for name,pin in expected.items() if pin['type']=='symlink');link=clone/link_name;target=expected[link_name]['target']
        refuse('alias-escape',lambda:(link.unlink(),link.symlink_to('/tmp')),lambda:(link.unlink(),link.symlink_to(target)))
        refuse('generated-alias',lambda:(root/'generated-link').symlink_to(clone),lambda:(root/'generated-link').unlink())
        refuse('special-fifo',lambda:os.mkfifo(root/'FIFO'),lambda:(root/'FIFO').unlink())
        refuse('hardlink',lambda:os.link(file,root/'HARDLINK'),lambda:(root/'HARDLINK').unlink())
        for label,key,value in [('source-cap','source_entry_limit',3052),('generated-cap','generated_entry_limit',1),('allocated-cap','allocated_limit',0),('logical-cap','logical_limit',0)]:
            limits=dict(role);limits[key]=value
            refuse(label,lambda:None,lambda:None,limits)
        generated=root/'generated';generated.mkdir()
        refuse('real-generated4097-cap',lambda:[(generated/str(index)).touch() for index in range(4097)],lambda:[path.unlink() for path in generated.iterdir()])
        generated.rmdir()
        real_lstat=Path.lstat;calls=[0]
        def changed_identity(path):
            observed=real_lstat(path)
            if path==root:
                calls[0]+=1
                if calls[0]>=3:
                    fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_blocks','st_size','st_nlink','st_mtime_ns','st_ctime_ns')
                    values={key:getattr(observed,key) for key in fields};values['st_ino']+=1
                    return SimpleNamespace(**values)
            return observed
        with mock.patch.object(Path,'lstat',changed_identity):
            refuse('root-identity-change',lambda:None,lambda:None)
        run('restored-full-model')
    assert len(records)==18
    print(json.dumps({'status':'PASS_EXPLICIT_FILESYSTEM_MODEL_ONLY','source_paths':3053,'aliases':72,'records':records,'SDK_or_native_acceptance':False},indent=2))

if __name__=='__main__':main()
