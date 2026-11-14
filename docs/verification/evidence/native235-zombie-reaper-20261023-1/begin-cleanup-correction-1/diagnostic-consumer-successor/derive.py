"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private additive schema successor; never executes a workload.
"""
from pathlib import Path
import hashlib,json
F=Path(__file__).resolve().parent
N=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/diagnostic-consumer-successor')
ROOT=Path('/home/holden/mckernel')
B=F.parent
sources={'consumer':B/'consumer/mcctrl_process.rs','provider':B/'provider/smp_application.rs'}
def ref(p):
 s=p.stat();return dict(path=str(p),size=s.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=s.st_mode)
refs={k:ref(p) for k,p in sources.items()}
helper='''

# Explicit source-bound BEGIN_CLEANUP schema; absent field preserves legacy.
BEGIN_CLEANUP_PROFILE_ID = "begin-cleanup-intent-real-ack-retirement-v1"
BEGIN_CLEANUP_SOURCE_REFS = SOURCE_REFS_LITERAL

def _begin_cleanup_enabled(manifest):
    return "cleanup_profile" in manifest

def _validate_cleanup_profile(profile, modules):
    _keys(profile, ("schema_version", "id", "consumer", "provider", "modules"))
    _need(type(profile["schema_version"]) is int and profile["schema_version"] == 1 and
          profile["id"] == BEGIN_CLEANUP_PROFILE_ID, "BEGIN cleanup schema")
    for name in ("consumer", "provider"):
        _need(profile[name] == BEGIN_CLEANUP_SOURCE_REFS[name], "BEGIN source identity")
        _ref(profile[name], "BEGIN " + name)
    _need(type(modules) is list and len(modules)==3 and profile["modules"] == modules, "BEGIN module tuple differs")
    # The ordinary manifest validator checks each complete module reference,
    # including actual bytes. Null/future descriptors cannot become authority.
    return dict(profile)

def _check_begin_cleanup(serial, prefix, terminal):
    """Intent is not ACK. Match owner identity, not cross-namespace tokens.

    ACK may precede intent logging; close may set abandoned=1. Retirement
    queries are issued only after successful cleanup ACK. The target terminal
    must precede its own actual retirement, independently of any child.
    """
    owner = re.fullmatch(r"os=(\\d+) generation=(\\d+) pid=(\\d+)", prefix)
    _need(owner is not None, "BEGIN owner identity")
    pid = owner.group(3)
    intents=[]; acknowledgements=[]; attempts=[]
    patterns = (
        ("application_process=cleanup_requested ", r"intent_errno=(-?\\d+)", intents),
        ("application cleanup ACK ", r"token=(\\d+) errno=(-?\\d+) abandoned=([01])", acknowledgements),
        ("application retirement ", r"token=(\\d+) errno=(-?\\d+)", attempts),
    )
    for position,line in enumerate(serial.splitlines()):
        for marker,suffix,rows in patterns:
            if marker not in line or not re.search(r"pid="+pid+r"\\b", line):
                continue
            match=re.search(re.escape(marker)+prefix+" "+suffix+r"\\s*$",line)
            _need(match is not None, "malformed/wrong-generation BEGIN lifecycle")
            rows.append((position, *map(int,match.groups())))
    _need(len(intents)==1 and intents[0][1]==0, "missing/failed BEGIN intent")
    _need(len(acknowledgements)==1, "missing/duplicate real cleanup ACK")
    ack=acknowledgements[0]
    _need(0<ack[1]<2**64 and ack[2]==0, "real cleanup ACK failure/token")
    _need(1<=len(attempts)<=12 and len({a[1] for a in attempts})==len(attempts), "BEGIN retirement attempts")
    _need(all(0<a[1]<2**64 and a[0]>terminal and a[0]>ack[0] for a in attempts), "BEGIN premature retirement/token")
    _need(all(a[2]==-11 for a in attempts[:-1]) and attempts[-1][2]==0, "BEGIN retirement result")
    return {"entry_token":ack[1],"query_tokens":[a[1] for a in attempts]}

_legacy_cleanup_validate_manifest = _validate_manifest
def _validate_manifest(obj):
    if "cleanup_profile" not in obj:
        return _legacy_cleanup_validate_manifest(obj)
    base=dict(obj);profile=base.pop("cleanup_profile")
    validated=_legacy_cleanup_validate_manifest(base)
    validated["cleanup_profile"]=_validate_cleanup_profile(profile,validated["modules"])
    return validated
'''.replace('SOURCE_REFS_LITERAL',repr(refs))
origins={
 'native':Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/native-runtime-ready-1/native_diagnostic.py'),
 'v3':Path('/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/runtime-first-restoration-1/native_diagnostic.py')}
rows=[]
for name,path in origins.items():
 t=path.read_text()
 old='''    for pattern in (r"application retirement " + prefix + r" token=\\d+ errno=0\\b",
                    r"application_process=release " + prefix + r" cleanup_errno=0\\b",
                    *[r"application procfs " + op + " " + prefix + " tid=" + schedules[0] + r"\\b"
                      for op in ("published", "deleted")]):'''
 new='''    lifecycle_patterns = () if _begin_cleanup_enabled(manifest) else (
        r"application retirement " + prefix + r" token=\\d+ errno=0\\b",
        r"application_process=release " + prefix + r" cleanup_errno=0\\b")
    for pattern in (*lifecycle_patterns,
                    *[r"application procfs " + op + " " + prefix + " tid=" + schedules[0] + r"\\b"
                      for op in ("published", "deleted")]):'''
 assert t.count(old)==1;(t:=t.replace(old,new))
 assert t.count('_check_syscall_trace(serial, prefix)')==2
 t=t.replace('_check_syscall_trace(serial, prefix):','_check_syscall_trace(serial, prefix, begin_cleanup=False):').replace('_check_syscall_trace(serial, prefix)\n','_check_syscall_trace(serial, prefix, _begin_cleanup_enabled(manifest))\n')
 old='''    for marker in ("application retirement ", "application_process=release "):
        positions = [i for i, line in enumerate(serial.splitlines()) if marker in line]
        _need(positions and all(i > exit_position for i in positions), "retirement precedes terminal exit")'''
 assert t.count(old)==1
 t=t.replace(old,'''    if begin_cleanup:
        _check_begin_cleanup(serial, prefix, exit_position)
    else:
'''+ '\n'.join('    '+line for line in old.splitlines()))
 if name=='native':
  t=t.replace('def _pair_trace(serial,pid,cpu):','def _pair_trace(serial,pid,cpu,begin_cleanup=False):')
  needle='    # The retained broker retries EAGAIN with a fresh retirement Exchange'
  assert t.count(needle)==1
  t=t.replace(needle,'''    if begin_cleanup:
        _check_begin_cleanup(serial,prefix,terminal)
        return
'''+needle)
  old='''        for pattern in (r"application retirement "+prefix+r" token=(\\d+) errno=0\\b",r"application_process=release "+prefix+r" cleanup_errno=0\\b",*[r"application procfs "+op+" "+prefix+r" tid="+str(a["pid"])+r"\\b" for op in ("published","deleted")]):'''
  assert t.count(old)==1
  t=t.replace(old,'''        lifecycle_patterns=() if _begin_cleanup_enabled(manifest) else (r"application retirement "+prefix+r" token=(\\d+) errno=0\\b",r"application_process=release "+prefix+r" cleanup_errno=0\\b")
        for pattern in (*lifecycle_patterns,*[r"application procfs "+op+" "+prefix+r" tid="+str(a["pid"])+r"\\b" for op in ("published","deleted")]):''')
  t=t.replace('_pair_trace(serial,a["pid"],i)','_pair_trace(serial,a["pid"],i,_begin_cleanup_enabled(manifest))')
  t=t.replace("'application_process=release ','application procfs '","'application_process=release ','application_process=cleanup_requested ','application cleanup ACK ','application procfs '")
 t+=helper
 dest=N/name/'native_diagnostic.py';dest.write_text(t)
 pub=F/(name+'_native_diagnostic.py');pub.write_bytes(dest.read_bytes())
 rows.append(dict(role=name,origin=ref(path),private=ref(dest),publication=ref(pub)))
profile=dict(schema_version=1,id='begin-cleanup-intent-real-ack-retirement-v1',**refs,modules=None)
(F/'CLEANUP-PROFILE.TEMPLATE.NOT-RELEASED.json').write_text(json.dumps(profile,indent=2)+'\n')
(F/'SOURCE-MAP.json').write_text(json.dumps(dict(scope=__doc__.splitlines()[0],status='SOURCE_ONLY_NOT_TESTED_NOT_RELEASED',sources=rows,profile_fill='After actual SDK acceptance only: replace modules null with exact normalized manifest modules (three complete actual file refs). Consumer/provider refs immutable. Unknown descriptors refuse manifest validation.'),indent=2)+'\n')
