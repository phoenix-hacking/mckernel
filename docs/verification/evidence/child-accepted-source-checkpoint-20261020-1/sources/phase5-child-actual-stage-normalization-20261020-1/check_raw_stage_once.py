"""One genuine raw-child pure-loader check plus four unchanged-oracle negatives.
Prepared only: run after independent source/profile review and root admission.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess

D = Path(__file__).resolve().parent
S = D/'runtime-source-1'
IDENTITY = ('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')

def bind_whole_input():
    pins = json.loads((D/'CHECK-INPUT-PINS.json').read_bytes())
    for row in pins:
        fd = os.open(row['path'], os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            before = os.fstat(fd)
            assert stat.S_ISREG(before.st_mode) and before.st_size == row['size'] and before.st_mode == row['mode'], row['path']
            digest = hashlib.sha256()
            while True:
                block = os.read(fd, 1<<20)
                if not block: break
                digest.update(block)
            assert digest.hexdigest() == row['sha256'], row['path']
            assert all(getattr(before,k) == getattr(os.fstat(fd),k) == getattr(os.lstat(row['path']),k) for k in IDENTITY), row['path']
        finally:
            os.close(fd)
    return len(pins)

def forbidden(*args,**kwargs):
    raise AssertionError('process/socket/root effects forbidden in raw loader checks')

def load(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def rejected(action, expected):
    try: action()
    except (ValueError, AssertionError) as exc:
        assert expected in str(exc), (expected,str(exc))
        return
    raise AssertionError('negative accepted: '+expected)

def main():
    assert os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000
    assert os.sched_getaffinity(0) == {6}
    count = bind_whole_input()  # One whole assertion before any runtime import.
    subprocess.Popen = forbidden
    os.execve = forbidden
    socket.socket = forbidden
    nd = load('child_raw_bound_evaluator',S/'native_diagnostic.py')
    manifest = json.loads((D/'PROPOSED-NORMALIZED-RAW-MANIFEST.json').read_bytes())
    actual = nd._validate_manifest(copy.deepcopy(manifest))
    assert actual == manifest
    cfg = json.loads((D/'EXACT-DATA-PROPOSAL.json').read_bytes())
    argv = nd.expected_qemu_argv(actual,Path(cfg['fresh_namespaces']['attempt']))
    assert argv[argv.index('-initrd')+1] == manifest['staging']['derived_initramfs']['path']
    assert argv[argv.index('-kernel')+1] == manifest['artifacts']['bzImage']['path']
    assert argv[argv.index('-qmp')+1] == 'unix:'+cfg['fresh_namespaces']['qmp_socket']+',server=on,wait=off'
    assert len(os.fsencode(cfg['fresh_namespaces']['qmp_socket'])) <= 107
    print('PASS genuine complete raw child stage and unchanged235B oracle; bound_inputs='+str(count))
    bad=copy.deepcopy(manifest);bad['payload']['oracle']['exit_code']=1
    rejected(lambda:nd._validate_manifest(bad),'exact child raw case payload')
    print('PASS changed exact child oracle rejected')
    bad=copy.deepcopy(manifest);bad['staging']['derived_initramfs']['sha256']='0'*64
    rejected(lambda:nd._validate_manifest(bad),'derived_initramfs hash drift')
    print('PASS changed gzip artifact identity rejected')
    adapter = nd._child_raw_adapter();original = adapter.read_json
    def changed_inventory(row,ref,need):
        value=original(row,ref,need)
        if row['path']==manifest['staging']['raw_manifest']['path']:
            value['staged_inventory'][0]['mode'] ^= 1
        return value
    adapter.read_json=changed_inventory
    rejected(lambda:adapter.validate_staging(manifest['staging'],manifest['artifacts'],manifest['modules'],nd._ref,nd._need),'child whole raw manifest identity and complete inventories')
    print('PASS changed full raw inventory metadata rejected')
    def changed_identity(row,ref,need):
        value=original(row,ref,need)
        if row['path']==adapter.CONTRACT['path']:
            value['source_identities'][manifest['artifacts']['native_boot']['path']]['st_ino'] += 1
        return value
    adapter.read_json=changed_identity
    rejected(lambda:adapter.validate_staging(manifest['staging'],manifest['artifacts'],manifest['modules'],nd._ref,nd._need),'child source nine-field identity')
    print('PASS changed source inode identity rejected; guest/root/archive/app runs=0')

if __name__ == '__main__':
    main()
