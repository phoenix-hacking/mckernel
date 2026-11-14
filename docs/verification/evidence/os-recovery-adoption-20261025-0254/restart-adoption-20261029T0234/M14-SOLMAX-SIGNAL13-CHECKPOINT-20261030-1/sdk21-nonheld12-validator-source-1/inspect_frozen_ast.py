#!/usr/bin/env python3
"""Read-only exact frozen source/node hash diagnostic; functional OS work only.
No imported adapter, fixture, subprocess, ELF, output writes or node execution.
"""
import ast, hashlib, json, sys
from pathlib import Path

PROFILE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-nonheld12-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json')
EXPECTED='c88825ef2e2cfbf28e8e244c2010748c493bdb0924fc333a69b79eb80d627d69'
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
    raw=PROFILE.read_bytes(); assert sha(raw)==EXPECTED
    profile=json.loads(raw); frozen=profile['original_oracle_and_validation']
    template=Path(frozen['validator_template']['path']).read_bytes()
    assert sha(template)==frozen['validator_template']['sha256']
    assert json.loads(template)['validator_nodes']==frozen['frozen_nodes']
    output=[]
    for row in frozen['frozen_nodes']:
        raw=Path(row['source']['path']).read_bytes(); text=raw.decode()
        source_ok=(len(raw)==row['source']['bytes'] and sha(raw)==row['source']['sha256'])
        nodes=[n for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==row['name']]
        assert len(nodes)==1
        node=nodes[0]; seg=sha(ast.get_source_segment(text,node).encode())
        digest=sha(ast.dump(node,include_attributes=False).encode())
        output.append({'name':row['name'],'source_sha256':sha(raw),'source_ok':source_ok,
          'line_span_ok':(node.lineno,node.end_lineno)==(row['first_line'],row['last_line']),
          'source_segment_sha256':seg,'expected_segment_sha256':row['source_segment_sha256'],
          'segment_ok':seg==row['source_segment_sha256'],'AST_sha256':digest,
          'expected_AST_sha256':row['AST_sha256'],'AST_ok':digest==row['AST_sha256']})
    exe=Path(sys.executable).resolve(); binary=exe.read_bytes()
    print(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing',
      'runtime_version':sys.version,'runtime_executable':str(exe),'runtime_bytes':len(binary),'runtime_sha256':sha(binary),
      'profile_sha256':EXPECTED,'nodes':output},indent=2))
    return 0 if all(r['source_ok'] and r['line_span_ok'] and r['segment_ok'] and r['AST_ok'] for r in output) else 1
if __name__=='__main__': sys.exit(main())
