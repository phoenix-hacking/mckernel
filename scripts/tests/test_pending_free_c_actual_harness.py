"""Pure extraction/result-oracle checks; never compiles or executes C."""
import ast
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'kernel/rust/tests/pending_free_c_actual_harness.py'
SPEC = importlib.util.spec_from_file_location('pending_free_c_actual_harness', PATH)
h = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)


def synthetic_rows():
    """Parser fixtures only: these are explicitly not executable C evidence."""
    result = []
    for route in ('result', 'fallback'):
        cases = [('inactive', 0), ('empty', 0), ('one', 1), ('two', 2), ('three', 3)]
        for name in h.CASES[4:]:
            cases.extend(((name, -22), (name+'-recovery', 3 if name in ('invalid-last','overlap-last') else 2)))
        for name, rc in cases:
            before = {'head':[10,11], 'pages':[
                {'list':[11,1], 'hash':[20+i,20+i], 'mode':1, 'phys':(4096,8192,16384)[i],
                 'offset':i+1, 'count':30+i, 'mapped':40+i, 'pgshift':12+i}
                for i in range(3)]}
            after = copy.deepcopy(before)
            if rc >= 0:
                after['head'] = [0,0]
                for page in after['pages'][:rc]:
                    page.update(mode=0, list=[90,91])
            result.append(dict(route=route, case=name, rc=rc, before=before, after=after,
                               panic=int(rc<0 and route=='fallback'),
                               callbacks=[[(4096,8192,16384)[i],i+1,1] for i in range(max(0,rc))]))
    return result


class PendingFreeCActualTests(unittest.TestCase):
    def test_python_syntax(self):
        ast.parse(PATH.read_text(), filename=str(PATH))

    def test_extraction_exact_source_bytes(self):
        parts, bindings = h.production()
        self.assertEqual(len(parts), 5)
        for part, binding in zip(parts, bindings):
            raw = (ROOT/binding['path']).read_text()[binding['start']:binding['end']]
            self.assertEqual(part, raw)
            self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), binding['sha256'])

    def test_shared_preflight_precedes_all_mutation(self):
        parts, _ = h.production()
        for body, guard in ((parts[3], h.GUARD_RESULT), (parts[4], h.GUARD_PUBLIC)):
            self.assertLess(body.index(guard), body.index('page->mode = PM_NONE'))
            self.assertLess(body.index(guard), body.index('list_del(&page->list)'))
        helper = parts[3].split('int mem_finish_free_pages_pending_result(', 1)[0]
        for required in ('slow->next->prev != slow', 'slow->prev->next != slow',
                         'fast == slow && slow != head', 'page->offset <= 0',
                         'page->offset > INT_MAX', 'ULONG_MAX / PAGE_SIZE',
                         'page->phys > ULONG_MAX - bytes', 'count == INT_MAX'):
            self.assertIn(required, helper)
        self.assertNotIn('list_del(', helper)
        self.assertNotIn('free_fn(', helper)

    def test_mutant_removes_only_two_preflight_calls(self):
        original, _ = h.generate()
        mutant, _ = h.generate(True)
        self.assertEqual(mutant, original.replace(h.GUARD_RESULT, '').replace(h.GUARD_PUBLIC, ''))
        self.assertIn('static int mem_validate_pending_free_ring(', mutant)
        self.assertIn('if (page->mode != PM_PENDING_FREE)', mutant)

    def test_source_only_never_executes(self):
        with patch.object(h.subprocess, 'run', side_effect=AssertionError('execution forbidden')):
            result = h.source_only()
        self.assertEqual(result['executed_c_rows'], 0)
        self.assertEqual(result['planned_rows'], 58)
        self.assertEqual(result['planned_mutant_rows'], 2)
        self.assertEqual(len(result['inputs']), 6)

    def test_snapshot_parser_positive(self):
        h.check_rows(synthetic_rows())

    def test_invalid_later_mutation_or_callback_rejected(self):
        for name in ('invalid-second', 'invalid-last', 'end-overflow', 'bad-prev',
                     'overlap', 'overlap-last'):
            for route in ('result','fallback'):
                for mutation in ('mode','callback'):
                    with self.subTest(name=name, route=route, mutation=mutation):
                        rows = synthetic_rows()
                        row = next(r for r in rows if r['case']==name and r['route']==route)
                        if mutation=='mode':
                            row['after']['pages'][0]['mode']=0
                        else:
                            row['callbacks']=[[4096,1,1]]
                        with self.assertRaises(AssertionError):
                            h.check_rows(rows)

    def test_recovery_callback_order_and_unrelated_fields_rejected(self):
        for mutation in ('order','hash','offset','panic'):
            rows = synthetic_rows()
            row = next(r for r in rows if r['case']=='invalid-last-recovery')
            if mutation=='order': row['callbacks'].reverse()
            elif mutation=='hash': row['after']['pages'][0]['hash']=[0,0]
            elif mutation=='offset': row['after']['pages'][1]['offset']=100
            else: row['panic']=1
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                h.check_rows(rows)

    def test_missing_or_reordered_rows_rejected(self):
        rows = synthetic_rows()
        with self.assertRaises(AssertionError): h.check_rows(rows[:-1])
        rows[0],rows[1] = rows[1],rows[0]
        with self.assertRaises(AssertionError): h.check_rows(rows)

    def test_mutant_requires_actual_prefix_release_shape(self):
        rows = []
        for route in ('result','fallback'):
            row = copy.deepcopy(next(r for r in synthetic_rows() if r['case']=='invalid-second' and r['route']==route))
            row['callbacks']=[[4096,1,1]]
            row['after']['pages'][0].update(mode=0, list=[90,91])
            row['after']['head']=[11,11]
            row['after']['pages'][1]['list']=[1,1]
            rows.append(row)
        h.check_mutant(rows)
        rows[1]['callbacks']=[]
        with self.assertRaises(AssertionError): h.check_mutant(rows)

    def test_missing_preflight_fails_source_admission(self):
        original = h.MEM.read_text()
        with patch.object(Path, 'read_text', autospec=True) as read:
            read.side_effect = lambda path: original.replace(h.GUARD_RESULT, '') if path==h.MEM else ORIGINAL_READ(path)
            with self.assertRaises(ValueError): h.production()


ORIGINAL_READ = Path.read_text

if __name__ == '__main__':
    unittest.main()
