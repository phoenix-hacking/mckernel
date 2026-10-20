"""Fixed one-shot child: actual auth/checks, real archive, actual result joins.
Functional OS/apps and Rust/reviewed assembly cutover; no guest or app launch.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,stat
D=Path(__file__).resolve().parent

def exact(row):
    p=Path(row['path']);a=p.lstat();raw=p.read_bytes();b=p.lstat()
    assert stat.S_ISREG(a.st_mode) and len(raw)==row.get('bytes',row.get('size')) and hashlib.sha256(raw).hexdigest()==row['sha256']
    if 'mode' in row:assert a.st_mode==row['mode']
    assert all(getattr(a,k)==getattr(b,k) for k in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns'))
    return raw

def load(name,row):
    exact(row);s=importlib.util.spec_from_file_location(name,row['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
    data=json.loads((D/'EXECUTION-DATA.json').read_bytes());cfg=json.loads(exact(data['inputs']))
    for row in data['private_sources']:exact(row)
    for row in cfg['refs'].values():exact(row)
    target=Path(cfg['collector_copy']['path']);assert not os.path.lexists(target)
    raw=exact(cfg['refs']['corrected_collector'])
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o755)
    with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fchmod(f.fileno(),0o755);os.fsync(f.fileno())
    exact(cfg['collector_copy'])
    load('actual_child_input_checks',data['input_checker']).main()
    print('CHILD_STAGE_PHASE=INPUT_AUTH_CLI_235B_EVALUATOR_JOIN_OK',flush=True)
    load('exact_six_role_stager',cfg['stager']).main(cfg['stage_argv'][4:])
    print('CHILD_STAGE_PHASE=REAL_ARCHIVE_CONSTRUCTED',flush=True)
    load('actual_child_stage_result_check',data['result_checker']).main()
    print('CHILD_STAGE_PHASE=REAL_MANIFEST_SIX_ROLE_JOIN_OK',flush=True)

if __name__=='__main__':main()
