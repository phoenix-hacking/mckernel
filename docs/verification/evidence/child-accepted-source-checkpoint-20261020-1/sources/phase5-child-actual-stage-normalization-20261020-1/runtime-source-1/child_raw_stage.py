"""One exact accepted child raw stage; metadata only, no overlay provenance."""
import hashlib
import json
import os
from pathlib import Path
import stat

CONTRACT = {'path': '/home/holden/mckernel-work/host-preparation/phase5-child-actual-stage-normalization-20261020-1/runtime-source-1/RAW-STAGE-CONTRACT.json', 'size': 42695, 'mode': 33152, 'sha256': '2586bb177c42ee31dded5422dc34099eec3e18e9af21f24ec22e2ab786287f73'}
KIND = 'child-actual-raw-stage-v1'
IDENTITY = ('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')

def _pairs(items):
    obj = {}
    for key,value in items:
        if key in obj:
            raise ValueError('duplicate child raw JSON key: '+key)
        obj[key] = value
    return obj

def read_json(row, ref, need):
    ref(row, 'child raw JSON source')
    raw = Path(row['path']).read_bytes()
    need(len(raw) == row['size'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'child raw JSON changed during read')
    return json.loads(raw, object_pairs_hook=_pairs)

def contract(ref, need):
    return read_json(CONTRACT, ref, need)

def validate_case(obj, ref, need):
    c = contract(ref, need)
    for key in ('case_id','payload','profile','modules','artifacts'):
        need(obj.get(key) == c[key], 'exact child raw case ' + key)

def validate_staging(obj, artifacts, modules, ref, need):
    c = contract(ref, need)
    need(set(obj) == {'kind','derived_initramfs','collector','raw_manifest','raw_stage_acceptance'}, 'child raw staging keys')
    need(obj['kind'] == KIND, 'child raw staging kind')
    need(artifacts == c['artifacts'] and modules == c['modules'], 'child complete current artifact tuple')
    refs = {name:ref(obj[name], 'child raw '+name) for name in ('derived_initramfs','collector','raw_manifest','raw_stage_acceptance')}
    need(all(refs[name] == c[name] for name in refs), 'child raw stage exact refs')
    raw = read_json(refs['raw_manifest'], ref, need)
    need(raw == c['raw_document'], 'child whole raw manifest identity and complete inventories')
    need(raw['kind'] == 'native-diagnostic-initramfs' and raw['schema_version'] == 1, 'genuine raw stage kind')
    need(len(raw['staged_inventory']) == 60 and len(raw['source_inventory']) == 56, 'complete child inventories')
    need(set(raw['replacements']) == {'bin/mcexec','bin/native-boot','images/mckernel.img','modules/ihk.ko','modules/ihk-smp-x86_64.ko','modules/mcctrl.ko'}, 'complete six replacement roles')
    proof = read_json(refs['raw_stage_acceptance'], ref, need)
    need(proof['schema'] == 'mckernel.child-six-artifact-actual-offline-stage-independent-review.v1' and proof['status'] == 'PASS_ACTUAL_SIX_ROLE_REAL_ARCHIVE_STAGE_ONLY' and proof['stage_acceptance'] is True, 'actual child raw stage independent acceptance')
    need(proof['stage_manifest']['path'] == refs['raw_manifest']['path'] and proof['stage_manifest']['sha256'] == refs['raw_manifest']['sha256'], 'actual independent stage manifest join')
    for proof_key, actual in [('stage_manifest',refs['raw_manifest']),('raw_archive',c['raw_archive']),('compressed_archive',refs['derived_initramfs']),('collector_fresh0755',refs['collector'])]:
        expected = proof[proof_key]
        need((expected['path'],expected['sha256'],expected['bytes'],expected['mode']) == (actual['path'],actual['sha256'],actual['size'],actual['mode']), 'complete accepted raw proof '+proof_key)
    ref(c['raw_archive'], 'child full raw archive')
    need(raw['artifacts']['initramfs.cpio'] == c['raw_archive']['sha256'] and raw['artifacts']['initramfs.cpio.gz'] == refs['derived_initramfs']['sha256'], 'raw and gzip artifact hashes')
    need(raw['payload']['path'] == artifacts['payload']['path'] and raw['payload']['sha256'] == artifacts['payload']['sha256'], 'unchanged actual child app')
    need(raw['collector']['path'] == refs['collector']['path'] and raw['collector']['sha256'] == refs['collector']['sha256'], 'corrected actual child collector')
    roles = {'bin/mcexec':artifacts['mcexec'],'bin/native-boot':artifacts['native_boot'],'images/mckernel.img':artifacts['mckernel_image'],**{'modules/'+Path(row['path']).name:row for row in modules}}
    inventory = {row['path']:row for row in raw['staged_inventory']}
    for name, item in roles.items():
        source = raw['replacements'][name]
        need(source['path'] == item['path'] and source['sha256'] == source['final_sha256'] == item['sha256'] and source['size'] == source['final_size'] == item['size'] and source['mode'] == source['final_mode'] == stat.S_IMODE(item['mode']), 'child replacement source ' + name)
        actual = os.lstat(item['path'])
        need(actual.st_dev == source['dev'] and actual.st_ino == source['inode'], 'child replacement inode ' + name)
        need((inventory[name]['sha256'],inventory[name]['size'],inventory[name]['mode']) == (item['sha256'],item['size'],stat.S_IMODE(item['mode'])), 'child final inventory role ' + name)
    for name,item in [('init',refs['collector']),('apps/app',artifacts['payload']),('lib64/ld-linux-x86-64.so.2',artifacts['loader']),('lib64/libc.so.6',artifacts['libc'])]:
        need((inventory[name]['sha256'],inventory[name]['size'],inventory[name]['mode']) == (item['sha256'],item['size'],0o755), 'child final member '+name)
    for path, expected in c['source_identities'].items():
        current = os.lstat(path)
        need({name:getattr(current,name) for name in IDENTITY} == expected, 'child source nine-field identity '+path)
    # The independent physical stage acceptance binds all 60 archive members and
    # all 56 base inventory rows. Do not invent an overlay or reparse/recompress.
    return {'kind':KIND, **refs}
