import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import mckernel_syscall_offload_check as checker


def passing_tables():
    rust = {symbol: ["T"] for symbol in checker.RUST_DEFINITIONS}
    rust.update({symbol: ["U"] for symbol in checker.RUST_REQUIRED_IMPORTS})
    c_object = {symbol: ["U"] for symbol in checker.C_IMPORTS}
    c_object.update({symbol: ["T"] for symbol in checker.C_RETAINED_DEFINITIONS})
    image = {symbol: ["T"] for symbol in checker.RUST_DEFINITIONS}
    image.update({symbol: ["T"] for symbol in checker.C_RETAINED_DEFINITIONS})
    return rust, c_object, image


class SyscallOffloadCheckTests(unittest.TestCase):
    COMMIT = "0123456789abcdef0123456789abcdef01234567"

    def test_parse_nm_accepts_defined_and_undefined_global_symbols(self):
        symbols = checker.parse_nm(
            "0000000000001000 T send_syscall\n"
            "                 U do_syscall\n"
            "0000000000002000 W alias\n"
        )
        self.assertEqual(symbols["send_syscall"], ["T"])
        self.assertEqual(symbols["do_syscall"], ["U"])
        self.assertEqual(symbols["alias"], ["W"])

    def test_production_contract_passes(self):
        checker.check_contract(*passing_tables())

    def test_missing_rust_definition_is_rejected(self):
        rust, c_object, image = passing_tables()
        del rust["send_syscall"]
        with self.assertRaisesRegex(ValueError, "send_syscall"):
            checker.check_contract(rust, c_object, image)

    def test_c_definition_instead_of_import_is_rejected(self):
        rust, c_object, image = passing_tables()
        c_object["syscall_generic_forwarding"] = ["T"]
        with self.assertRaisesRegex(ValueError, "unexpectedly defines"):
            checker.check_contract(rust, c_object, image)

    def test_residual_local_c_definition_is_rejected_even_with_import(self):
        rust, c_object, image = passing_tables()
        c_object["send_syscall"] = ["t", "U"]
        with self.assertRaisesRegex(ValueError, "unexpectedly defines"):
            checker.check_contract(rust, c_object, image)

    def test_missing_retained_c_seam_is_rejected(self):
        rust, c_object, image = passing_tables()
        del c_object["do_syscall"]
        with self.assertRaisesRegex(ValueError, "do_syscall"):
            checker.check_contract(rust, c_object, image)

    def test_duplicate_or_unresolved_final_definition_is_rejected(self):
        rust, c_object, image = passing_tables()
        image["syscall_offload_wait_reply"] = ["T", "T"]
        with self.assertRaisesRegex(ValueError, "exactly one"):
            checker.check_contract(rust, c_object, image)
        image["syscall_offload_wait_reply"] = ["T", "U"]
        with self.assertRaisesRegex(ValueError, "exactly one"):
            checker.check_contract(rust, c_object, image)

    def test_build_report_hashes_exact_production_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory)
            artifacts = (
                build / "kernel/rust/mckernel_rust.o",
                build / "kernel/CMakeFiles/mckernel.img.dir/syscall.c.o",
                build / "kernel/mckernel.img",
            )
            for artifact in artifacts:
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_bytes(artifact.name.encode("ascii"))
            tables = passing_tables()
            with mock.patch.object(checker, "run_nm", side_effect=tables):
                report = checker.build_report(build, self.COMMIT.upper())

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["source_commit"], self.COMMIT)
        self.assertEqual(
            set(report["artifacts"]),
            {"rust_object", "c_syscall_object", "image"},
        )


if __name__ == "__main__":
    unittest.main()
