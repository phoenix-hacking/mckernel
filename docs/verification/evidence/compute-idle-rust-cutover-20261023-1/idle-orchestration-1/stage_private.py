#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
REPO = Path('/home/holden/mckernel')
OUT = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/idle-orchestration-1')
PINS = {'kernel/process.c': '910771e0908d3fc69fcad13e94a2f0da13a964ce0293911fa2dcd5180b6e9ca7',
        'kernel/rust/sched_helpers.rs': '8b5c15fe52c59964105561d560bca5c648464872a44ead44b672e180c44acbd1',
        'kernel/include/sched_helpers.h': '15e506c4a6e6bd359e704a29e89bff20ea65a14ea69f24171aeb43024847d474'}


def item(text, marker):
    start = text.index(marker)
    opening = text.index('{', start)
    depth = 0
    for end in range(opening, len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if depth == 0:
            return text[start:end + 1]
    raise ValueError('unbalanced source')


def main():
    before = {}
    for path, checksum in PINS.items():
        raw = (REPO / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != checksum:
            raise ValueError('exact canonical preimage changed: ' + path)
        before[path] = raw.decode()
    after = dict(before)
    original_idle = item(before['kernel/process.c'], 'static void idle(void)')
    consumer = (HERE / 'idle_consumer.c.inc').read_text()
    after['kernel/process.c'] = before['kernel/process.c'].replace(original_idle,
        consumer + original_idle + '\n#endif', 1)
    marker = '/* Caller holds runq_lock; list nodes and C-produced offsets stay valid. */'
    after['kernel/include/sched_helpers.h'] = before['kernel/include/sched_helpers.h'].replace(
        marker, (HERE / 'idle_abi.h.inc').read_text() + '\n' + marker, 1)
    rust_marker = '/// Returns one iff a locked idle runqueue contains a thread exactly running.'
    after['kernel/rust/sched_helpers.rs'] = before['kernel/rust/sched_helpers.rs'].replace(
        rust_marker, (HERE / 'idle_rust.rs.inc').read_text() + '\n' + rust_marker, 1)
    rows, patch = [], []
    for path in PINS:
        for label, value in [('preimage', before[path]), ('postimage', after[path])]:
            target = OUT / label / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('x') as stream:
                stream.write(value)
        rows.append(dict(path=path, before_sha256=PINS[path],
                         after_sha256=hashlib.sha256(after[path].encode()).hexdigest()))
        patch.extend(difflib.unified_diff(before[path].splitlines(True), after[path].splitlines(True),
                                        fromfile='a/' + path, tofile='b/' + path))
    # Exact original idle function and every byte outside the insertion survive.
    restored = after['kernel/process.c'].replace(consumer + original_idle + '\n#endif', original_idle, 1)
    if restored != before['kernel/process.c']:
        raise ValueError('unexpected C change outside exact idle selection')
    for path in (HERE / 'source.patch', OUT / 'source.patch'):
        with path.open('x') as stream:
            stream.write(''.join(patch))
    receipt = dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                   status='PRIVATE_THREE_SOURCE_IMPLEMENTATION_STAGED_NOT_ACCEPTED',
                   original_idle_function_retained_byte_identically=True,
                   all_c_bytes_outside_idle_selection_identical=True,
                   canonical_files_changed=False, active_image_changed=False,
                   files=rows, next='Actual-body state/order parity and actual header consumer compile, then independent focused review')
    for path in (HERE / 'SOURCE-MAP.json', OUT / 'SOURCE-MAP.json'):
        with path.open('x') as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
