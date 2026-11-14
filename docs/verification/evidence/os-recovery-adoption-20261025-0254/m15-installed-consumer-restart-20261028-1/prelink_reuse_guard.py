"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Read-only pre-link guard for reusing SDK11 Rust inputs with current generated rules.
No command is executed and no artifact is staged, linked, installed or accepted.
The BUILDID reconciliation requires independent review before execution use.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_file(path, ref, label):
    data = path.read_bytes()
    need(len(data) == ref['bytes'] and digest(data) == ref['sha256'], label)
    return data


def config_compatibility(accepted, current):
    """Only BUILDID's ASCII spelling may differ, and its buffer capacity must match.

    The pinned build_ihkconfig.py passes the literal through IHKCONFIG_BUILDID;
    the pinned ihkconfig.rs uses it only in env!(...).len() + 1. No Rust body
    in the pinned whole70 input set reads BUILDID. All other bytes stay exact.
    """
    pattern = rb'(?m)^#define BUILDID "([A-Za-z0-9._+\-]+)"$'
    old = list(re.finditer(pattern, accepted))
    new = list(re.finditer(pattern, current))
    need(len(old) == len(new) == 1, 'one plain ASCII BUILDID in each config')
    need(len(old[0][1]) == len(new[0][1]), 'BUILDID capacity changed')
    # Also rejects additional differently-spelled BUILDID directives.
    directive = rb'(?m)^\s*#\s*define\s+BUILDID\b'
    need(len(re.findall(directive, accepted)) == len(re.findall(directive, current)) == 1,
         'duplicate or unsupported BUILDID directive')
    need(re.sub(pattern, b'#define BUILDID "<bound>"', accepted) ==
         re.sub(pattern, b'#define BUILDID "<bound>"', current),
         'non-BUILDID config drift')
    return dict(mode='IDENTICAL' if accepted == current else 'ONLY_EQUAL_CAPACITY_BUILDID',
                accepted_buildid=old[0][1].decode('ascii'),
                current_buildid=new[0][1].decode('ascii'), capacity=len(old[0][1]) + 1)


def link_tokens(data):
    text = data.decode('utf-8')
    need(len(text.splitlines()) == 1, 'one generated link command required')
    return shlex.split(text, comments=False, posix=True)


def validate_links(contract, library, cli):
    for name, data in [('ihklib', library), ('ihkconfig', cli)]:
        need(link_tokens(data) == contract['generated_link_tokens'][name],
             'current generated link rule differs: ' + name)


def component_block(script, component):
    """Extract one generated CMake component arm, retaining its nested conditions."""
    lines = script.splitlines()
    marker = 'if(CMAKE_INSTALL_COMPONENT STREQUAL "' + component + '" OR NOT CMAKE_INSTALL_COMPONENT)'
    starts = [i for i, line in enumerate(lines) if line.strip() == marker]
    need(len(starts) == 1, 'exact component arm: ' + component)
    start = starts[0]
    depth = 1
    for end in range(start + 1, len(lines)):
        line = lines[end].strip()
        if re.match(r'^if\(', line):
            depth += 1
        elif re.match(r'^endif\(', line):
            depth -= 1
            if depth == 0:
                return '\n'.join(lines[start + 1:end])
    raise ValueError('unterminated component arm: ' + component)


def validate_install(contract, script):
    expected = contract['install_contract']
    for component, rule in expected.items():
        body = component_block(script, component)
        installs = re.findall(r'file\(INSTALL DESTINATION "([^"]+)" TYPE (\w+) FILES "([^"]+)"\)', body)
        need(installs == [tuple(rule['install'])], 'selective install target: ' + component)
        changes = re.findall(r'file\(RPATH_CHANGE\s+FILE "([^"]+)"\s+OLD_RPATH "([^"]*)"\s+NEW_RPATH "([^"]*)"\)', body)
        need(changes == [tuple(rule['rpath_change'])], 'installed RPATH: ' + component)
        # Full installs continue to select the same generated component arm.
        need('NOT CMAKE_INSTALL_COMPONENT' in script, 'full install selection')


def validate(contract, source_root, accepted_root, build_root):
    # Root must provide the isolated, patch-integrated source; dirty canonical
    # source alone cannot pass the exact postimage check.
    for relative, ref in contract['current_source_files'].items():
        check_file(source_root / relative, ref, 'source preimage/postimage: ' + relative)
    headers = sorted(str(p.relative_to(source_root)) for p in
                     (source_root / 'ihk/linux/include').rglob('*.h'))
    need(headers == contract['header_paths'], 'selected public header membership')
    for relative, ref in contract['accepted_sdk_files'].items():
        check_file(accepted_root / relative, ref, 'accepted SDK bytes: ' + relative)
    accepted = (accepted_root / 'ihk/config.h').read_bytes()
    current = (build_root / 'ihk/config.h').read_bytes()
    config = config_compatibility(accepted, current)
    generated_headers = sorted(str(p.relative_to(build_root)) for p in
                               (build_root / 'ihk/linux/include').rglob('*.h'))
    need(generated_headers == contract['generated_header_paths'], 'generated ABI header membership')
    for relative in generated_headers:
        need((build_root / relative).read_bytes() == (accepted_root / relative).read_bytes(),
             'generated ABI header drift: ' + relative)
    user = build_root / 'ihk/linux/user'
    library_link = (user / 'CMakeFiles/ihklib.dir/link.txt').read_bytes()
    cli_link = (user / 'CMakeFiles/ihkconfig.dir/link.txt').read_bytes()
    install = (user / 'cmake_install.cmake').read_bytes()
    validate_links(contract, library_link, cli_link)
    validate_install(contract, install.decode('utf-8'))
    return dict(status='PASS_PRELINK_SOURCE_REUSE_ONLY', config=config,
                source_files=len(contract['current_source_files']),
                accepted_sdk_files=len(contract['accepted_sdk_files']),
                library_link_sha256=digest(library_link), cli_link_sha256=digest(cli_link),
                install_script_sha256=digest(install),
                current_artifact=False, default_build=False, native=False, file_closure=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--accepted-root', type=Path, required=True)
    parser.add_argument('--build-root', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(args.contract.read_bytes()), args.source_root,
                              args.accepted_root, args.build_root), sort_keys=True))


if __name__ == '__main__':
    main()
