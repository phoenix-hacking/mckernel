"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded117 successor: Root-only123-file readonly source export plus exact3module refs.
Pure validate_export is exercised by tests; no actual export occurs in source work.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os

D = Path(__file__).resolve().parent
S = D.parent
CHECKOUT_ROOT = Path('/home/holden/mckernel')


def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def auth(row):
    assert type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}
    assert Path(row['path']).is_absolute() and not Path(row['path']).is_symlink() and ref(row['path']) == row
    return Path(row['path'])


def read(path):
    return json.loads(Path(path).read_bytes())


def validate_export(binding):
    assert binding['author'] == '/root' and binding['decision'] == 'MATERIALIZE_EXACT_CURRENT118_RUST123_READONLY_EXPORT'
    assert binding['maximum_invocations'] == 1
    assert binding['source_overlay'] == ref(S / 'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json')
    overlay = read(auth(binding['source_overlay']))
    adoption = read(auth(binding['source_adoption']))
    source = read(S / 'SOURCE-MAP-FROM116.json')
    assert adoption['author'] == '/root' and len(adoption['source_changes']) == 9
    expected = {row['relative']: row['postimage']['sha256'] for row in source['writes']}
    assert len(expected) == 9
    for row in adoption['source_changes']:
        assert row['after']['path'] == str(CHECKOUT_ROOT / row['relative'])
        assert auth(row['after']) and row['relative'] in expected and row['after']['sha256'] == expected.pop(row['relative'])
    assert not expected
    assert len(overlay['files']) == 123 and len({row['relative'] for row in overlay['files']}) == 123
    assert sum(row['relative'].endswith('.rs') for row in overlay['files']) == 112
    for row in overlay['files']:
        auth(row['source'])
        relative = Path(row['relative'])
        assert not relative.is_absolute() and '..' not in relative.parts and str(relative) == row['relative']
    profile = read(D / 'cohort/PROFILE.TEMPLATE.SOURCE-ONLY.json')
    external = read(D / 'EXTERNAL-THREE-MODULE-INPUTS.json')['external_inputs']
    assert external == profile['inputs']['external_relative_modules'] and len(external) == 3
    root = Path(profile['inputs']['source6153'])
    assert [row['relative'] for row in external] == ['scripts/tests/fixtures/mckernel_guest_sysfs.rs', 'host-kernel/native-rust/abi/vdso.rs', 'host-kernel/native-rust/zero_pages.rs']
    for row in external:
        assert row['source']['path'] == str(root / row['relative']) and row['container_path'] == '/src/' + row['relative']
        auth(row['source'])
    lib = next(row for row in overlay['files'] if row['relative'] == 'lib.rs')
    text = auth(lib['source']).read_text()
    for row in external:
        assert text.count('#[path = "../../' + row['relative'] + '"]') == 1
    return overlay, external, profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-input', required=True)
    args = parser.parse_args()
    overlay, external, profile = validate_export(read(args.root_input))
    root = D / 'rust-subtree'
    manifest = D / 'ROOT-ACTUAL-RUST123-EXPORT-MANIFEST.json'
    assert not os.path.lexists(root) and not os.path.lexists(manifest)
    root.mkdir(mode=0o755)
    rows = []
    for row in overlay['files']:
        target = root / row['relative']
        target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(auth(row['source']).read_bytes())
        target.chmod(0o444)
        assert ref(target)['sha256'] == row['source']['sha256']
        rows.append(dict(relative=row['relative'], snapshot=ref(target)))
    value = dict(schema='mckernel.exact-kernel-rust-subtree-readonly.v1', runtime_authority=None,
                 export_root=str(root), container_destination='/src/kernel/rust',
                 base_source_root=profile['inputs']['source6153'] + '/kernel/rust', files=rows, external_inputs=external)
    with manifest.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status='EXACT123_READONLY_SOURCE_EXPORT_NOT_EXECUTION_AUTHORITY', manifest=ref(manifest),
                          files=123, Rust_files=112, external_modules=3, compiler_calls=0)))


if __name__ == '__main__':
    main()
