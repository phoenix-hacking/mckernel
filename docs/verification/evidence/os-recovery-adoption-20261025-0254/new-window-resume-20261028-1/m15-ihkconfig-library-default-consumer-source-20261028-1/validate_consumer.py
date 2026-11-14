"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Validate bounded real-tool captures and unchanged installed SDK11 bytes.
No subprocess, workload, compiler, install, grant or control action occurs here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def need(ok, message):
    if not ok:
        raise ValueError(message)


def symbols(text):
    found = {}
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        need(len(fields) in (2, 3), 'unexpected nm row')
        kind, name = fields[-2:]
        need(len(kind) == 1, 'unexpected nm type')
        name = name.split('@', 1)[0]
        found.setdefault(name, []).append(kind)
    return found


def validate(contract, captures, expected_usage, installed_root):
    roots = contract['roots']; names = set(roots)
    need(len(roots) == 76 and sum(k == 'T' for k in roots.values()) == 70, 'SDK70+6 root contract')
    for label, relative in [('installed_cli', 'usr/local/sbin/ihkconfig'),
                            ('installed_library', 'usr/local/lib64/libihk.so')]:
        data = (installed_root / relative).read_bytes(); ref = contract['accepted_artifacts'][label]
        need(len(data) == ref['bytes'] and hashlib.sha256(data).hexdigest() == ref['sha256'], 'installed bytes '+label)
    need(len(captures) == 6, 'exact six capture records required')
    for i, capture in enumerate(captures):
        need(capture.get('index') == i and capture.get('direct_child_joined') is True
             and capture.get('group_absent') is True and capture.get('closed_streams') is True
             and not capture.get('timed_out'), 'child retirement capture '+str(i))
        need(capture.get('returncode') == (1 if i in (4, 5) else 0), 'real command status '+str(i))
        need(capture.get('argv') == contract['expected_capture_argv'][i]
             and capture.get('environment') == contract['expected_environment'], 'exact argv/environment '+str(i))
    defined = symbols(captures[0]['stdout'])
    need(all(defined.get(name) == [kind] for name, kind in roots.items()), 'library unique Rust provider roots')
    need(not (set(symbols(captures[1]['stdout'])) & names), 'unresolved project library provider')
    imported = set(symbols(captures[2]['stdout'])) & names
    need(imported == set(contract['project_imports']), 'CLI exact four public library imports')
    for i in range(4):
        need(captures[i]['stderr'] == '', 'unexpected tool/loader stderr '+str(i))
    library = str(installed_root / 'usr/local/lib64/libihk.so')
    lines = [line.strip() for line in captures[3]['stdout'].splitlines() if re.match(r'\s*libihk\.so\s+=>', line)]
    need(len(lines) == 1 and re.fullmatch(r'libihk\.so\s+=>\s+'+re.escape(library)+r'\s+\(0x[0-9a-fA-F]+\)', lines[0]), 'loader exact private Rust DSO')
    for i in (4, 5):
        need(captures[i]['stdout'] == '' and captures[i]['stderr'].encode() == expected_usage,
             'unchanged C-oracle usage/exit '+str(i))
    return dict(status='PASS_REUSED_SDK11_INSTALLED_CLI_ARGUMENT_ERRORS_ONLY', provider_functions=70,
                provider_data=6, public_cli_imports=4, real_cli_main_cases=2,
                native=False, current_default_build=False, file_closure=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--captures', type=Path, required=True)
    p.add_argument('--installed-root', type=Path, required=True)
    p.add_argument('--expected-usage', type=Path, required=True)
    a = p.parse_args()
    contract = json.loads(a.contract.read_bytes())
    usage = a.expected_usage.read_bytes()
    need(hashlib.sha256(usage).hexdigest() == contract['expected_usage']['sha256'], 'oracle bytes')
    print(json.dumps(validate(contract, json.loads(a.captures.read_bytes()), usage, a.installed_root), sort_keys=True))


if __name__ == '__main__':
    main()
