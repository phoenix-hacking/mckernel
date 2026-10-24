#!/usr/bin/env python3
"""Prepare byte-exact original MM inline bodies. Does not compile or execute them."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SDK = Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output')
SOURCE = SDK / 'source/linux-6.12.0-211.44.1.el10_2'
PROJECT = Path('/home/holden/mckernel')
FUNCTIONS = {
    'include/linux/seqlock.h': [
        'do_raw_write_seqcount_begin', 'do_raw_write_seqcount_end'],
    'include/linux/mmap_lock.h': [
        '__mmap_lock_trace_start_locking', '__mmap_lock_trace_acquire_returned',
        '__mmap_lock_trace_released', 'mmap_assert_write_locked',
        'mm_lock_seqcount_begin', 'mm_lock_seqcount_end', 'mmap_write_lock',
        'vma_end_write_all', 'mmap_write_unlock'],
    'include/linux/mm.h': ['__is_vma_write_locked', 'vma_start_write'],
}

def function(text, name):
    # All selected definitions are balanced-brace inline functions without
    # braces in comments/strings. Reject that assumption instead of truncating.
    import re
    pattern = re.compile(r'(?m)^static (?:__always_inline |inline )?(?:void|bool) '
                         + re.escape(name) + r'\s*\(')
    match = pattern.search(text)
    if match is None:
        raise ValueError('missing original definition: ' + name)
    start = match.start()
    brace = text.find('{', match.end())
    if brace < 0:
        raise ValueError('missing body: ' + name)
    depth = 1
    i = brace + 1
    state = 'code'
    while depth:
        if i >= len(text):
            raise ValueError('unterminated function: ' + name)
        pair = text[i:i + 2]
        char = text[i]
        if state == 'comment':
            if pair == '*/':
                state = 'code'
                i += 2
                continue
        elif state == 'line':
            if char == '\n':
                state = 'code'
        elif state in ('"', "'"):
            if char == '\\':
                i += 2
                continue
            if char == state:
                state = 'code'
        elif pair == '/*':
            state = 'comment'
            i += 2
            continue
        elif pair == '//':
            state = 'line'
            i += 2
            continue
        elif char in ('"', "'"):
            state = char
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        i += 1
    return text[start:i] + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'generated')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(HERE) or output == HERE:
        raise SystemExit('output must be a new subdirectory of this private candidate')
    output.mkdir(parents=True, exist_ok=False)
    config = (SDK / 'build/.config').read_text()
    required = ['CONFIG_X86_64=y', 'CONFIG_SMP=y', 'CONFIG_PER_VMA_LOCK=y',
                'CONFIG_TRACING=y', 'CONFIG_TRACEPOINTS=y', 'CONFIG_MEMCG=y',
                'CONFIG_JUMP_LABEL=y', 'CONFIG_HAVE_JUMP_LABEL_HACK=y',
                '# CONFIG_KCSAN is not set', '# CONFIG_DEBUG_VM is not set',
                '# CONFIG_DEBUG_LOCK_ALLOC is not set', '# CONFIG_PREEMPT_RT is not set']
    if any(line not in config.splitlines() for line in required):
        raise SystemExit('pinned fixture configuration no longer matches')
    chunks = []
    pointers = []
    for relative, names in FUNCTIONS.items():
        path = SOURCE / relative
        raw = path.read_bytes()
        text = raw.decode()
        for name in names:
            body = function(text, name)
            chunks.append('/* Exact original: ' + relative + ' :: ' + name + ' */\n' + body)
            pointers.append({'source': str(path), 'function': name,
                             'body_sha256': hashlib.sha256(body.encode()).hexdigest()})
    (output / 'original_linux_mm_bodies.h').write_text('\n'.join(chunks))
    mock_headers = output / 'include/linux'
    mock_headers.mkdir(parents=True)
    (mock_headers / 'mm.h').write_text(
        '#ifndef M15_EXACT_REFERENCE_MM_H\n#define M15_EXACT_REFERENCE_MM_H\n'
        '#include "../../../fixture_runtime.h"\n'
        '#include "../../original_linux_mm_bodies.h"\n#endif\n')
    (mock_headers / 'mmap_lock.h').write_text('#include "mm.h"\n')
    wrappers = PROJECT / 'host-kernel/native-rust/mcctrl_vm_write_compat.c'
    private_original = output / 'original'
    private_original.mkdir()
    for suffix in ('c', 'h'):
        original = wrappers.with_suffix('.' + suffix)
        (private_original / original.name).write_bytes(original.read_bytes())
    (output / 'ORIGINAL-REFERENCE.json').write_text(json.dumps({
        'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
        'status': 'ORIGINAL_BODY_EXTRACTION_ONLY_NOT_COMPILED',
        'original_project_C': str(wrappers),
        'original_project_C_sha256': hashlib.sha256(wrappers.read_bytes()).hexdigest(),
        'original_project_header': str(wrappers.with_suffix('.h')),
        'original_project_header_sha256': hashlib.sha256(wrappers.with_suffix('.h').read_bytes()).hexdigest(),
        'private_original_project_C': str(private_original / wrappers.name),
        'compile_rule': 'Compile original_project_C unchanged with generated mock Linux headers; never substitute a hand-written C reference.',
        'exact_required_config': required,
        'definitions': pointers,
        'limitations': ['Mocked primitive sequencing is not Linux runtime proof.',
                       'No Rust replacement exists yet; no equivalence result.',
                       'Jump-label code generation and barriers need separate exact-SDK review.'],
    }, indent=2) + '\n')
    print(output)

if __name__ == '__main__':
    main()
