"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure retained-data replay; no workload, root, compiler, mutation or acceptance.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
D=Path(__file__).resolve().parent
facts=json.loads((D/'EXACT-SOURCE-DATA-DIAGNOSIS.json').read_bytes())

def checked_read(binding):
    p=Path(binding['path']);b=p.read_bytes()
    if len(b)!=binding['bytes'] or hashlib.sha256(b).hexdigest()!=binding['sha256']:
        raise ValueError('frozen source/capture binding changed: '+str(p))
    return b

def load(binding,name):
    checked_read(binding)
    spec=importlib.util.spec_from_file_location(name,binding['path'])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

sys.path.insert(0,str(Path(facts['actual_frozen_consumer']['path']).parent))
original=load(facts['actual_frozen_consumer'],'p12_original_frozen')
actual_native=load(facts['actual_unchanged_pair_checker'],'p12_actual_native')
successor=load(facts['successor'],'p12_uart_successor')
manifest=json.loads(checked_read(facts['manifest']))
serial=checked_read(facts['raw_serial']).decode('ascii')
try:
    original.check_long_session(manifest,dict(serial=serial),actual_native._pair_body)
except original.LongSessionError as error:
    if str(error)!='trace exact bytes/cap':raise
    original_error=str(error)
else:raise ValueError('original failure not reproduced')
# Actual retained raw CRLF capture, actual unchanged strict per-pair checker.
metrics=successor.check_long_session(manifest,dict(serial=serial),actual_native._pair_body)
print(json.dumps(dict(scope=facts['scope'],status='OFFLINE_PROTOCOL_REPLAY_ONLY',original_failure_preserved=original_error,successor_protocol_metrics=metrics,raw_serial_sha256=facts['raw_serial']['sha256'],native_acceptance=False,physical_retirement_accepted=False),sort_keys=True))
