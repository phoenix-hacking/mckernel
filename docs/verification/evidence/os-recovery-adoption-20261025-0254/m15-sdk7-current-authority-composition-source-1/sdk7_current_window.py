"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure fixed-window metadata. No clock reads, owner import or execution authority.
"""
import copy
import hashlib
import json
from pathlib import Path
PARENT_WINDOW=dict(path='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-18-hour-window-1/parent-handoff/WINDOW.json',bytes=471,sha256='033e3d6667008fc2c1006f1b45954eda301782a5294857b20b57d3e45d8d004f')
ROOT_CUTOFF=dict(path='/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW18H-20261026-FIXED-CUTOFF-BINDING.json',bytes=952,sha256='2e1d3fa8338e51973cf0af5677e7e256259aff539adb164be0fb53240d834b35')
FIXED=[1793100290.0,882395.5689528405,897734.6960034363]
WINDOW_ID='new18h-20261026-bf8b8eb1832f4c94a0166f20a95642ea'
def need(ok,reason):
 if not ok:raise ValueError(reason)
def bound(ref):
 raw=Path(ref['path']).read_bytes();need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'fixed-parent-source-changed');return json.loads(raw)
def normalize(parent,proof):
 need(parent['window_id']==proof['window_id']==WINDOW_ID and parent['boot_id']==proof['boot_id'],'same-parent-window-and-boot')
 need(proof['fixed_cutoffs']==FIXED and parent['deadline_epoch']==FIXED[0] and proof['deadline_utc']=='2026-10-27T11:24:50Z','exact-root-fixed-cutoffs')
 need(proof['thread_id']=='01a170fb-57c3-7ab3-862d-8005bef92a63' and proof['credit_run_id']=='7f4af94a83b14cc08f97401f5891d965','same-goal-and-credit-run')
 need(parent['monotonic_deadline']>=FIXED[1] and parent['boot_deadline']>=FIXED[2],'root-boundary-must-never-extend-parent')
 result=copy.deepcopy(parent)
 result.update(status='FIXED_PARENT_BOUNDARY_SOURCE_METADATA_NO_RUNTIME_AUTHORITY',
  start_epoch=FIXED[0]-64800,start_monotonic=FIXED[1]-64800,start_boot=FIXED[2]-64800,
  deadline_epoch=FIXED[0],monotonic_deadline=FIXED[1],boot_deadline=FIXED[2],
  deadline_utc='2026-10-27T11:24:50Z',parent_window_provenance=PARENT_WINDOW,earliest_parent_cutoff_proof=ROOT_CUTOFF)
 return result
def load_window():return normalize(bound(PARENT_WINDOW),bound(ROOT_CUTOFF))
def validate_window(window):
 need(window==load_window(),'exact-earliest-bound-parent-window-required')
 return window
