"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure file/parser fixtures only. Fake SDK files are explicitly synthetic.
"""
import copy
import json
from pathlib import Path
import shlex
import tempfile
import unittest

import prelink_reuse_guard as guard


HERE = Path(__file__).resolve().parent
CANONICAL = Path('/home/holden/mckernel')


class ReuseGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='.pure-', dir=HERE)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.accepted = self.root / 'accepted-sdk11'
        self.build = self.root / 'build'
        self.contract = json.loads((HERE / 'PRELINK-CONTRACT.json').read_bytes())
        for relative in self.contract['current_source_files']:
            data = ((HERE / 'CMakeLists.txt.candidate').read_bytes()
                    if relative == 'ihk/linux/user/CMakeLists.txt'
                    else (CANONICAL / relative).read_bytes())
            self.write(self.source / relative, data)
        self.old_config = (Path(self.contract['accepted_sdk_host_root']) / 'ihk/config.h').read_bytes()
        for relative in self.contract['accepted_sdk_files']:
            # Fake archive/object/metadata never count as compiled behavior.
            data = self.old_config if relative == 'ihk/config.h' else ('SYNTHETIC:' + relative).encode()
            self.write(self.accepted / relative, data)
            self.contract['accepted_sdk_files'][relative] = dict(bytes=len(data), sha256=guard.digest(data))
        self.write(self.build / 'ihk/config.h', self.old_config)
        self.user = self.build / 'ihk/linux/user'
        for target, tokens in self.contract['generated_link_tokens'].items():
            self.write(self.user / ('CMakeFiles/' + target + '.dir/link.txt'),
                       (shlex.join(tokens) + '\n').encode())
        self.install = []
        for component, rule in self.contract['install_contract'].items():
            destination, kind, source = rule['install']
            path, before, after = rule['rpath_change']
            self.install += [
                'if(CMAKE_INSTALL_COMPONENT STREQUAL "' + component + '" OR NOT CMAKE_INSTALL_COMPONENT)',
                '  file(INSTALL DESTINATION "' + destination + '" TYPE ' + kind + ' FILES "' + source + '")',
                '  if(EXISTS "' + path + '")',
                '    file(RPATH_CHANGE FILE "' + path + '" OLD_RPATH "' + before + '" NEW_RPATH "' + after + '")',
                '  endif()', 'endif()']
        self.install_text = '\n'.join(self.install) + '\n'
        self.write(self.user / 'cmake_install.cmake', self.install_text.encode())

    @staticmethod
    def write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def run_guard(self):
        return guard.validate(self.contract, self.source, self.accepted, self.build)

    def test_identical_positive(self):
        result = self.run_guard()
        self.assertEqual(result['config']['mode'], 'IDENTICAL')
        self.assertFalse(result['current_artifact'])
        self.assertFalse(result['native'])

    def test_current_equal_capacity_buildid_positive(self):
        self.write(self.build / 'ihk/config.h', self.old_config.replace(b'"3114d9e"', b'"a7ddca2"'))
        result = self.run_guard()
        self.assertEqual(result['config']['mode'], 'ONLY_EQUAL_CAPACITY_BUILDID')
        self.assertEqual(result['config']['capacity'], 8)

    def test_config_negative_controls(self):
        cases = {
            'capacity': self.old_config.replace(b'"3114d9e"', b'"longer-id"'),
            'feature': self.old_config.replace(b'#define ENABLE_MEMDUMP 1', b'#define ENABLE_MEMDUMP 0'),
            'duplicate': self.old_config + b'#define BUILDID "3114d9e"\n',
            'unsupported_duplicate': self.old_config + b' # define BUILDID 123\n',
            'non_ascii': self.old_config.replace(b'"3114d9e"', b'"123456\xff"'),
            'numeric': self.old_config.replace(b'"3114d9e"', b'3114'),
        }
        for name, data in cases.items():
            with self.subTest(name=name):
                self.write(self.build / 'ihk/config.h', data)
                with self.assertRaises(ValueError):
                    self.run_guard()

    def test_link_negative_controls(self):
        original = copy.deepcopy(self.contract['generated_link_tokens'])
        controls = []
        library = original['ihklib']
        cli = original['ihkconfig']
        controls.append(('ihklib', [x for x in library if x != '-Wl,--undefined=ihk_os_boot']))
        controls.append(('ihklib', library + ['old/ihklib.c.o']))
        controls.append(('ihklib', library + ['-Wl,--allow-shlib-undefined']))
        controls.append(('ihklib', [x.replace('/accepted-sdk11/', '/wrong-sdk/') for x in library]))
        controls.append(('ihklib', [x for x in library if x != '-lgcc_s']))
        swapped = list(library)
        a, b = swapped.index('-lrt'), swapped.index('-lutil')
        swapped[a], swapped[b] = swapped[b], swapped[a]
        controls.append(('ihklib', swapped))
        controls.append(('ihkconfig', [x.replace('rust/ihkconfig.o', 'ihkconfig.c.o') for x in cli]))
        controls.append(('ihkconfig', [x.replace('libihk.so', '/other/libihk.so') for x in cli]))
        controls.append(('ihkconfig', ['/other/cc'] + cli[1:]))
        for index, (target, tokens) in enumerate(controls):
            with self.subTest(index=index, target=target):
                data = (shlex.join(tokens) + '\n').encode()
                good = {name: (shlex.join(values) + '\n').encode() for name, values in original.items()}
                good[target] = data
                with self.assertRaisesRegex(ValueError, 'generated link'):
                    guard.validate_links(self.contract, good['ihklib'], good['ihkconfig'])
        with self.assertRaisesRegex(ValueError, 'one generated link command'):
            guard.validate_links(self.contract, (shlex.join(library) + '\nother-command\n').encode(),
                                 (shlex.join(cli) + '\n').encode())

    def test_install_negative_controls(self):
        cases = [
            self.install_text.replace('ihkconfig_runtime', 'Unspecified'),
            self.install_text.replace('TYPE EXECUTABLE', 'TYPE FILE'),
            self.install_text.replace('NEW_RPATH "/usr/local/lib64"', 'NEW_RPATH "/other"'),
            self.install_text + self.install_text,
            self.install_text.replace('OR NOT CMAKE_INSTALL_COMPONENT', ''),
            self.install_text.replace('TYPE EXECUTABLE FILES "', 'TYPE EXECUTABLE FILES "/other/'),
        ]
        for index, text in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    guard.validate_install(self.contract, text)

    def test_source_sdk_header_negative_controls(self):
        paths = [self.source / 'ihk/linux/user/rust/build_ihkconfig.py',
                 self.source / 'ihk/linux/include/ihk/ihklib.h',
                 self.accepted / 'ihk/linux/user/rust/ihkconfig.o',
                 self.accepted / 'ihk/linux/user/rust/whole70/libihklib_whole70.a',
                 self.accepted / 'ihk/linux/user/rust/whole70/dump_abi.rs']
        for path in paths:
            with self.subTest(relative=str(path.relative_to(self.root))):
                old = path.read_bytes()
                path.write_bytes(old + b'changed')
                with self.assertRaises(ValueError):
                    self.run_guard()
                path.write_bytes(old)
        for path in [self.source / 'ihk/linux/include/new-unbound.h',
                     self.build / 'ihk/linux/include/new-generated.h']:
            with self.subTest(relative=str(path.relative_to(self.root))):
                self.write(path, b'new')
                with self.assertRaisesRegex(ValueError, 'membership'):
                    self.run_guard()
                path.unlink()

    def test_real_retained_sdk_rules_are_not_current_rules(self):
        sdk_user = Path(self.contract['accepted_sdk_host_root']) / 'ihk/linux/user'
        with self.assertRaisesRegex(ValueError, 'generated link'):
            guard.validate_links(self.contract,
                                 (sdk_user / 'CMakeFiles/ihklib.dir/link.txt').read_bytes(),
                                 (sdk_user / 'CMakeFiles/ihkconfig.dir/link.txt').read_bytes())
        with self.assertRaisesRegex(ValueError, 'component arm'):
            guard.validate_install(self.contract, (sdk_user / 'cmake_install.cmake').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
