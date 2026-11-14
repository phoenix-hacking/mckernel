#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source metadata only. Default checks in memory; explicit --emit-request writes only
this folder's new request using exclusive creation. No workload namespaces.
"""
import argparse, hashlib, json
from pathlib import Path
D = Path(__file__).resolve().parent
TARGET = D / 'image-request.CURRENT290.ATTEMPT5.SOURCE-ONLY.NOT-RELEASED.json'

def reference(path):
    path=Path(path); raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def request_bytes():
    delta=json.loads((D.parent/'REQUEST-SUCCESSOR-EXACT-DELTA.SOURCE-ONLY.NOT-GRANTED.json').read_bytes())
    assert reference(delta['base']['path']) == delta['base']
    result=json.loads(Path(delta['base']['path']).read_bytes())
    for row in delta['replacements']:
        key=row['pointer'].removeprefix('/')
        assert '/' not in key and result[key] == row['before']
        result[key]=row['after']
    return (json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emit-request',action='store_true')
    args=parser.parse_args();raw=request_bytes()
    expected=json.loads((D/'PROSPECTIVE-REQUEST-REFERENCE.NOT-MATERIALIZED.json').read_bytes())
    row=dict(path=str(TARGET),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    assert row==expected
    if args.emit_request:
        with TARGET.open('xb') as stream:stream.write(raw)
        assert reference(TARGET)==expected
    print(json.dumps(dict(status='SOURCE_METADATA_ONLY_NOT_RELEASED',request=row,
                         materialized=args.emit_request,namespace_created=False),sort_keys=True))

if __name__=='__main__':main()
