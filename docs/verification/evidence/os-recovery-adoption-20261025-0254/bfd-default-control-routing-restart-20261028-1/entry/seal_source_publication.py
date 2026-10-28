"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root data-only sealing after actual fetched source/config publication; no live gates.
"""
from pathlib import Path
import argparse,hashlib,json
D=Path(__file__).resolve().parent

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--publication',type=Path,required=True);a.add_argument('--publication-sha256',required=True);q=a.parse_args();r=ref(q.publication);assert r['sha256']==q.publication_sha256
 pub=json.loads(q.publication.read_bytes());assert pub['runtime_authority'] is None and pub['status'].startswith('PASS_FETCHED')
 b=json.loads((D/'ENTRY-BINDINGS.json').read_bytes());b['source_publication']=r
 expected=list(b['static_refs'].values())+[b['observer_source'],b['guard_facade'],b['guard_configuration'],b['finite_verifier'],b['capture_source'],b['publisher_source']]
 rows={x['actual']['path']:x['actual'] for x in pub['rows']}
 for value in expected:assert rows[value['path']]==ref(value['path'])==value
 with (D/'SEALED-ENTRY-BINDINGS.json').open('x') as f:json.dump(b,f,indent=2);f.write('\n')
 print(json.dumps(dict(status='SOURCE_CONFIG_PUBLICATION_BOUND_NO_RUNTIME_GRANT',sealed=ref(D/'SEALED-ENTRY-BINDINGS.json'))))
