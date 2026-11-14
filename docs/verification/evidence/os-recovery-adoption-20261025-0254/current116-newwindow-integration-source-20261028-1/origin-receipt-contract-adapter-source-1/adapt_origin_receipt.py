"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only aliases for one exact retained source-generation receipt. No execution.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os

D = Path(__file__).resolve().parent
E = D.parent.parent
SOURCE = E / 'ROOT-CURRENT116-F03SEVEN-SHM-BUILD-PREPARATION-1/ROOT-ACTUAL-ORIGIN-PRODUCER-JOIN.json'
SOURCE_BYTES = 3002
SOURCE_SHA = 'fa9c08cdd8bc382a13582b6b06c830f68879d831e4bb81cb4f5d0c2989874264'
CONTRACT = D / 'EXACT-RETAINED-RECEIPT.CONTRACT.json'
CONTRACT_SHA = 'fa9c08cdd8bc382a13582b6b06c830f68879d831e4bb81cb4f5d0c2989874264'


def require(value, message):
    if not value: raise ValueError(message)


def reference(path):
    path = Path(path)
    require(path.is_absolute() and not path.is_symlink() and path.is_file(), 'absolute regular byte subject')
    first = path.stat(); raw = path.read_bytes(); last = path.stat()
    require((first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns, first.st_ctime_ns) ==
            (last.st_dev, last.st_ino, last.st_size, last.st_mtime_ns, last.st_ctime_ns), 'stable byte subject')
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    def constant(value): raise ValueError('nonfinite JSON number: ' + value)
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    require(type(result) is dict, 'declared receipt JSON object')
    return result


def contract():
    require(reference(CONTRACT)['sha256'] == CONTRACT_SHA, 'frozen exact receipt contract bytes')
    return decode(CONTRACT.read_bytes())


def validate_semantics(value):
    expected = contract()
    require(set(value) == set(expected), 'exact original receipt field schema')
    require(value['author'] == '/root' and value['scope'] == __doc__.splitlines()[0], 'genuine source receipt owner/scope')
    require(value['source_generation_only'] is True and value['compiler'] is False, 'source-only, compiler did not execute')
    require(type(value['returncode']) is int and value['returncode'] == 0, 'actual source producer returned zero')
    require(value['child_positive_join'] is True and value['closed_streams'] is True, 'positive child join and closed streams')
    require(value['argv'] == expected['argv'] and value['outputs'] == expected['outputs'], 'exact frozen producer argv and ordered outputs')
    require(value == expected, 'all original receipt facts exact')
    for row in value['outputs'] + [value['stdout'], value['stderr']]:
        require(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and reference(row['path']) == row,
                'exact retained output/stream bytes')
    binding = decode(Path(value['outputs'][0]['path']).read_bytes())
    require(binding['status'] == 'GENERATED_SOURCE_ONLY_NO_COMPILER_RESULT' and
            binding['new_C_runtime_objects'] == 0 and binding['compiled_Rust_metadata_qualification'] is None,
            'retained generated binding is not compiler qualification')
    return value


def adapted(source_path):
    source_path = Path(source_path)
    expected = dict(path=str(SOURCE), bytes=SOURCE_BYTES, sha256=SOURCE_SHA)
    require(reference(source_path) == expected, 'exact genuine fa9c source receipt path/bytes')
    original = validate_semantics(decode(source_path.read_bytes()))
    result = copy.deepcopy(original)
    result.update(source_receipt=expected,
        receipt_adapter_schema='mckernel.exact-origin-receipt-semantic-aliases.v1',
        compiler_executed=original['compiler'], direct_child_joined=original['child_positive_join'],
        streams_closed=original['closed_streams'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--source-receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = adapted(args.source_receipt)
    require(args.output.is_absolute() and args.output.parent.is_dir(), 'existing absolute data output parent')
    raw = (json.dumps(result, indent=2) + '\n').encode()
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(dict(status='EXACT_RETAINED_ORIGIN_RECEIPT_ALIASES_DATA_ONLY',
                          receipt=reference(args.output), source_receipt=result['source_receipt'], runtime_authority=None)))


if __name__ == '__main__': main()
