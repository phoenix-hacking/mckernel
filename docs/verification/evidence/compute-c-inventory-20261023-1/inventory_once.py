#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One existing build_report invocation; retain its SAME attribute_symbols results.
No map/second attribution pass, compilation, root, Docker, guest or runtime work.
"""
from collections import defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

REPO = Path('/home/holden/mckernel')
MODULE = REPO / 'scripts/mckernel_text_ownership.py'
OUT = Path('/home/holden/mckernel-work/host-preparation/compute-c-inventory-20261023-1')
BASE = Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1')
IMAGE = BASE / 'full-image-attempt-1/owner-work/output/build/kernel/mckernel.img'
SOURCE = BASE / 'source-materialization-1/materialized-source'
EXPECTED_IMAGE_SHA = '10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
TOOLS = dict(nm='/usr/bin/nm', addr2line='/usr/bin/addr2line')


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    begin = time.monotonic()
    need(os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}, 'ordinary CPU6 grant required')
    runroot = OUT / 'actual-onepass-1'
    runroot.mkdir()
    records, attributed_results = [], []
    result = dict(scope=SCOPE, status='FAIL_PRESERVE_ALL', attribution_invocations=0, build_report_invocations=0,
                  whole_image_rust_percentage_claimed=False, runtime_coverage_claimed=False,
                  source_derivative_sha256='5cffcc1b23dc5ca377baa055aab0417b0daac7ddcac0e2281903260f0ebd79e3',
                  source_manifest_sha256='28a6c1dededda19d2da07279f9a59d542996ae77bd96d176567cc86f0c5a8459',
                  materialization_sha256='d7e24b4c0d3174b3479e33796d712d439444bae82902482448890b9d8142d43d')

    def checked(argv):
        index = len(records) + 1
        prefix = runroot / ('%03d' % index)
        started = time.monotonic()
        record = dict(argv=argv, scope=SCOPE)
        records.append(record)
        (prefix.with_suffix('.command.json')).write_text(json.dumps(record, indent=2) + '\n')
        process = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, universal_newlines=True)
        prefix.with_suffix('.stdout').write_text(process.stdout)
        prefix.with_suffix('.stderr').write_text(process.stderr)
        prefix.with_suffix('.status').write_text(str(process.returncode) + '\n')
        record.update(returncode=process.returncode, seconds=time.monotonic() - started,
                      stdout_bytes=len(process.stdout.encode()), stderr_bytes=len(process.stderr.encode()))
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, argv, process.stdout, process.stderr)
        return process.stdout

    try:
        bindings = []
        for role, path in [('wrapper', Path(__file__)), ('module', MODULE), *TOOLS.items()]:
            path = Path(path)
            resolved = path.resolve(strict=True)
            raw = resolved.read_bytes()
            row = dict(role=role, path=str(path), resolved_path=str(resolved), sha256=sha(raw), bytes=len(raw))
            if role in TOOLS:
                row['version'] = checked([str(path), '--version']).splitlines()[0]
            bindings.append(row)
        write('SOURCE-TOOL-BINDINGS.json', bindings)
        spec = importlib.util.spec_from_file_location('existing_text_ownership', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Preserve all leaf command diagnostics while keeping the existing
        # run_checked success/error semantics and a SINGLE attribution pass.
        module.run_checked = checked
        # This lane is explicitly no-Git. Commit metadata is intentionally
        # unqueried; accepted producer derivative identities remain authoritative.
        module.git_commit = lambda repo: None
        original_attribution = module.attribute_symbols
        def retain_same_attribution(*args, **kwargs):
            result['attribution_invocations'] += 1
            need(result['attribution_invocations'] == 1, 'second attribution call refused')
            values = original_attribution(*args, **kwargs)
            attributed_results.extend(values)
            write('SAME-PASS-ATTRIBUTED-SYMBOLS.json', values)
            return values
        module.attribute_symbols = retain_same_attribution
        result['build_report_invocations'] += 1
        report = module.build_report(IMAGE, SOURCE, **TOOLS)
        report['commit_resolution'] = 'Not queried: no Git invocation authorized in this lane'
        write('symbol-language.json', report)
        need(report['image_sha256'] == EXPECTED_IMAGE_SHA, 'named ELF differs from selected10972')
        need(result['attribution_invocations'] == 1, 'one retained attribution required')
        # Existing summarize_attribution already rejects inconsistent aliases.
        # Reuse its SAME returned entries; no addr2line or report recomputation.
        spans = {}
        for entry in attributed_results:
            key = (int(entry['address'], 16), entry['size'])
            if key not in spans:
                spans[key] = {**entry, 'names': []}
            spans[key]['names'].append(entry['name'])
        c_spans = [entry for entry in spans.values() if entry['language'] == 'c']
        other_spans = [entry for entry in spans.values() if entry['language'] == 'other']
        header_spans = [entry for entry in other_spans if Path(entry['source']).suffix.lower() in ('.h', '.hpp', '.hxx')]
        unknown_spans = [entry for entry in other_spans if entry['source'] == '??']
        def ranked(entries):
            by_source = defaultdict(list)
            for entry in entries:
                by_source[entry['source']].append(entry)
            return sorted([dict(source=source, unique_spans=len(rows), bytes=sum(row['size'] for row in rows),
                                functions=sorted(rows, key=lambda row: (-row['size'], row['address'])))
                           for source, rows in by_source.items()], key=lambda row: (-row['bytes'], row['source']))
        inventory = dict(scope=SCOPE, schema='mckernel.current10972.c-only-singlepass-inventory.v1',
                         image_sha256=report['image_sha256'], metric_scope=report['metric_scope'],
                         method=report['method'], alias_deduplication='unique (integer address,size) from SAME attribute_symbols result',
                         c_only_unique_spans=len(c_spans), c_only_span_bytes=sum(row['size'] for row in c_spans),
                         c_only_raw_symbol_names=sum(len(row['names']) for row in c_spans),
                         c_sources_ranked=ranked(c_spans),
                         other_unique_spans=len(other_spans), other_span_bytes=sum(row['size'] for row in other_spans),
                         unknown_unique_spans=len(unknown_spans), unknown_span_bytes=sum(row['size'] for row in unknown_spans),
                         header_unique_spans=len(header_spans), header_span_bytes=sum(row['size'] for row in header_spans),
                         unknown_sources_ranked=ranked(unknown_spans), header_sources_ranked=ranked(header_spans),
                         all_other_sources_ranked=ranked(other_spans),
                         limitations=['Symbol-start source attribution, not instruction-level ownership or runtime coverage',
                                      'Unique sized symbol spans are not necessarily source-level function counts',
                                      'C+Rust metric denominator excludes assembly/other and is not whole-image Rust percentage',
                                      'Header and unknown sources stay other; mixed-language inline ownership is not resolved',
                                      'Source commit field does not replace exact derivative/materialization identity'])
        need(inventory['c_only_span_bytes'] == report['language_bytes']['c'], 'same-pass C total mismatch')
        need(len(spans) == report['unique_symbol_span_count'], 'same-pass alias count mismatch')
        write('C-ONLY-SOURCE-RANKED-INVENTORY.json', inventory)
        diagnostics = [row for row in records if row['stderr_bytes'] and row['argv'][0] in TOOLS.values()]
        result.update(image_sha256=report['image_sha256'], c_only_unique_spans=len(c_spans),
                      c_only_span_bytes=inventory['c_only_span_bytes'],
                      language_bytes=report['language_bytes'], unknown_unique_spans=len(unknown_spans),
                      unknown_span_bytes=inventory['unknown_span_bytes'], header_unique_spans=len(header_spans),
                      header_span_bytes=inventory['header_span_bytes'], tool_diagnostic_commands=diagnostics,
                      source_ranked_summary=[{k:row[k] for k in ('source','unique_spans','bytes')}
                                             for row in inventory['c_sources_ranked']])
        need(not diagnostics, 'tool emitted diagnostics; preserve unaccepted attribution, do not repeat/change profile')
        result['status'] = 'PASS_ONE_CURRENT10972_C_SYMBOL_SPAN_INVENTORY_NOT_COVERAGE'
    except BaseException as error:
        result['error'] = repr(error)
    finally:
        result['seconds'] = time.monotonic() - begin
        result['commands'] = records
        write('RESULT.json', result)
        print(json.dumps(result, sort_keys=True))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
