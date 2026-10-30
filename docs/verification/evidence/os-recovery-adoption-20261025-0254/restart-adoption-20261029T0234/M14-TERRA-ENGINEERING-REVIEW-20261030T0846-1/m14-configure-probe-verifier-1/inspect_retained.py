#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,pathlib
from verify_probe import map_value
profile=pathlib.Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-nonheld13-data32-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json')
pb=profile.read_bytes();assert hashlib.sha256(pb).hexdigest()=='e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3'
rows=[x for x in json.loads(pb)['readonly_config_and_eight_objects'] if x['container'].endswith('/tmp.resolve_MODULES_END/driver.ko')];assert len(rows)==1
b=pathlib.Path(rows[0]['host']).read_bytes();digest=hashlib.sha256(b).hexdigest();assert digest==rows[0]['sha256']
print('sha256='+digest);print('symbol='+f'0x{map_value(b):016x}')
