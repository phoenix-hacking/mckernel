#!/usr/bin/env python3
"""Record the reviewed rescue protocol; actual execution is separately gated."""
import argparse,json
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--case',required=True); p.add_argument('--collector',type=Path,required=True); p.add_argument('--fixture',type=Path,required=True); p.add_argument('--attempt-root',type=Path,required=True); a=p.parse_args()
 if a.case not in ('control','stopped-rescue') or a.attempt_root.exists(): raise ValueError('fresh reviewed case')
 a.attempt_root.mkdir(mode=0o700)
 result={'case':a.case,'status':'SOURCE_ONLY_NOT_EXECUTED','application_acceptance':False,'backend_enabled':False,'required_events':['READY','STOP_ARMED','raw-stop-4991','leader-zombie','grandchild-adopted','grandchild-zombie','SIGTERM','SIGCONT','ECHILD']}
 (a.attempt_root/'rescue-report.json').write_text(json.dumps(result,sort_keys=True)+'\n'); return 0
if __name__=='__main__': raise SystemExit(main())
