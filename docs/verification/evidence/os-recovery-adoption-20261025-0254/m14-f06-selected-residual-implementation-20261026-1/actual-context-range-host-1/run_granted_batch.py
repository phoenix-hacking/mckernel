"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One sequential Root-granted four-leaf batch, exactly twelve ordinary HOST commands.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

D=Path(__file__).resolve().parent
P=D.parent
EXPERT=P/'next-process-vm-selected-1/next-prctl-getter-selected-1/actual-host-getter-1/reviewed-account-supervisor-correction-1'
EXPERT_SHA='e8b84de39128433542b213fc3a374dd50d3e12f232bd397dddaa24859349a805'
ITEMS=[
 ('ptrace-context',P/'selected-context-range-backlog-1/ptrace-context','36330a8ef7106bbb59026292637f8e6a05c246613cb397c8817fc4f680b6d6e2'),
 ('ptrace-alloc',P/'selected-context-range-backlog-1/ptrace-alloc','4c499be3bcadc9683587384eea5be65916b24868b9f73676dfbc72a179764977'),
 ('vdso-add-range',P/'selected-context-range-backlog-1/vdso-add-range','6ed5a342562f54d99a1f3105ca385d52b41effe09cc02d63fe080368035cc4ff'),
 ('vdso-set-range',P/'selected-context-range-backlog-1/vdso-set-range','d1b43fbef398eb3665991d93f236cd24e7c1e2ba233d6cda0ea4852652467cb3'),
]


def ref(path):
    path=Path(path)
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify(rows):
    for row in rows:
        if ref(row['path'])!=row:raise ValueError('frozen input/tool drift: '+row['path'])


def main():
    os.sched_setaffinity(0,{6})
    for kind,limit in [(resource.RLIMIT_AS,2*2**30),(resource.RLIMIT_CPU,60),
                       (resource.RLIMIT_FSIZE,64*2**20),(resource.RLIMIT_CORE,0)]:
        resource.setrlimit(kind,(limit,limit))
    assert ref(EXPERT/'run_sealed.py')['sha256']==EXPERT_SHA
    sys.path.insert(0,str(EXPERT))
    spec=importlib.util.spec_from_file_location('accepted_f06_admission',EXPERT/'run_sealed.py')
    reviewed=importlib.util.module_from_spec(spec);spec.loader.exec_module(reviewed)
    supplement=json.loads((D/'SEALED-BATCH-BINDINGS.json').read_text())
    verify(supplement['headers']+supplement['tools'])
    plans=[]
    for name,folder,sha in ITEMS:
        path=folder/'FUTURE-HOST-COMMAND-PLAN.json'
        assert ref(path)['sha256']==sha
        plan=json.loads(path.read_text());assert len(plan['commands'])==3
        verify(plan['inputs'])
        assert not Path(plan['fresh_output']).exists()
        plans.append((name,path,plan))
    initial_admission=reviewed.admission()
    logs=D/'logs';logs.mkdir(mode=0o700)
    results=[];leaves=[]
    for name,path,plan in plans:
        verify(plan['inputs']+supplement['headers']+supplement['tools'])
        admission=reviewed.admission()
        Path(plan['fresh_output']).mkdir(mode=0o700)
        leaf_rows=[]
        for leaf_index,command in enumerate(plan['commands']):
            verify(plan['inputs']+supplement['headers']+supplement['tools'])
            assert ref(path)['sha256']==next(item[2] for item in ITEMS if item[0]==name)
            admission=reviewed.admission()
            index=len(results);started_wall=time.time();started=time.monotonic()
            birth=None
            with (logs/(str(index)+'.stdout')).open('xb') as stdout,(logs/(str(index)+'.stderr')).open('xb') as stderr:
                child=subprocess.Popen(command['argv'],cwd=plan['cwd'],stdin=subprocess.DEVNULL,
                    stdout=stdout,stderr=stderr,start_new_session=True,close_fds=True,
                    env={'PATH':'/usr/bin:/bin','LC_ALL':'C','RUST_BACKTRACE':'0'})
                raw_stat=Path('/proc/'+str(child.pid)+'/stat').read_text()
                birth=dict(pid=child.pid,proc_stat_raw=raw_stat,
                    starttime_ticks=int(raw_stat[raw_stat.rfind(')')+2:].split()[19]),
                    process_group=os.getpgid(child.pid),session=os.getsid(child.pid),
                    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    observed_wall=time.time())
                while True:
                    pid,status,usage=os.wait4(child.pid,os.WNOHANG)
                    if pid:break
                    if time.monotonic()-started>=90:
                        os.killpg(child.pid,signal.SIGTERM)
                        try:child.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid,signal.SIGKILL);child.wait()
                        raise RuntimeError('own command timeout/direct child joined: '+str(index))
                    time.sleep(0.01)
                child.returncode=os.waitstatus_to_exitcode(status)
            try:os.killpg(child.pid,0);group_absent=False
            except ProcessLookupError:group_absent=True
            row=dict(index=index,leaf=name,leaf_index=leaf_index,purpose=command['purpose'],argv=command['argv'],
                pid=child.pid,birth=birth,streams_closed=stdout.closed and stderr.closed,started_wall=started_wall,elapsed=time.monotonic()-started,
                CPU_user=usage.ru_utime,CPU_system=usage.ru_stime,max_RSS_KiB=usage.ru_maxrss,
                returncode=child.returncode,direct_wait=True,group_absent=group_absent,
                admission=admission,stdout=ref(logs/(str(index)+'.stdout')),stderr=ref(logs/(str(index)+'.stderr')))
            results.append(row);leaf_rows.append(row)
            (D/'RESULTS.json').write_text(json.dumps(dict(status='RUNNING',initial_admission=initial_admission,results=results,completed_leaves=leaves),indent=2)+'\n')
            if child.returncode!=0 or not group_absent:raise RuntimeError('first batch failure: '+str(index))
        assert Path(leaf_rows[-1]['stdout']['path']).read_text()==plan['expected']['stdout']
        leaf=dict(leaf=name,status='PASS_FROZEN_LEAF_HOST',plan=ref(path),cases=plan['expected']['cases'],
            results=leaf_rows,scope=plan['effect_scope'],production_native_acceptance=False)
        leaves.append(leaf)
        (D/(name+'.RESULTS.json')).write_text(json.dumps(leaf,indent=2)+'\n')
    result=dict(status='PASS_F06_CONTEXT_RANGE_FOUR_LEAF_HOST',scope=__doc__,initial_admission=initial_admission,
        reviewed_admission_source=ref(EXPERT/'run_sealed.py'),sealed_batch=ref(D/'SEALED-BATCH-BINDINGS.json'),
        results=results,completed_leaves=leaves,
        limit='GCC9/Rust1.92 controlled-effect adapter HOST ABI only; no actual currentstack/reference/allocation/IRQ/IPC/mapping/native/default acceptance')
    (D/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],commands=len(results),leaves=len(leaves),cases=sum(x['cases'] for x in leaves),
        all_direct_waited=True,all_groups_absent=True,CPU_seconds=sum(x['CPU_user']+x['CPU_system'] for x in results),
        wall_seconds=sum(x['elapsed'] for x in results),max_child_RSS_KiB=max(x['max_RSS_KiB'] for x in results)),sort_keys=True))


if __name__=='__main__':
    try:main()
    except BaseException as error:
        (D/'FIRST-FAILURE.json').write_text(json.dumps(dict(error=repr(error),scope=__doc__),indent=2)+'\n')
        raise
