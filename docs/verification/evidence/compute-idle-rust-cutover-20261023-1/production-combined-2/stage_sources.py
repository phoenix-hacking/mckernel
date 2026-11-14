#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only exact two-postimage increment over the prior coherent idle+memory tree.
"""
from pathlib import Path
import hashlib

D=Path(__file__).resolve().parent
P=D.parent
OLD=P/'production-consumer-1/materialize_successor.py'
OUT=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2')

def main():
    data=OLD.read_bytes()
    assert hashlib.sha256(data).hexdigest()=='b176a876537f9c81137713b3697fadcbf29e7c7aed10a3900ffbe9404c61dc54'
    s=data.decode().replace('THREE canonical postimages only.','TWO latest canonical memory postimages over prior idle+memory source.')
    s=s.replace("OUT = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-consumer-1')",'OUT = Path('+repr(str(OUT))+')')
    s=s.replace("BASE = Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')","BASE = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/memory-combined-preparation-1')")
    s=s.replace("SOURCE = BASE / 'source-materialization-1/materialized-source'","SOURCE = BASE / 'materialized-source'")
    a=s.index('AUTHORITY = ');b=s.index('MAX_GROWTH = ',a)
    s=s[:a]+'''AUTHORITY = REPO / 'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/phys-to-virt-callback-1/CANONICAL-INTEGRATION.json'
BASE_CANONICAL_SHA = 'db4f6a3b25f5b483cc2a34cc06efa374396cfdadfb074162e81aadeaf02e9240'
POST = {'arch/x86_64/kernel/memory.c': '95bb6a4a916a802e98eb9f7eac98eef990d6f75a3e42b06f29ac0a73ef2a452b',
        'kernel/rust/x86_memory_helpers.rs': '689b9741821609a7c2e3aadb8cd46b0dbc57948090b38758f0b3eb120a5297fb'}
'''+s[b:]
    s=s.replace("(BASE / 'thin-inputs.json')","(BASE / 'source-inputs.json')")
    a=s.index("    need(authority['decision']");b=s.index('    document = copy.deepcopy(baseline)',a)
    s=s[:a]+'''    need(authority['decision'] == 'PASS_M14_CALLBACK_SOURCE_AND_SELECTED_ABI_LINK'
         and {path:row['sha256'] for path,row in authority['postimages'].items()} == POST,
         'actual reviewed latest two-file canonical integration')
'''+s[b:]
    s=s.replace('three_source_delta=changed','latest_memory_two_source_delta=changed')
    s=s.replace("'mckernel.idle-orchestration-production-consumer-thin-inputs.v1'","'mckernel.m14-combined-production-thin-inputs.v1'")
    s=s.replace("document['idle_orchestration_overlay'] = derivation","document['latest_memory_callback_overlay'] = derivation")
    s=s.replace("(BASE / 'source-materialization-1/materialization-journal.jsonl')","(BASE / 'materialization-journal.jsonl')")
    s=s.replace('PASS_COHERENT_THREE_POSTIMAGE_SOURCE_MATERIALIZATION_ONLY','PASS_COHERENT_LATEST_FIVE_POSTIMAGE_SOURCE_MATERIALIZATION_ONLY')
    with (D/'materialize_generated.py').open('x') as f:f.write(s)
    exec(compile(s,str(D/'materialize_generated.py'),'exec'),{'__name__':'__main__','__file__':str(D/'materialize_generated.py')})

if __name__=='__main__':main()
