"""Actual corrected producer and actual snapshot non-effect static_joins."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,socket,stat,subprocess
C=Path(__file__).resolve().parent
R=C.parent
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def forbidden(*args,**kwargs):raise AssertionError('live/process/socket/mkdir/publish effect forbidden')
def exact(row):
    fd=os.open(row['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        a=os.fstat(fd);assert stat.S_ISREG(a.st_mode)and a.st_mode==row['mode']and a.st_size==row['size'];h=hashlib.sha256()
        while True:
            b=os.read(fd,1<<20)
            if not b:break
            h.update(b)
        assert h.hexdigest()==row['sha256'],row['path'];after=os.fstat(fd);named=os.lstat(row['path']);assert all(getattr(a,k)==getattr(after,k)==getattr(named,k)for k in FIELDS)
    finally:os.close(fd)
def main():
    assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000 and os.sched_getaffinity(0)=={6}
    cfg=json.loads((C/'FIXTURE-INPUTS.json').read_bytes())
    for row in cfg['pins']:exact(row)
    subprocess.Popen=forbidden;subprocess.run=forbidden;os.execve=forbidden;socket.socket=forbidden;os.mkdir=forbidden
    source=Path(cfg['candidate']['path']);tree=ast.parse(source.read_bytes())
    names={'load','ref','typed_ref','need','derive_current_control_tuple','bind_current_control_tuple'}
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names];assert {n.name for n in functions}==names
    namespace={'Path':Path,'hashlib':hashlib,'json':json,'copy':copy}
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),namespace)
    data=json.loads(Path(cfg['static_inputs']['path']).read_bytes());pre=json.loads(Path(cfg['preflight']['path']).read_bytes());binding=pre['binding'];original=json.loads(Path(cfg['actual_original_bindings']['path']).read_bytes())
    owner_tree=ast.parse(Path(data['runtime_owner']['path']).read_bytes());runtime=ast.literal_eval(next(n.value for n in owner_tree.body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='SOURCE_HASHES'for x in n.targets)))
    current=namespace['derive_current_control_tuple'](binding,data,pre,runtime)
    corrected=namespace['bind_current_control_tuple'](original,current)
    manifest=json.loads(Path(binding['manifest']['path']).read_bytes())
    assert corrected['repaired_image_sha256']==manifest['artifacts']['mckernel_image']['sha256'] and corrected['repaired_image_sha256']!=original['repaired_image_sha256']
    assert current['artifacts']==manifest['artifacts']and current['modules']==manifest['modules']and current['payload']==manifest['payload']and current['owner']==data['runtime_owner']
    assert {k for k in corrected if corrected[k]!=original.get(k)}=={'repaired_image_sha256','authoritative_current_control_tuple'}
    print('PASS actual producer derives complete genuine current image/module/app/owner tuple')
    snapshot_path=Path(cfg['snapshot']['path']);spec=importlib.util.spec_from_file_location('corrected_child_snapshot_actual_consumer',snapshot_path);snapshot=importlib.util.module_from_spec(spec);spec.loader.exec_module(snapshot)
    snapshot.collect_live=forbidden;snapshot.validate_live=forbidden;snapshot.publish=forbidden;snapshot.command=forbidden
    proposal,owner=snapshot.static_joins(corrected)
    assert proposal['normalized_manifest']==binding['manifest']and owner.SOURCE_HASHES==runtime
    print('PASS unchanged actual snapshot static_joins accepts genuine current child digest')
    try:snapshot.static_joins(original)
    except snapshot.Refusal as exc:assert str(exc)=='fixed current child image',str(exc)
    else:raise AssertionError('retained inherited image digest accepted')
    print('PASS unchanged actual snapshot static_joins rejects retained inherited old digest')
    wrong=copy.deepcopy(original);wrong['runtime_owner']['sha256']='0'*64
    try:namespace['bind_current_control_tuple'](wrong,current)
    except ValueError as exc:assert 'existing current manifest/owner/source roles'in str(exc)
    else:raise AssertionError('wrong coupled owner tuple accepted')
    print('PASS coupled current owner/source tuple refusal; live/root/snapshot/write/guest effects=0')
if __name__=='__main__':main()
