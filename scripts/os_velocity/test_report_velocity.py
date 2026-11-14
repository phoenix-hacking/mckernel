import unittest
from report_velocity import report


def baseline(accepted=2):
    return [{'event': 'baseline', 'start': 0, 'end': 1800,
             'accepted': [{'package': 'base' + str(i), 'stage': 'current_object',
                           'proof': 'retained-acceptance'} for i in range(accepted)]}]


def work(package, at, stage='current_object'):
    return [{'event': 'declare', 'package': package, 'stage': stage, 'at': at - 2},
            {'event': 'start', 'package': package, 'stage': stage, 'at': at - 1},
            {'event': 'accept', 'package': package, 'stage': stage, 'at': at,
             'proof': 'actual-acceptance'}]


class Velocity(unittest.TestCase):
    def test_ordered_declaration_and_start_can_share_observation_time(self):
        rows = work('same-clock', 2000)
        rows[1]['at'] = rows[0]['at']
        self.assertEqual(report(baseline() + rows, 1800, 3600)['current']['net_steps'], 1)
        with self.assertRaises(ValueError):
            report(baseline() + [rows[1], rows[0], rows[2]], 1800, 3600)

    def test_baseline_duration_and_target(self):
        d = baseline(); d[0].update(start=1792903323.2948987, end=1792905126.062605)
        r = report(d, 1800, 3600)
        self.assertAlmostEqual(r['baseline']['steps_per_hour'], 3.993858984390887)
        self.assertAlmostEqual(r['target_steps_per_hour'], 7.788025019562229)

    def test_retry_success_deduplicated_and_boundaries_half_open(self):
        d = baseline() + work('a', 1800)
        d += [dict(d[-1], at=2000), dict(d[-1], at=3600)]
        self.assertEqual(report(d, 1800, 3600)['current']['net_steps'], 1)

    def test_reopen_subtracts_prior_acceptance(self):
        d = baseline()
        d += [{'event': 'reopen', 'package': 'base0', 'stage': 'current_object',
               'at': 1900, 'reason': 'actual regression'}]
        self.assertEqual(report(d, 1800, 3600)['current']['net_steps'], -1)
        d += [{'event': 'start', 'package': 'base0', 'stage': 'current_object', 'at': 1950},
              {'event': 'accept', 'package': 'base0', 'stage': 'current_object',
               'at': 2000, 'proof': 'actual-correction-acceptance'}]
        self.assertEqual(report(d, 1800, 3600)['current']['net_steps'], 0)

    def test_accept_requires_predeclared_started_contract(self):
        with self.assertRaises(ValueError):
            report(baseline() + [work('a', 2000)[-1]], 1800, 3600)

    def test_no_redeclaration_or_nonsoftware_bookkeeping(self):
        for extra in [work('a', 2100)[0], dict(work('b', 2100)[0], stage='docs')]:
            with self.assertRaises(ValueError):
                report(baseline() + work('a', 2000) + [extra], 1800, 3600)

    def test_behavior_only_cannot_inflate_integration_throughput(self):
        with self.assertRaises(ValueError):
            report(baseline() + work('parity-only', 2000, stage='behavior'), 1800, 3600)

    def test_zero_baseline_reports_absolute_only(self):
        r = report(baseline(0) + work('a', 2000), 1800, 3600)
        self.assertIsNone(r['current']['ratio_to_baseline'])
        self.assertFalse(r['sustained_195_claim'])

    def test_two_windows_and_quality_required(self):
        d = baseline()
        for at in [1900, 2000, 2100, 2200, 3700, 3800, 3900, 4000]:
            d += work(str(at), at)
        self.assertFalse(report(d, 3600, 5400)['sustained_195_claim'])
        d += [{'event': 'quality', 'start': 1800, 'end': 5400, 'comparable_scope': True,
               'no_splitting': True, 'no_native_default_slowdown': True}]
        self.assertTrue(report(d, 3600, 5400)['sustained_195_claim'])
        d[-1]['no_native_default_slowdown'] = False
        self.assertFalse(report(d, 3600, 5400)['sustained_195_claim'])

    def test_missing_proof_and_reversed_window_rejected(self):
        d = baseline() + work('a', 2000); del d[-1]['proof']
        with self.assertRaises(ValueError):
            report(d, 1800, 3600)
        with self.assertRaises(ValueError):
            report(baseline(), 3600, 1800)


if __name__ == '__main__':
    unittest.main()
