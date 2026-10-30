"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
UNRUN small synthetic regression fixtures for the exact source projection oracle.
No original held content, compiler, subprocess or physical operation is used.
"""
import unittest
from exact_projection import Hunk,ProjectionError,parse_patch,construct,validate_exact,expected_host,validate_outputs

HOST=(b'unchanged outside prefix\n#[no_mangle]\npub unsafe extern "C" fn mcexec_util_thread_body(\n'
 b') {\n    unsafe {\n        (*uti_desc).uti_info = uti_info;\n    }\n'
 b'    synthetic_size_and_attribute_checks();\n'
 b'    unsafe {\n        (*uti_desc).start_syscall_intercept = 1;\n    }\n}\n'
 b'\n#[no_mangle]\nunchanged outside suffix\n')

def fixture():
    c=b'unchanged prefix\nold function\nunchanged held placeholder\n'
    h=Hunk(2,1,2,1,b'old function\n',b'new function\n')
    host,body=expected_host(HOST)
    hh=Hunk(1,HOST.count(b'\n'),1,host.count(b'\n'),HOST,host)
    staged={'kernel/syscall.c':construct(c,[h]),'kernel/rust/syscall_policy.rs':b'rust base\n\ncombined\n',
            'kernel/rust/f03_request_constructors.rs':b'constructor\n','host_function':body,'host_postimage':host}
    return c,h,hh,staged

def validate_fixture(staged=None,host_hunks=None,combined=b'combined\n'):
    c,h,hh,default=fixture()
    validate_outputs(c,[h],b'rust base\n',combined,b'combined\n',b'constructor\n',default if staged is None else staged,HOST,[hh] if host_hunks is None else host_hunks)

class ExactProjectionTests(unittest.TestCase):
    def test_positive_complete_projection(self):
        validate_fixture()

    def test_deletion_only_fake_is_rejected(self):
        patch=b'--- a/x\n+++ b/x\n@@ -2 +1,0 @@\n-delete me\n'
        hunks=parse_patch(patch)['x']
        base=b'keep\ndelete me\nlast\n'
        self.assertEqual(construct(base,hunks),b'keep\nlast\n')
        with self.assertRaises(ProjectionError):validate_exact(base,hunks,base)

    def test_extraneous_held_c_change_is_rejected(self):
        _,_,_,staged=fixture()
        staged['kernel/syscall.c']=staged['kernel/syscall.c'].replace(b'unchanged held placeholder',b'extraneous changed placeholder')
        with self.assertRaises(ProjectionError):validate_fixture(staged)

    def test_missing_rust_append_is_rejected(self):
        _,_,_,staged=fixture();staged['kernel/rust/syscall_policy.rs']=b'rust base\n'
        with self.assertRaises(ProjectionError):validate_fixture(staged)

    def test_extraneous_combined_rust_is_rejected(self):
        with self.assertRaises(ProjectionError):validate_fixture(combined=b'combined\nextraneous\n')

    def test_changed_rust_base_is_rejected(self):
        _,_,_,staged=fixture();staged['kernel/rust/syscall_policy.rs']=b'changed base\n\ncombined\n'
        with self.assertRaises(ProjectionError):validate_fixture(staged)

    def test_repeated_anchor_is_rejected(self):
        h=Hunk(1,1,1,1,b'repeated\n',b'changed\n')
        with self.assertRaises(ProjectionError):construct(b'repeated\nrepeated\n',[h])

    def test_overlapping_unique_anchors_are_rejected(self):
        a=Hunk(1,2,1,1,b'a\nb\n',b'first\n')
        b=Hunk(2,2,2,1,b'b\nc\n',b'second\n')
        with self.assertRaises(ProjectionError):construct(b'a\nb\nc\n',[a,b])

    def test_repeated_hunk_is_rejected(self):
        c,h,_,_=fixture()
        with self.assertRaises(ProjectionError):construct(c,[h,h])

    def test_host_outside_diff_is_rejected(self):
        _,_,hh,staged=fixture()
        bad=hh.new.replace(b'unchanged outside suffix',b'extraneous outside change')
        altered=Hunk(hh.old_line,hh.old_count,hh.new_line,bad.count(b'\n'),hh.old,bad)
        staged['host_postimage']=bad
        with self.assertRaises(ProjectionError):validate_fixture(staged,[altered])

    def test_host_function_diff_is_rejected(self):
        _,_,_,staged=fixture();staged['host_function']+=b'// extra\n'
        with self.assertRaises(ProjectionError):validate_fixture(staged)

    def test_constructor_diff_is_rejected(self):
        _,_,_,staged=fixture();staged['kernel/rust/f03_request_constructors.rs']=b'changed constructor\n'
        with self.assertRaises(ProjectionError):validate_fixture(staged)

    def test_extra_staged_source_path_is_rejected(self):
        _,_,_,staged=fixture();staged['unapproved/source.rs']=b'extraneous\n'
        with self.assertRaises(ProjectionError):validate_fixture(staged)

    def test_malformed_patch_count_is_rejected(self):
        with self.assertRaises(ProjectionError):parse_patch(b'--- a/x\n+++ b/x\n@@ -1,2 +1 @@\n-one\n+two\n')

    def test_wrong_exact_source_line_is_rejected(self):
        h=Hunk(2,1,1,1,b'a\n',b'changed\n')
        with self.assertRaises(ProjectionError):construct(b'a\nb\n',[h])

    def test_new_file_section_parses_exactly(self):
        patch=b'--- /dev/null\n+++ b/new.rs\n@@ -0,0 +1,2 @@\n+line one\n+line two\n'
        parsed=parse_patch(patch)['new.rs']
        self.assertEqual(len(parsed),1)
        self.assertEqual(parsed[0].old,b'')
        self.assertEqual(parsed[0].new,b'line one\nline two\n')

    def test_hunk_resource_bound_is_enforced(self):
        c,h,_,_=fixture()
        with self.assertRaises(ProjectionError):construct(c,[h]*17)

if __name__=='__main__':unittest.main()
