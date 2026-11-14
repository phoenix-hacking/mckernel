"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root read-only current holder/container joins plus unchanged v2 physical observer.
No workload replay, termination, cleanup or artifact/native acceptance.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os
helper=Path(__file__).resolve().parent/'capture_resources.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='1b206989e8739bb212e212bbbe6df52e9d363f4f11c75f3ca4ad1a62ddde0774'
spec=importlib.util.spec_from_file_location('current110_exact_resource_reader',helper)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
def check(root):
 root=Path(root);assert root.is_absolute() and root.parent==c.E and root.name.startswith('ROOT-')
 guard=c.load(c.GUARD,c.GUARD_SHA,'current110_postbuild_exact_v2_guard');guard.guard()
 ready=c.read(root/'HOLDER/HOLDER.READY.json');joined=c.read(root/'HOLDER/RUNNER.JOINED.json');local=c.read(root/'HOLDER/BUILD-LOCAL-TERMINAL.json')
 tool=c.read(root/'ROOT-ACTUAL-HOLDER-TOOL-RESULT.json')
 # Root retains its actual tool result; this reader does not manufacture a join.
 assert tool['joined'] is True and tool['exit_code']==0 and tool['terminal_tool_result']['exit_code']==0
 assert joined['joined'] is True and joined['returncode']==0 and local['joined'] is True and local['container_terminal_or_no_launch'] is True
 assert ready['holder']==local['holder']
 for row in [ready['holder'],dict(pid=joined['pid'],starttime=joined['starttime'])]:
  assert not Path('/proc',str(row['pid'])).exists(),'known numeric holder/runner present; do not infer retirement from thread completion'
 terminal=c.read(root/'OUTPUT/terminal.json');cid=(root/'OUTPUT/container.cid').read_text().strip()
 assert terminal['container']==cid and len(cid)==64 and terminal['returncode']==0
 assert terminal['state']['Running'] is False and terminal['state']['Pid']==0 and terminal['state']['ExitCode']==0 and not terminal['state']['OOMKilled']
 observer=c.load(c.OBSERVER,c.OBSERVER_SHA,'current110_postbuild_reused_v2_current_observer')
 physical=observer.observe()
 return dict(scope=c.SCOPE,status='CURRENT110_POSITIVE_BUILD_JOINS_AND_CURRENT_PHYSICAL_PENDING_ROOT_INDEPENDENT_ACCEPTANCE',
  guard=c.ref(c.GUARD),observer=c.ref(c.OBSERVER),observed_clocks=guard.guard(),physical=physical,
  holder_ready=c.ref(root/'HOLDER/HOLDER.READY.json'),runner_join=c.ref(root/'HOLDER/RUNNER.JOINED.json'),
  holder_tool_result=c.ref(root/'ROOT-ACTUAL-HOLDER-TOOL-RESULT.json'),container_terminal=c.ref(root/'OUTPUT/terminal.json'),
  native_acceptance=False,artifact_acceptance=False)
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--admission',required=True);args=parser.parse_args()
 print(json.dumps(check(Path(args.admission)),indent=2))
