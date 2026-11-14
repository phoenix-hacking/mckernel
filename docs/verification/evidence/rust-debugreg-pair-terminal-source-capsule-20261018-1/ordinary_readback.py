"""Conditional ordinary readback of the exact bounded observer raw five.

Unreadable or not-yet-created files are a pending observation, never permission
to rerun the observer or elevate privileges. This helper grants no cleanup.
"""
import importlib.util,json,os,resource
from pathlib import Path
P=Path(__file__).resolve().parent
SUMMARY=P/'readback_observer.py'
def module():
 sp=importlib.util.spec_from_file_location('ordinary_summary',SUMMARY);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def observe(m):
 paths=[m.OUTPUT/name for name in m.NAMES]
 missing=[name.name for name in paths if not os.access(name,os.R_OK)]
 if missing:return dict(status='PENDING_ORDINARY_READABILITY',files=missing,observer_replayed=False,cleanup_authorized=False)
 # read_all holds/checks stable descriptors and original hashes; summarize
 # cross-checks nonce, full observation/draft byte digests and finite projection.
 result=m.summarize(m.read_all())
 assert len(m.canonical(result))<=1048576
 return result
def main():
 resource.setrlimit(resource.RLIMIT_AS,(1<<30,1<<30));resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 print(json.dumps(observe(module()),sort_keys=True))
if __name__=='__main__':main()
