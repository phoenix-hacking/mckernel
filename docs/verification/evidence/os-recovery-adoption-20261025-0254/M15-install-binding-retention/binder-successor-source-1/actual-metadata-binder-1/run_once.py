from pathlib import Path
import json,hashlib,signal,importlib.util
D=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('h',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,h.stop)
r=json.loads((D/'REQUEST.json').read_text())
for key in ('helper','test'):
 ref=r[key];raw=Path(ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
signal.setitimer(signal.ITIMER_REAL,51)
joined=h.owned_capture(dict(argv=r['argv'],purpose=r['scope']+' One metadata-only private-source binding; no generated source execution.'),D,45,lambda:None)
h.write(D/'WHOLE-JOIN.json',joined);signal.setitimer(signal.ITIMER_REAL,0)
assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None and not joined['timed_out']
print(json.dumps(dict(status='PASS_METADATA_ONLY_BINDING',returncode=joined['returncode'],seconds=joined['seconds'])))
