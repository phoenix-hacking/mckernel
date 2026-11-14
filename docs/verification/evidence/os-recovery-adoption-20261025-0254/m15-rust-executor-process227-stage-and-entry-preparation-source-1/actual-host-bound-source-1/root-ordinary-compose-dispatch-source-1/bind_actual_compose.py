"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root subsequent DATA-only invocation of exact qualifiedbinder from actualcomposeSHA.
No compose/compiler/payload/native operation; never invent an actualreceipt hash.
"""
from pathlib import Path
import hashlib,json,os
D=Path(__file__).resolve().parent;P=D.parent
profile=json.loads((D/'PROFILE.NOT-GRANTED.json').read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
result=json.loads((Path(profile['capture_root'])/'ACTUAL-COMPOSE-RESULT.json').read_text())
assert result['status']=='ACTUAL_ONE_46D_COMPOSE_ZERO_JOINED_FULL_RECEIPT_NOT_NATIVE'
receipt=Path(profile['actual_receipt_path']);actual=ref(receipt);assert actual==result['receipt']
assert ref(profile['actual_overlay_path'])==result['overlay']
binder=P/'bind_process227_collector.py';assert ref(binder)['sha256']=='941ad7697bdb9d20d109183ab611a2547d4306b127612e6d0d8c9158274695c9'
argv=['/usr/bin/python3','-B',str(binder),'--bind-existing-root-composition','--receipt',str(receipt),'--receipt-sha256',actual['sha256']]
with (D/'ROOT-ACTUAL-BINDER-LITERAL-ARGV.json').open('x') as f:json.dump(dict(scope=__doc__.splitlines()[0],argv=argv,actual_compose_result=ref(Path(profile['capture_root'])/'ACTUAL-COMPOSE-RESULT.json'),actual_receipt=actual,native_authority=None),f,indent=2);f.write('\n')
os.execv(argv[0],argv)
