#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust migration only; no security testing.

Read one coordinator artifact-qualification ledger without mutating it.
"""
import argparse
import json
import math
from pathlib import Path

STAGES = ('current_object', 'default', 'SDK', 'native')


def number(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('timestamps must be finite')
    return value


def report(records, start, end):
    start, end = number(start), number(end)
    if end <= start:
        raise ValueError('current window must have positive duration')
    baselines = [r for r in records if r['event'] == 'baseline']
    if len(baselines) != 1:
        raise ValueError('exactly one frozen baseline required')
    baseline = baselines[0]
    duration = number(baseline['end']) - number(baseline['start'])
    if duration <= 0:
        raise ValueError('baseline must have positive duration')
    contracts = baseline['accepted']
    keys = [(r['package'], r['stage']) for r in contracts]
    if len(set(keys)) != len(keys) or any(s not in STAGES for _, s in keys):
        raise ValueError('baseline contracts must be unique supported stages')
    if any(not r.get('proof') for r in contracts):
        raise ValueError('baseline needs actual acceptance references')
    windows = [(start - (end - start), start), (start, end)]
    counts = [{s: 0 for s in STAGES} for _ in windows]
    states = {key: {'declared': None, 'started': number(baseline['end']),
                    'accepted': True} for key in keys}
    timings, last = {}, -math.inf
    for row in records:
        kind = row['event']
        if kind in ('baseline', 'quality'):
            continue
        at = number(row['at'])
        if at < last:
            raise ValueError('events must be in timestamp order')
        last = at
        key = (row['package'], row['stage'])
        if key[1] not in STAGES:
            raise ValueError('unsupported substantive stage')
        if kind == 'declare':
            if key in states:
                raise ValueError('contract already declared; retain ID across retries')
            states[key] = {'declared': at, 'started': None, 'accepted': False}
            continue
        if key not in states:
            raise ValueError('contract must be predeclared')
        state = states[key]
        if kind == 'start':
            # Ordered records can share one observation timestamp. The state
            # lookup above still requires the declaration to appear first.
            if state['declared'] is not None and at < state['declared']:
                raise ValueError('declaration must precede work')
            if state['started'] is None:
                state['started'] = at
                timings['/'.join(key)] = {k: row.get(k) for k in
                                         ('ready_at', 'first_compiler_at')}
            continue
        if state['started'] is None:
            raise ValueError('acceptance/reopening requires recorded work start')
        if kind == 'accept':
            if not row.get('proof'):
                raise ValueError('acceptance requires actual proof reference')
            delta = int(not state['accepted'])
            state['accepted'] = True
        elif kind == 'reopen':
            if not row.get('reason'):
                raise ValueError('reopening requires reason')
            delta = -int(state['accepted'])
            state['accepted'] = False
        else:
            raise ValueError('unknown event')
        for (left, right), count in zip(windows, counts):
            if left <= at < right:
                count[key[1]] += delta
    baseline_by_stage = {s: sum(r['stage'] == s for r in contracts) for s in STAGES}
    base_rate = len(contracts) * 3600 / duration
    summaries = []
    for (left, right), count in zip(windows, counts):
        rate = sum(count.values()) * 3600 / (right - left)
        summaries.append({'start': left, 'end': right, 'seconds': right - left,
                          'net_by_stage': count, 'net_steps': sum(count.values()),
                          'net_steps_per_hour': rate,
                          'ratio_to_baseline': rate / base_rate if base_rate > 0 else None})
    quality = any(r['event'] == 'quality' and r.get('start') == windows[0][0]
                  and r.get('end') == end and all(r.get(k) is True for k in
                  ('comparable_scope', 'no_splitting', 'no_native_default_slowdown'))
                  for r in records)
    sustained = quality and end - start >= 1800 and windows[0][0] >= baseline['end'] and all(
                               w['ratio_to_baseline'] is not None and
                               w['ratio_to_baseline'] >= 1.95 for w in summaries)
    return {'baseline': {'seconds': duration, 'net_steps': len(contracts),
                         'by_stage': baseline_by_stage, 'steps_per_hour': base_rate},
            'target_steps_per_hour': base_rate * 1.95 if base_rate > 0 else None,
            'previous': summaries[0], 'current': summaries[1],
            'two_window_quality_attestation': quality, 'sustained_195_claim': sustained,
            'readiness_and_first_compiler': timings,
            'limits': 'Stage mix matters; no per-stage ratio for zero baseline. Unknown '
                      'timestamps stay null. Coordinator attestation is not independent proof.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--current-start', type=float, required=True)
    parser.add_argument('--current-end', type=float, required=True)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.ledger.read_text().splitlines() if line.strip()]
    print(json.dumps(report(records, args.current_start, args.current_end), indent=2))


if __name__ == '__main__':
    main()
