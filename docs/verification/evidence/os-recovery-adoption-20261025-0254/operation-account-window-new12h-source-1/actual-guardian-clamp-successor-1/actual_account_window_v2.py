"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only explicit actual-guardian clamp successor. No operation/outer-control authority.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'actual_account_window.py'
BASE_SHA256='8bf26bae56a019876c6a1463945733c85be5016d21ac5f6f955c29fd131a8cbe'
RECEIPT_SHA256='8a33c90172e4fea5f3d1541758fef205a5e6c24440875ebbfd45f6512c9021f9'
PACKET='01b50e2ee16444bef512e6732a4f21d5169e8ac5080d02eca7886002a1cd853a'
JOURNAL=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/armed-controller/journal.json')
CUTOFFS=(1793165769.0,947874.5689514667,963213.6960030915)

def need(ok,why):
 if not ok:raise ValueError(why)

need(hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA256,'reviewed predecessor guard drift')
spec=importlib.util.spec_from_file_location('operation_account_window_reviewed_v1',BASE)
v1=importlib.util.module_from_spec(spec);spec.loader.exec_module(v1)
check_account_state=v1.check_account_state
available_balance=v1.available_balance
amount=v1.amount
THREAD,RUN,BUDGET,BOOT=v1.THREAD,v1.RUN,v1.BUDGET,v1.BOOT

def load_receipt():
 raw=(HERE/'ACTUAL-GUARDIAN-VERIFIED.json').read_bytes()
 need(hashlib.sha256(raw).hexdigest()==RECEIPT_SHA256,'actual parent guardian receipt drift')
 receipt=json.loads(raw)
 need(receipt['status']=='PASS_MODEL_DEADLINE_GUARDIAN_LIVE_LEASE_HELD'
      and receipt['thread_id']==THREAD and receipt['lease_observed_held'] is True
      and receipt['native_release'] is False and receipt['guardian']['pid']==1619833
      and receipt['guardian']['start']=='92037917'
      and receipt['journal']==str(JOURNAL),'actual guardian receipt identity')
 return receipt

def load_window():
 result=v1.load_window()
 result.update(deadline_epoch=CUTOFFS[0],monotonic_deadline=CUTOFFS[1],boot_deadline=CUTOFFS[2],
  operation_guardian_receipt_sha256=RECEIPT_SHA256,operation_guardian_packet_sha256=PACKET)
 return result

def validate_guardian(journal,receipt,observed):
 need(receipt==load_receipt(),'exact parent guardian receipt')
 need(observed is not None and observed['pid']==receipt['guardian']['pid']
      and observed['start']==receipt['guardian']['start'] and observed['state']!='Z',
      'actual parent guardian live birth')
 need(journal['packet_sha256']==PACKET and journal['boot_id']==BOOT
      and journal['credit_run_id']==RUN and journal['credit_started'] is True
      and journal['initial_prepaid_guard'] is True
      and journal['replacement_watcher_pid']==1616666
      and journal['replacement_watcher_start']=='92001383'
      and not journal.get('transition_hold') and not journal.get('stop_intent')
      and not journal.get('deadline_stop_sent'), 'current parent guardian identity or hold')
 cutoffs=(journal['deadline'],journal['finite_watcher_monotonic_deadline'],journal['boot_deadline'])
 need(all(type(v) in (int,float) and math.isfinite(v) and 0<v<=limit
          for v,limit in zip(cutoffs,CUTOFFS)),'guardian must only tighten inherited cutoffs')
 need(journal['last_action']=='WAIT_EXISTING_CREDIT_WATCHER','guardian must remain waiting resident watcher')
 return tuple(min(a,b) for a,b in zip(CUTOFFS,cutoffs))

def observe_guardian(pid):
 try:fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:return None
 need(len(fields)>=20,'readable guardian process identity')
 return dict(pid=pid,start=fields[19],state=fields[0])

def current_cutoffs():
 receipt=load_receipt()
 return validate_guardian(json.loads(JOURNAL.read_bytes()),receipt,
                          observe_guardian(receipt['guardian']['pid']))

def check_window(window,clocks,boot_id,cutoffs=CUTOFFS):
 need(window==load_window(),'exact clamped actual window')
 v1.check_window(v1.load_window(),clocks,boot_id)
 need(len(cutoffs)==3 and all(type(v) in (int,float) and math.isfinite(v) and 0<v<=limit
                             for v,limit in zip(cutoffs,CUTOFFS)),'only stricter inherited cutoffs')
 need(all(a<b for a,b in zip(clocks,cutoffs)),'actual guardian inherited cutoff')
 return clocks

def guard():
 clocks=[v1.time.time(),v1.time.monotonic(),v1.time.clock_gettime(v1.time.CLOCK_BOOTTIME)]
 check_window(load_window(),clocks,Path('/proc/sys/kernel/random/boot_id').read_text().strip(),current_cutoffs())
 check_account_state(json.loads(v1.STATE.read_bytes()),clocks[0])
 return clocks
