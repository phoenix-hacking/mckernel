#!/usr/bin/python3
"""Actual saved-IHK export guard regression; candidate binding requires material GO."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bindings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    bindings = json.loads(args.bindings.read_text())
    if bindings.get('status') != 'FROZEN_AFTER_ACTUAL_MATERIAL_GO' or not bindings.get('material_GO'):
        raise RuntimeError('actual material GO and frozen candidate binding are required')
    for item in bindings['files']:
        path = Path(item['path'])
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError('frozen guard/input identity mismatch: ' + str(path))
    if args.output.exists():
        raise RuntimeError('retain old output; use separately admitted fresh output')
    cases = json.loads(Path(bindings['case_file']).read_text())
    sys.path.insert(0, bindings['policy_dependency_directory'])
    specification = importlib.util.spec_from_file_location('actual_ihk_export_guard', bindings['candidate_helper'])
    helper = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(helper)
    defined = {line.split()[-1] for line in Path(cases['actual_nm']['path']).read_text().splitlines() if line.split()}
    base = set(cases['base_summary_provider_symbols'])
    prior = set(cases['prior_export_set'])
    delta = set(cases['proposed_delta'])
    expected = base | set(helper.EXPECTED_NATIVE_LIFECYCLE_EXPORTS)
    if len(prior) != 21 or expected != prior | delta or expected != set(cases['actual_current_export_set']):
        raise RuntimeError('candidate changed more than the exact two approved literal exports')
    if set(cases['prior_native_constant']) - set(helper.EXPECTED_NATIVE_LIFECYCLE_EXPORTS):
        raise RuntimeError('candidate removed an earlier native export contract')
    results = []
    for case in cases['cases']:
        symbols = set(defined)
        addition = case['addition']
        if addition is not None:
            if addition in expected or any(token in symbols for token in case['added_defined_symbol_tokens']):
                raise RuntimeError('negative export is already admitted or emitted: ' + addition)
            symbols.update(case['added_defined_symbol_tokens'])
        try:
            helper._validate_provider_export_symbols(symbols, expected)
        except helper.ValidationError as error:
            diagnostic = str(error)
            if addition is None or 'contains unreviewed export metadata:' not in diagnostic:
                raise
            if any(token not in diagnostic for token in case['added_defined_symbol_tokens'][1:]):
                raise RuntimeError('rejection did not identify all three exact added metadata families')
            results.append({'name': case['name'], 'status': 'REJECTED_EXPECTED', 'symbol': addition,
                            'diagnostic': diagnostic})
        else:
            if addition is not None:
                raise RuntimeError('undeclared/held export was accepted: ' + addition)
            results.append({'name': case['name'], 'status': 'PASS_ACTUAL_SAVED_SYMBOLS',
                            'exact_current_exports': sorted(expected), 'prior21_retained': prior <= expected})
    if len(results) != 5:
        raise RuntimeError('exact actual-positive plus four negative checks required')
    report = {'status': 'PASS_ACTUAL_EXPORT_GUARD_AND_FOUR_STRICT_REJECTIONS', 'results': results,
              'source_or_held_scope_activation': False, 'module_loadability_or_runtime': False,
              'C_retirement': False, 'original_acceptance_delta': 0}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
