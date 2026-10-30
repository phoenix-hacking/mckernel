#!/usr/bin/python3
"""Unrun synthetic source regression; requires separate reviewed process grant.

Uses small temporary data and one sparse oversized file. No compiler, toolchain
inventory, source staging or host execution. The parent retains all outputs.
"""
import hashlib, importlib.util, os, pathlib, tempfile, unittest

HERE=pathlib.Path(__file__).absolute().parent
spec=importlib.util.spec_from_file_location('collector_under_test',HERE/'collect_host_toolchain_v8.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def bound(path):
    st=path.stat()
    return {'identity':[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,st.st_mode,st.st_uid], 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


class CollectorInputTests(unittest.TestCase):
    def setUp(self): self.root=pathlib.Path(tempfile.mkdtemp(prefix='m14-collector-v8-'))
    def test_inventory_linker_script_and_selected_refusal(self):
        target=self.root/'libLLVM.so.22.1-rust-1.95.0-nightly';target.write_bytes(b'fixture')
        script=self.root/'libLLVM-22-rust-1.95.0-nightly.so';script.write_bytes(b'INPUT(libLLVM.so.22.1-rust-1.95.0-nightly)\n')
        result=c.classify_nonelf(script,bound(script),False)
        self.assertEqual(result['kind'],'linker_input_script');self.assertEqual(result['size'],43)
        self.assertEqual(result['target'],str(target))
        with self.assertRaisesRegex(RuntimeError,'selected dependency is non-ELF'):c.classify_nonelf(script,bound(script),True)
    def test_tiny_elf_and_unknown_nonelf_fail_closed(self):
        path=self.root/'tiny';path.write_bytes(b'\x7fELF')
        with self.assertRaisesRegex(RuntimeError,'size=4'):c.elf_dynamic(path)
        path.write_bytes(b'not a supported input')
        with self.assertRaisesRegex(RuntimeError,'unsupported non-ELF'):c.classify_nonelf(path,bound(path),False)
    def test_oversized_elf_rejected_before_mapping(self):
        path=self.root/'large'
        with path.open('wb') as f: f.truncate(c.MAX_ELF_BYTES+1)
        with self.assertRaisesRegex(RuntimeError,'size=536870913'):c.elf_dynamic(path)


if __name__=='__main__': unittest.main()
