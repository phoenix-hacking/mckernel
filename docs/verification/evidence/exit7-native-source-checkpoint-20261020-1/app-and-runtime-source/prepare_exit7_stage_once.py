"""Proposed finite offline exit7 derivative; run only under dispatcher grant.

Functional OS/apps plus Rust/reviewed assembly cutover. Reuses accepted
collector and derive body; creates one same-byte0755 app copy and archive.
No process, root, module, guest, compiler or native release is started.
"""
from pathlib import Path
import copy, hashlib, importlib.util, json, os, stat
D=Path(__file__).resolve().parent

def read_exact(row):
    p=Path(row['path']); a=p.lstat()
    assert stat.S_ISREG(a.st_mode) and a.st_mode==row['mode']
    raw=p.read_bytes(); b=p.lstat()
    assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns)
    assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    return raw

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def main():
    cfg=json.loads((D/'INPUT-AND-DECLARED-DATA.json').read_bytes())
    for key in ('retained_case','accepted_linux','rust_source','oracle','accepted_app',
                'expected_stdout','expected_stderr','tested_parent','current_collector',
                'current_overlay','base','stage_engine','overlay_engine',
                'tested_runtime_evaluator','private_evaluator'):
        read_exact(cfg[key])
    parent=json.loads(read_exact(cfg['tested_parent']))
    assert parent['modules']==cfg['matched_modules'] and parent['profile']==cfg['matched_profile']
    for name,row in cfg['matched_artifacts'].items():
        assert parent['artifacts'][name]==row
    for row in (*cfg['matched_artifacts'].values(),*cfg['matched_modules']):read_exact(row)
    assert parent['staging']['collector']==cfg['current_collector']
    assert parent['staging']['derived_initramfs']==cfg['base']
    assert set(parent)=={'schema_version','kind','case_id','artifacts','modules','profile','payload','staging'}
    nd=load('exit7_exact_evaluator',cfg['private_evaluator']['path'])
    ov=load('exit7_accepted_overlay',cfg['overlay_engine']['path'])
    engine=load('exit7_accepted_derive',cfg['stage_engine']['path'])
    output=D/'ordinary-stage-1';assert not os.path.lexists(output)
    output.mkdir(mode=0o700)
    source=Path(cfg['accepted_app']['path']);before=source.lstat()
    assert before.st_mode==0o100700
    raw=read_exact(cfg['accepted_app'])
    target=Path(cfg['declared_payload_copy']['path']);assert target.parent==output
    engine.write(target,raw);os.chmod(target,0o755)
    assert engine.ref(target)==cfg['declared_payload_copy']
    after=source.lstat()
    assert (before.st_dev,before.st_ino,before.st_mode,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_mode,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
    old_map=json.loads(read_exact(cfg['current_overlay']))['final_map']
    archive=output/'exit7.cpio.gz'
    overlay=engine.derive(ov,cfg['base'],cfg['declared_payload_copy'],cfg['current_collector'],cfg['matched_artifacts']['mcexec'],archive,old_map)
    assert overlay['final_map']['init']==old_map['init']
    engine.js(output/'overlay-manifest.json',overlay)
    m=copy.deepcopy(parent);m['case_id']=cfg['case_id'];m['payload']=cfg['payload_contract']
    m['artifacts']['payload']=cfg['declared_payload_copy']
    m['artifacts']['initramfs']=m['artifacts']['root_base']=cfg['base']
    m['staging']=dict(base_initramfs=cfg['base'],collector=cfg['current_collector'],
        derived_initramfs=engine.ref(archive),overlay_manifest=engine.ref(output/'overlay-manifest.json'),
        overlay_source=cfg['overlay_engine'])
    nd._validate_manifest(m)
    engine.js(output/'manifest.json',m)
    assert nd.load_manifest(str(output/'manifest.json'))==m
    used=sum(p.stat().st_size for p in output.iterdir())
    assert used<=64<<20
    engine.js(output/'stage-result.json',dict(status='EXIT7_OFFLINE_STAGE_ONLY',
        manifest=engine.ref(output/'manifest.json'),payload=engine.ref(target),
        original_0700_preserved=True,collector_unchanged=True,archive_prefix_unchanged=True,
        permitted_final_changes=['apps/app'],bytes=used,guest_runs=0,native_acceptance=False))
    print(json.dumps(dict(status='EXIT7_OFFLINE_STAGE_ONLY',files=5,guest_runs=0)))

if __name__=='__main__':main()
