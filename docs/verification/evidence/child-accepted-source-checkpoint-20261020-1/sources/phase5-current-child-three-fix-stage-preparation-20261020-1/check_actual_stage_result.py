"""Verify real produced stage identities after the one real archive command."""
from pathlib import Path
import hashlib,json,stat
D=Path(__file__).resolve().parent

def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def main():
    cfg=json.loads((D/'STAGE-INPUTS.json').read_bytes());out=Path(cfg['stage_output']);m=json.loads((out/'manifest.json').read_bytes())
    assert m['kind']=='native-diagnostic-initramfs' and m['schema_version']==1 and m['base_root']==cfg['base_root']
    app=cfg['unchanged_app_and_oracle']['binary'];collector=cfg['collector_copy']
    assert m['payload']==dict(path=app['path'],sha256=app['sha256'])
    assert m['collector']==dict(path=collector['path'],sha256=collector['sha256'])
    assert set(m['replacements'])==set(cfg['required_six_replacements'])
    inv={r['path']:r for r in m['staged_inventory']};assert len(inv)==len(m['staged_inventory'])
    for role,expected in cfg['required_six_replacements'].items():
        observed=m['replacements'][role];assert {k:observed[k]for k in expected}==expected
        row=inv[role];assert row['type']=='file' and all(row[k]==expected[k] for k in ('sha256','size','mode'))
        assert observed['final_sha256']==expected['sha256'] and observed['final_size']==expected['size'] and observed['final_mode']==expected['mode']
    assert inv['bin/native-boot']['sha256']==cfg['refs']['native_boot']['sha256'] and inv['bin/native-boot']['size']==35784
    assert inv['init']['sha256']==collector['sha256'] and inv['init']['size']==collector['bytes'] and inv['init']['mode']==0o755
    assert inv['apps/app']['sha256']==app['sha256'] and inv['apps/app']['size']==app['bytes'] and inv['apps/app']['mode']==0o755
    for name,h in m['artifacts'].items():assert name in ('initramfs.cpio','initramfs.cpio.gz') and digest(out/name)==h
    for row in m['staged_inventory']:
        p=out/'root'/row['path'];s=p.lstat();assert stat.S_IMODE(s.st_mode)==row['mode']
        if row['type']=='file':assert s.st_size==row['size'] and digest(p)==row['sha256']
    print(json.dumps(dict(status='PASS_REAL_ARCHIVE_MANIFEST_SIX_ROLE_AND_235B_JOIN',members=len(inv),native_boot=inv['bin/native-boot']['sha256'],collector=collector['sha256'],normalized_runtime_acceptance=False,guest_runs=0),sort_keys=True))

if __name__=='__main__':main()
