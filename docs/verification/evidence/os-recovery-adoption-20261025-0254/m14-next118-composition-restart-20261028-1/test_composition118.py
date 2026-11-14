"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source bindings and drift controls; no compile, fixture, guard or producer.
"""
import copy
import io
import json
import unittest

import compose118 as c


class Composition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.source117, cls.source, cls.recipe, cls.checks = c.compose()
        cls.review03 = c.checked(c.PINS['reviewF03'])
        cls.review06 = c.checked(c.PINS['reviewF06'])
        cls.retained = c.checked(c.PINS['recipe117'])['retained_inputs']

    def source_rejected(self, mutate):
        source = dict(self.source)
        mutate(source)
        with self.assertRaises(ValueError):
            c.validate_sources(self.base, self.source117, source, self.review03, self.review06)

    def recipe_rejected(self, mutate):
        recipe = copy.deepcopy(self.recipe)
        mutate(recipe)
        with self.assertRaises(ValueError):
            c.validate_recipe(recipe, self.source, self.retained)

    def test_positive_complete_composition(self):
        self.assertEqual(self.checks['changed_paths_relative116'], 9)
        self.assertEqual(self.checks['changed_paths_relative117'], 8)
        self.assertEqual(self.checks['actual_HOST_pairs_reused'], 2880)
        self.assertEqual(self.source['kernel/rust/f06_vdso_info.rs'], self.source117['kernel/rust/f06_vdso_info.rs'])
        self.assertTrue(all(self.checks[name] == 0 for name in ['actual_builds', 'actual_fixture_replays', 'actual_native', 'canonical_writes', 'file_closures']))

    def test_positive_both_patch_maps_apply_and_inverse(self):
        for version, baseline in [(116, self.base), (117, self.source117)]:
            source_map = json.loads((c.HERE / ('SOURCE-MAP-FROM' + str(version) + '.json')).read_bytes())
            self.assertEqual(len(source_map['writes']), 9 if version == 116 else 8)
            seen = set()
            for row in source_map['writes']:
                path = row['relative']
                self.assertNotIn(path, seen)
                seen.add(path)
                output = c.read(row['postimage']).decode()
                self.assertEqual(output, self.source[path])
                if row['preimage']:
                    self.assertEqual(c.read(row['preimage']).decode(), baseline[path])
                    patch = c.read(row['patch']).decode()
                    self.assertEqual(c.apply(baseline[path], patch), output)
                    self.assertEqual(c.apply(output, c.patch_for(output, baseline[path], path)), baseline[path])
                else:
                    self.assertNotIn(path, baseline)
                    self.assertIsNone(row['patch'])

    def test_positive_reference_overlay_123_112(self):
        overlay = json.loads((c.HERE / 'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json').read_bytes())
        self.assertEqual(len(overlay['files']), 123)
        self.assertEqual(len({row['relative'] for row in overlay['files']}), 123)
        self.assertEqual(sum(row['relative'].endswith('.rs') for row in overlay['files']), 112)
        for row in overlay['files']:
            c.read(row['source'])
        self.assertEqual(overlay['physical_directory_exports_created'], 0)

    def test_positive_original_reviewed_deltas_and_cfg(self):
        patches = [c.read(row).decode() for row in self.review03['integration_patches']]
        self.assertEqual(c.apply(self.source117['kernel/syscall.c'], patches[0]), self.source['kernel/syscall.c'])
        self.assertEqual(c.apply(self.source117[c.RUST], patches[1]), self.source[c.RUST])
        leaf = c.read(self.review06['source']).decode()
        self.assertEqual(leaf, self.source[c.LEAF])
        for before, now in zip(self.recipe['command_hash_history'], self.recipe['ordered_commands']):
            self.assertEqual(before['current118_argv_sha256'], now['argv_sha256'])
        self.assertEqual([row['index'] for row in self.recipe['command_hash_history'] if row['argv_changed']], [0, 2])

    def test_negative_input_hash_drift(self):
        row = dict(c.PINS['source117'])
        row['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'exact BYTE input'):
            c.read(row)

    def test_negative_patch_preimage_drift(self):
        patch = c.read(self.review03['integration_patches'][1]).decode()
        before = self.source117[c.RUST].replace('const _: PtraceSetSingleStepFn', 'const _: ChangedType', 1)
        with self.assertRaisesRegex(ValueError, 'exact unique patch preimage'):
            c.apply(before, patch)

    def test_negative_ambiguous_patch_preimage(self):
        patch = c.read(self.review03['integration_patches'][1]).decode()
        before = self.source117[c.RUST]
        old = c.hunks(patch)[0][0]
        with self.assertRaisesRegex(ValueError, 'exact unique patch preimage'):
            c.apply(before + old, patch)

    def test_negative_duplicate_patch_application(self):
        patch = c.read(self.review03['integration_patches'][1]).decode()
        with self.assertRaisesRegex(ValueError, 'patch already applied'):
            c.apply(self.source[c.RUST], patch)

    def test_negative_duplicate_public_provider(self):
        entry = c.read(self.review03['entry']).decode()
        self.source_rejected(lambda source: source.__setitem__(c.RUST, source[c.RUST] + entry))

    def test_negative_missing_header_binding(self):
        binding = c.read(self.review03['data_binding']).decode()
        self.source_rejected(lambda source: source.__setitem__('kernel/syscall.c', source['kernel/syscall.c'].replace(binding, '', 1)))

    def test_negative_changed_signal_fp_leaf(self):
        self.source_rejected(lambda source: source.__setitem__(c.LEAF, source[c.LEAF].replace('return -12;', 'return -14;', 1)))

    def test_negative_cmake_selector_drift(self):
        self.source_rejected(lambda source: source.__setitem__(c.CMAKE, source[c.CMAKE].replace('"f06_native_signal_restore_fp_candidate"', '"wrong_cfg"', 1)))

    def test_negative_cmake_shared_anchor_drift(self):
        source_map = c.checked(c.PINS['source117'])
        patch117 = c.read(next(row['patch'] for row in source_map['writes'] if row['relative'] == c.CMAKE)).decode()
        patch118 = c.read(self.review06['integration_patches'][2]).decode()
        source = self.source117[c.CMAKE].replace('"MCKERNEL_RUST_F06_SHMGET_DISPATCH"', '"DRIFT"', 1)
        with self.assertRaises(ValueError):
            c.merge_cmake(self.base[c.CMAKE], source, patch117, patch118)

    def test_negative_arch_source_profile_drift(self):
        self.source_rejected(lambda source: source.__setitem__(c.ARCH, source[c.ARCH] + '\n'))

    def test_negative_stale_command_hash(self):
        self.recipe_rejected(lambda recipe: recipe['ordered_commands'][0].__setitem__('argv_sha256', self.recipe['command_hash_history'][0]['predecessor117_argv_sha256']))

    def test_negative_rehashed_missing_arch_selector(self):
        def mutate(recipe):
            row = recipe['ordered_commands'][2]
            row['argv'].remove('-DMCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP')
            row['argv_sha256'] = c.sha(c.encoder()(row['argv']))
        self.recipe_rejected(mutate)

    def test_negative_origin_output_drift(self):
        self.recipe_rejected(lambda recipe: recipe['prerequisite_origin'].__setitem__('output', '/work/output/build/kernel/f06-origin'))

    def test_negative_retained_object_removal(self):
        self.recipe_rejected(lambda recipe: recipe['retained_inputs'].pop())

    def test_negative_extra_command(self):
        self.recipe_rejected(lambda recipe: recipe['ordered_commands'].append(copy.deepcopy(recipe['ordered_commands'][0])))

    def test_negative_wrong_closure(self):
        self.recipe_rejected(lambda recipe: recipe.__setitem__('expected_closed_source_files', 122))


if __name__ == '__main__':
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Composition)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    raw = stream.getvalue()
    (c.HERE / 'PURE-CONTROLS.stdout').write_text(raw)
    summary = dict(scope=c.SCOPE, status='PASS_PURE_SOURCE_BINDINGS_ONLY' if result.wasSuccessful() else 'FAIL',
                   tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                   compilers=0, fixture_replays=0, origin_producer_invocations=0, canonical_writes=0,
                   runtime_operations=0, stdout=c.ref(c.HERE / 'PURE-CONTROLS.stdout'))
    (c.HERE / 'PURE-CONTROLS.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(raw, end='')
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
