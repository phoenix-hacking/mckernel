#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Known-input private source preparation only; no compiler/root/Docker/guest/Git.
Reuse the idle copy implementation, with an exact bound two-postimage successor.
"""
from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent
OLD = HERE.parent/'production-consumer-1/materialize_successor.py'
EXPECTED = 'b176a876537f9c81137713b3697fadcbf29e7c7aed10a3900ffbe9404c61dc54'
OUT = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/memory-combined-preparation-1')


def main():
    raw = OLD.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('accepted private idle source copier drift')
    source = raw.decode()
    source = source.replace('Ordinary exact known-input source copy: THREE canonical postimages only.',
                            'Ordinary exact known-input source copy: reviewed memory TWO postimages over accepted idle successor.')
    source = source.replace("OUT = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-consumer-1')", "OUT = Path("+repr(str(OUT))+")")
    source = source.replace("BASE = Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')", "BASE = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-consumer-1')\nMEMORY = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-1/m14-memory')")
    source = source.replace("SOURCE = BASE / 'source-materialization-1/materialized-source'", "SOURCE = BASE / 'materialized-source'")
    start = source.index('AUTHORITY = ')
    end = source.index('MAX_GROWTH = ', start)
    source = source[:start]+'''AUTHORITY = MEMORY / 'SOURCE-REVIEW.md'
BASE_CANONICAL_SHA = '7dc3bbf0dca602a1085dab30d304b7a59f9c765acfdc36a0abf744c2dc1a5f31'
POST = {'arch/x86_64/kernel/memory.c': '4818be5c7277621ce41dae1d261dec97e7e0c65b6054a6e8511a4d64d555c68f',
        'kernel/rust/x86_memory_helpers.rs': '9cba23c3b1e9ba94205c5b8234c5be0408d8c41722b5a0e094ca5a0d1211d067'}
''' + source[end:]
    source = source.replace("baseline = json.loads((BASE / 'thin-inputs.json').read_text())", "baseline = json.loads((BASE / 'source-inputs.json').read_text())")
    start = source.index('    authority_raw = ')
    end = source.index('    document = copy.deepcopy(baseline)', start)
    source = source[:start]+'''    authority_raw = AUTHORITY.read_bytes()
    need(sha(authority_raw) == '62b652a8e7d23b4262a35a262d4d7d7750c4aa3d06ccadf6d32c32099c878e24'
         and b'Independent decision: SOURCE PASS' in authority_raw,
         'accepted exact independent memory source review')
    pins = json.loads((MEMORY/'handoff-sha256.json').read_text())
    need(sha((MEMORY/'cutover.patch').read_bytes()) == pins['cutover.patch'] == 'cf82c4807bd4a5f72ea3709f14a375578a42ddd2bf072251cb3b5c2d14f1fe38',
         'accepted memory delta bytes')
    original = json.loads((MEMORY/'source-bindings.json').read_text())
    for relative,row in original['sources'].items():
        need(baseline['materialized_repository_files'][relative] == row['sha256'],
             'memory baseline and existing idle successor coherent: '+relative)
    receipt = json.loads((MEMORY/'fixture-receipt.json').read_text())
    need(sha((MEMORY/'fixture-receipt.json').read_bytes()) == pins['fixture-receipt.json']
         and receipt['exit_code'] == 0 and receipt['joined_group_absent'] is True
         and receipt['fixture_result']['cases'] == 129888,
         'retained reviewed memory evidence; never rerun fixture here')
''' + source[end:]
    source = source.replace('(REPO / relative)', "(MEMORY / 'candidate' / relative)")
    source = source.replace("canonical integrated postimage changed: ", "reviewed private memory postimage changed: ")
    source = source.replace('canonical_integration_sha256=sha(authority_raw), three_source_delta=changed,',
                            "accepted_memory_review_sha256=sha(authority_raw), memory_two_source_delta=changed,\n                      memory_patch_sha256=pins['cutover.patch'], memory_fixture_receipt_sha256=pins['fixture-receipt.json'],")
    source = source.replace("'mckernel.idle-orchestration-production-consumer-thin-inputs.v1'", "'mckernel.idle-and-memory-production-consumer-thin-inputs.v1'")
    source = source.replace("document['idle_orchestration_overlay'] = derivation", "document['memory_two_source_overlay'] = derivation")
    source = source.replace("(BASE / 'source-materialization-1/materialization-journal.jsonl')", "(BASE / 'materialization-journal.jsonl')")
    source = source.replace('(REPO if relative in POST else SOURCE) / relative', "((MEMORY / 'candidate') if relative in POST else SOURCE) / relative")
    source = source.replace("'PASS_COHERENT_THREE_POSTIMAGE_SOURCE_MATERIALIZATION_ONLY'", "'PASS_COHERENT_IDLE_PLUS_TWO_MEMORY_POSTIMAGE_SOURCE_MATERIALIZATION_ONLY'")
    source = source.replace('canonical_integration_sha256=sha(authority_raw),', 'accepted_memory_review_sha256=sha(authority_raw),')
    with (HERE/'materialize_combined_generated.py').open('x') as stream:
        stream.write(source)
    # Exact copy implementation has no subprocess and executes in this granted process.
    namespace = {'__name__': '__main__', '__file__': str(HERE/'materialize_combined_generated.py')}
    exec(compile(source, namespace['__file__'], 'exec'), namespace)


if __name__ == '__main__':
    main()
