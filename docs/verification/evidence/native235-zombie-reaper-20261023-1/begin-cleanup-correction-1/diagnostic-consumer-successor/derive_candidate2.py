"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import json,hashlib
F=Path(__file__).resolve().parent;D=F/'candidate2';D.mkdir(exist_ok=True)
N=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/diagnostic-consumer-successor/candidate2')
CASES=('P-M06-01-process-exec-wait-235B','P-M01-02-child-SIGTERM-and-exec-recovery-227B')
helper='''

BEGIN_PROCESS_CASES = CASES_LITERAL

def _begin_process_case(manifest):
    return _begin_cleanup_enabled(manifest) and manifest["case_id"] in BEGIN_PROCESS_CASES

def _audit_begin_children(serial, prefix):
    """Return a parent projection only after auditing every observed child row.

    Child authority is a positive RET to a matched parent clone(56), plus real
    same-generation procfs publication. A child can run before the parent RET
    log. A SIGTERM-cancelled child need not emit exit_group; every sampled
    ordinary delivery still needs its actual return and valid optional route.
    """
    owner=re.fullmatch(r"os=(\\d+) generation=(\\d+) pid=(\\d+)",prefix)
    _need(owner is not None,"process trace parent identity")
    os_id,generation,parent=map(int,owner.groups())
    suffixes={"delivered":r"worker=(\\d+) delivery=(\\d+) cpu=(\\d+) number=(\\d+)",
              "returned":r"worker=(\\d+) delivery=(\\d+) cpu=(\\d+) value=(-?\\d+)",
              "return_route":r"worker=(\\d+) delivery=(\\d+) launcher_cpu=(-?\\d+) guest_cpu=(\\d+)"}
    groups={};row_pids={}
    for position,line in enumerate(serial.splitlines()):
        for name,suffix in suffixes.items():
            marker="application_syscall="+name+" "
            if marker not in line:continue
            m=re.search(re.escape(marker)+r"os=(\\d+) generation=(\\d+) pid=(\\d+) "+suffix+r"\\s*$",line)
            _need(m is not None,"malformed process syscall row")
            os_seen,gen_seen,pid,worker,delivery,a,b=map(int,m.groups())
            _need((os_seen,gen_seen)==(os_id,generation) and pid>0 and 0<worker<2**64 and 0<delivery<2**64,"foreign process syscall identity")
            records=groups.setdefault(pid,{k:{} for k in suffixes});key=(worker,delivery)
            _need(key not in records[name],"duplicate process syscall row")
            records[name][key]=((a,b),position);row_pids[position]=pid
    _need(parent in groups,"missing process parent trace")
    pd,pr=groups[parent]["delivered"],groups[parent]["returned"]
    children={}
    for key,((cpu,number),position) in pd.items():
        if number!=56 or key not in pr:continue
        (retcpu,value),retpos=pr[key]
        _need(retcpu==cpu==0 and position<retpos,"parent clone correspondence")
        if value<=0:continue
        _need(value!=parent and value not in children,"duplicate/parent clone child")
        children[value]=position
    _need(set(groups)<={parent,*children},"unlinked child syscall PID")
    for child,clone_position in children.items():
        # A child may be cancelled before its first sampled syscall; its
        # provider publication must still identify the clone return exactly.
        publication=[]
        for position,line in enumerate(serial.splitlines()):
            if "application procfs published " not in line or not re.search(r"pid="+str(child)+r"\\b",line):continue
            m=re.search(r"application procfs published os="+str(os_id)+r" generation="+str(generation)+r" pid="+str(child)+r" tid="+str(child)+r"\\s*$",line)
            _need(m is not None,"child procfs identity")
            publication.append(position)
        _need(len(publication)==1 and publication[0]>clone_position,"missing/duplicate child publication")
        if child not in groups:continue
        delivered,returned,routes=(groups[child][k] for k in suffixes)
        _need(delivered and set(routes)<=set(returned)<=set(delivered),"child syscall correspondence")
        terminals={k for k,(row,_) in delivered.items() if row[1] in (60,231)}
        _need(len(terminals)<=1 and set(returned)==set(delivered)-terminals,"child ordinary RET coverage")
        terminal=delivered[next(iter(terminals))][1] if terminals else None
        workers={}
        for key,((cpu,number),begin) in delivered.items():
            _need(cpu==0 and begin>publication[0],"child CPU/publication order")
            if key in terminals:continue
            (retcpu,_),end=returned[key]
            _need(retcpu==0 and begin<end and (terminal is None or end<terminal),"child syscall/terminal order")
            slot=0
            if key in routes:
                (launcher,guest),where=routes[key]
                _need(launcher==1 and guest==0 and begin<where<end,"child route identity/order")
                slot=launcher
            _need(workers.setdefault(key[0],slot)==slot,"child worker route changed")
    parent_view=[line for position,line in enumerate(serial.splitlines()) if position not in row_pids or row_pids[position]==parent]
    return "\\n".join(parent_view), sorted(children)
'''.replace('CASES_LITERAL',repr(CASES))
rows=[]
for name in ('native','v3'):
 src=F/(name+'_native_diagnostic.py');s=src.read_text()
 s=s.replace('begin-cleanup-intent-real-ack-retirement-v1','begin-cleanup-real-ack-parent-clone-v2')
 s=s.replace('"consumer", "provider", "modules"))','"consumer", "provider", "modules", "child_trace_cases"))')
 needle='    for name in ("consumer", "provider"):'
 assert s.count(needle)==1;s=s.replace(needle,'    _need(profile["child_trace_cases"] == list(BEGIN_PROCESS_CASES), "BEGIN child trace case scope")\n'+needle)
 s=s.replace('def _check_syscall_trace(serial, prefix, begin_cleanup=False):','def _check_syscall_trace(serial, prefix, begin_cleanup=False, child_domain=False):')
 needle='    suffixes = {\n        "delivered":'
 assert s.count(needle)==1;s=s.replace(needle,'    if child_domain:\n        serial, _ = _audit_begin_children(serial, prefix)\n'+needle)
 s=s.replace('_check_syscall_trace(serial, prefix, _begin_cleanup_enabled(manifest))','_check_syscall_trace(serial, prefix, _begin_cleanup_enabled(manifest), _begin_process_case(manifest))')
 s+=helper
 target=N/name/'native_diagnostic.py';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(s)
 pub=D/(name+'_native_diagnostic.py');pub.write_bytes(target.read_bytes())
 rows.append({'role':name,'candidate1_path':str(src),'private_path':str(target),'publication_path':str(pub),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'size':target.stat().st_size})
p=json.loads((F/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json').read_text());p['id']='begin-cleanup-real-ack-parent-clone-v2';p['child_trace_cases']=list(CASES)
(D/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json').write_text(json.dumps(p,indent=2)+'\n')
(D/'SOURCE-MAP.json').write_text(json.dumps({'scope':__doc__,'status':'SOURCE_ONLY_NOT_TESTED_NOT_RELEASED','sources':rows,'candidate1_whole_join':str(F/'WHOLE-JOIN.json'),'failure_family':'candidate1 runtime blocked by observed child syscall foreign-PID rejection; candidate2 first bounded correction'},indent=2)+'\n')
