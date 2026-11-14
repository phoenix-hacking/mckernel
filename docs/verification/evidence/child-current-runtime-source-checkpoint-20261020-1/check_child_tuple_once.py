"""One real readonly child tuple positive and three changed-input refusals."""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,socket,stat,subprocess
R=Path(__file__).resolve().parent
S=R/'source'
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def forbidden(*args,**kwargs):raise AssertionError('process/socket/root/writer effect forbidden')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def bind():
    rows=json.loads((R/'TUPLE-CHECK-INPUT-PINS.json').read_bytes())
    for row in rows:
        fd=os.open(row['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            a=os.fstat(fd);assert stat.S_ISREG(a.st_mode)and a.st_mode==row['mode']and a.st_size==row['size'];h=hashlib.sha256()
            while True:
                block=os.read(fd,1<<20)
                if not block:break
                h.update(block)
            assert h.hexdigest()==row['sha256'],row['path'];b=os.fstat(fd);c=os.lstat(row['path']);assert all(getattr(a,k)==getattr(b,k)==getattr(c,k)for k in FIELDS)
        finally:os.close(fd)
    return len(rows)
def reject(action):
    try:action()
    except AssertionError:return
    raise AssertionError('changed role/effect/namespace incorrectly accepted')
def main():
    assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000 and os.sched_getaffinity(0)=={6}
    count=bind()
    subprocess.Popen=forbidden;os.execve=forbidden;socket.socket=forbidden
    selected=load('child_tuple_actual_body',S/'select_child_tuple_once.py');result=selected.select();t=result['tuple']
    assert len(result['outputs'])==19 and len(result['captures'])==49
    print('PASS genuine child whole tuple/19outputs/49captures/QMP97; bound_inputs='+str(count))
    original=selected.exact
    wrong=copy.deepcopy(t);wrong['actual_normalization_acceptance']=t['accepted_physical_reader']['independent_whole_acceptance']
    def wrong_role(row):return json.dumps(wrong).encode()if row==selected.TUPLE else original(row)
    selected.exact=wrong_role;reject(selected.select);selected.exact=original
    print('PASS genuine physical proof refused in child normalization role')
    contract=load('child_contract_false_effect_actual_body',S/'child_normalization_contract.py');read=contract.read
    def false_effect(row):
        raw=read(row)
        if row['path']==result['original_role']['report']['actual_preflight']['path']:
            value=json.loads(raw);value['clocks_or_host_effects']=1;return json.dumps(value).encode()
        return raw
    contract.read=false_effect;reject(lambda:contract.validate(t['actual_normalization_acceptance'],t['raw_artifact_authority']))
    print('PASS false clock/effect fact refused by genuine child contract')
    wrong=copy.deepcopy(t);wrong['packet_output_locator']['selected_static_inputs_template']=str(R/'wrong-packet'/'STATIC-CHILD-NONTEMPORAL-INPUTS.PENDING.json')
    def wrong_namespace(row):return json.dumps(wrong).encode()if row==selected.TUPLE else original(row)
    selected.exact=wrong_namespace;reject(selected.select);selected.exact=original
    print('PASS changed output namespace refused; process/socket/writer/root/guest effects=0')
if __name__=='__main__':main()
