"""Functional McKernel OS work only; no security testing or real growth."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('growth_clock_under_test', HERE / 'grow_scratch.py')
growth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(growth)
PROOF = growth.ref(HERE.parent / 'ROOT-NEW18H-20261026-FIXED-CUTOFF-BINDING.json')


class ReserveClockTest(unittest.TestCase):
    def check(self, remaining, reserve):
        clocks = [end - left for end, left in zip(growth.FIXED_CUTOFFS, remaining)]
        with patch.object(growth.time, 'time', return_value=clocks[0]), \
             patch.object(growth.time, 'monotonic', return_value=clocks[1]), \
             patch.object(growth.time, 'clock_gettime', return_value=clocks[2]):
            growth.fixed_cutoff_guard(PROOF, reserve=reserve)

    def test_all_three_have_reserve(self):
        for reserve in (0, 300, 600):
            self.check([reserve + 1] * 3, reserve)

    def test_wall_rollback_cannot_extend_other_clocks(self):
        for reserve in (300, 600):
            for clock in (1, 2):
                remaining = [3600, 3600, 3600]
                remaining[clock] = reserve - 1
                with self.assertRaises(Exception):
                    self.check(remaining, reserve)

    def test_exact_boundary_refused_for_each_clock(self):
        for reserve in (0, 300, 600):
            for clock in range(3):
                remaining = [3600, 3600, 3600]
                remaining[clock] = reserve
                with self.assertRaises(Exception):
                    self.check(remaining, reserve)


if __name__ == '__main__':
    unittest.main()
