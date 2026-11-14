#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Compiler-free review of this private proposal. Deliberately exercises pin refusal
with compiler calls forbidden, so host-header refusal is not Rocky ABI proof.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

B=Path(__file__).resolve().parents[1]
R=Path('/home/holden/mckernel')

def main():
    checks=[]
    for source in (B/'orchestration').glob('*.py'):
        ast.parse(source.read_text(), filename=str(source))
    checks.append('Python orchestration syntax')
    p=subprocess.run(['git','apply','--check',str(B/'bfd-rust-accessors.patch')],cwd=R,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    checks.append('Patch applies to current selected CMake without modifying it')
    bind=json.loads((B/'SOURCE-BINDING.json').read_text())
    for relative,sha in bind['sources'].items():
        assert hashlib.sha256((R/relative).read_bytes()).hexdigest()==sha,relative
    checks.append('Six narrow original source hashes still match; Rust tool bodies untouched')
    spec=importlib.util.spec_from_file_location('m15_bfd_qualification',B/'orchestration/qualify.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with patch.object(module,'digest',return_value='unqualified-fixture-digest'), \
         patch.object(module.subprocess,'run',side_effect=AssertionError('compiler/subprocess forbidden')):
        try:
            module.qualify(R,B/'evidence/NEVER-CREATE-guard-fixture')
        except AssertionError as error:
            assert 'source changed:' in str(error)
        else: raise AssertionError('changed source was accepted')
    checks.append('Changed original source rejected before subprocess/output creation')
    def only_sources(path):
        relative=str(path.relative_to(R)) if path.is_relative_to(R) else ''
        return bind['sources'].get(relative,'unqualified-header-fixture')
    with patch.object(module,'digest',side_effect=only_sources), \
         patch.object(module.subprocess,'run',side_effect=AssertionError('compiler/subprocess forbidden')):
        try:
            module.qualify(R,B/'evidence/NEVER-CREATE-guard-fixture')
        except AssertionError as error:
            assert 'pin mismatch: header' in str(error)
        else: raise AssertionError('unqualified header accepted')
    checks.append('Wrong BFD header rejected before compiler/output creation')
    assert not (B/'evidence/NEVER-CREATE-guard-fixture').exists()
    report={'status':'PASS_COMPILER_FREE_PREPARATION_CHECKS','scope':bind['scope'],
            'checks':checks,'compiler_invoked':False,'pinned_ABI_executed':False,
            'native_acceptance':False,'limits':'Static preparation and mocked fail-closed guards only; no C/Rust executable equivalence claim.'}
    (B/'evidence/STATIC-CHECKS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status']+f'; {len(checks)} checks; compiler/native credit 0')
if __name__=='__main__': main()
