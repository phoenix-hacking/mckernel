from __future__ import print_function

import contextlib
import copy
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import native_rust_kconfig_solver as solver


REPOSITORY_KCONFIG = os.path.join(REPO_ROOT, "host-kernel", "kbuild", "Kconfig")


FAKE_MAKE = r'''#!/usr/bin/env python3
from __future__ import print_function
import json
import os
import re
import sys

CONFIG_SET = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
SYMBOLS = (
    "CONFIG_MODULES",
    "CONFIG_MCKERNEL_IHK_RUST",
    "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST",
    "CONFIG_MCKERNEL_MCCTRL_RUST",
    "CONFIG_RUST",
    "CONFIG_X86_64",
)

arguments = sys.argv[1:]
if len(arguments) != 4:
    print("wrong argument count", file=sys.stderr)
    sys.exit(91)
if arguments[0] != "ARCH=x86_64" or arguments[1] != "LLVM=1":
    print("architecture/toolchain command drift", file=sys.stderr)
    sys.exit(92)
if not arguments[2].startswith("O=/") or arguments[3] != "olddefconfig":
    print("O=/olddefconfig command drift", file=sys.stderr)
    sys.exit(93)
output = arguments[2][2:]
config = os.path.join(output, ".config")
log = os.environ["FAKE_MAKE_LOG"]
with open(log, "a") as stream:
    stream.write(json.dumps({
        "argv": arguments,
        "cwd": os.getcwd(),
        "fixed_environment": dict((name, os.environ.get(name)) for name in ("LANG", "LC_ALL", "TZ")),
        "removed_environment_present": [
            name for name in (
                "ARCH", "GNUMAKEFLAGS", "KBUILD_EXTMOD", "KBUILD_KCONFIG", "KBUILD_OUTPUT",
                "KBUILD_SRC", "KCONFIG_ALLCONFIG", "KCONFIG_CONFIG",
                "KCONFIG_NOSILENTUPDATE", "KCONFIG_OVERWRITECONFIG", "LLVM",
                "MAKEFLAGS", "MAKEFILES", "MAKELEVEL",
                "MFLAGS", "O"
            ) if name in os.environ
        ],
    }, sort_keys=True) + "\n")
with open(log, "r") as stream:
    invocation = sum(1 for line in stream if line)
if os.environ.get("FAKE_FAIL_AT") == str(invocation):
    print("requested fake failure", file=sys.stderr)
    sys.exit(94)

with open(config, "r") as stream:
    lines = stream.read().splitlines()
values = {}
for line in lines:
    match = CONFIG_SET.match(line)
    if match:
        values[match.group(1)] = match.group(2)
        continue
    match = CONFIG_UNSET.match(line)
    if match:
        values[match.group(1)] = "n"
for symbol in SYMBOLS:
    if symbol not in values:
        if symbol.startswith("CONFIG_MCKERNEL_"):
            values[symbol] = "n"
        else:
            print("missing request symbol " + symbol, file=sys.stderr)
            sys.exit(95)

result = dict(values)
if (
    values["CONFIG_MODULES"] != "y"
    or values["CONFIG_RUST"] != "y"
    or values["CONFIG_X86_64"] != "y"
    or values["CONFIG_MCKERNEL_IHK_RUST"] == "n"
):
    result["CONFIG_MCKERNEL_IHK_RUST"] = "n"
    result["CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST"] = "n"
    result["CONFIG_MCKERNEL_MCCTRL_RUST"] = "n"
else:
    result["CONFIG_MCKERNEL_IHK_RUST"] = "m"
    result["CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST"] = (
        "n" if values["CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST"] == "n" else "m"
    )
    result["CONFIG_MCKERNEL_MCCTRL_RUST"] = (
        "n" if values["CONFIG_MCKERNEL_MCCTRL_RUST"] == "n" else "m"
    )
if os.environ.get("FAKE_BAD_X86") == "1":
    result["CONFIG_X86_64"] = "n"

def config_line(symbol, value):
    if value == "n":
        return "# {0} is not set".format(symbol)
    return "{0}={1}".format(symbol, value)

serialized_symbols = list(SYMBOLS)
if (
    result["CONFIG_MODULES"] != "y"
    or result["CONFIG_RUST"] != "y"
    or result["CONFIG_X86_64"] != "y"
):
    serialized_symbols = [
        symbol for symbol in serialized_symbols
        if not symbol.startswith("CONFIG_MCKERNEL_")
    ]
elif result["CONFIG_MCKERNEL_IHK_RUST"] == "n":
    serialized_symbols = [
        symbol for symbol in serialized_symbols
        if symbol not in (
            "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST",
            "CONFIG_MCKERNEL_MCCTRL_RUST",
        )
    ]

payload = "# Deterministic fake Linux olddefconfig output.\n"
payload += "\n".join(
    config_line(symbol, result[symbol]) for symbol in serialized_symbols
) + "\n"
if os.environ.get("FAKE_DRIFT_AT") == str(invocation):
    payload += "# deterministic second-pass drift\n"
with open(config, "w") as stream:
    stream.write(payload)
if os.environ.get("FAKE_SYMLINK_AT") == str(invocation):
    os.unlink(config)
    os.symlink("/dev/null", config)
'''


def write_bytes(path, data, mode=0o600):
    with open(path, "wb") as stream:
        stream.write(data)
    os.chmod(path, mode)


def make_source(root):
    source = os.path.join(root, "linux-source")
    os.mkdir(source)
    write_bytes(
        os.path.join(source, "Makefile"),
        b"VERSION = 6\nPATCHLEVEL = 12\nSUBLEVEL = 0\n",
    )
    staged = os.path.join(source, "drivers", "misc", "mckernel")
    os.makedirs(staged)
    with open(REPOSITORY_KCONFIG, "rb") as stream:
        write_bytes(os.path.join(staged, "Kconfig"), stream.read())
    return source


def make_seed(root):
    seed = os.path.join(root, "seed.config")
    write_bytes(
        seed,
        (
            "# Deterministic generated seed fixture.\n"
            "CONFIG_MODULES=y\n"
            "CONFIG_RUST=y\n"
            "CONFIG_X86_64=y\n"
            "# CONFIG_MCKERNEL_IHK_RUST is not set\n"
            "# CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST is not set\n"
            "# CONFIG_MCKERNEL_MCCTRL_RUST is not set\n"
        ).encode("ascii"),
    )
    return seed


def make_fake_environment(root, log_name="make.log"):
    binary = os.path.join(root, "bin")
    os.mkdir(binary)
    make = os.path.join(binary, "make")
    write_bytes(make, FAKE_MAKE.encode("ascii"), 0o700)
    environment = dict(os.environ)
    environment["PATH"] = binary + os.pathsep + environment.get("PATH", "")
    environment["FAKE_MAKE_LOG"] = os.path.join(root, log_name)
    for name in solver.REMOVED_ENVIRONMENT_KEYS:
        environment[name] = "hostile-fixture-value"
    environment["LANG"] = "hostile-locale"
    environment["LC_ALL"] = "hostile-locale"
    environment["TZ"] = "hostile-timezone"
    return environment


class NativeRustKconfigSolverOracleTests(unittest.TestCase):
    def test_exact_54_case_oracle_and_distribution(self):
        requests = solver.matrix_requests()
        self.assertEqual(54, len(requests))
        self.assertEqual(54, len({solver._case_id(i, row) for i, row in enumerate(requests)}))
        distribution = {0: 0, 1: 0, 2: 0, 3: 0}
        for index, request in enumerate(requests):
            with self.subTest(case=index):
                result = solver.oracle(request)
                selected = sum(
                    result[symbol] == "m" for symbol in solver.MODULE_SYMBOLS
                )
                distribution[selected] += 1
                if request[solver.CONFIG_MODULES] == "n":
                    self.assertEqual(["n", "n", "n"], [result[s] for s in solver.MODULE_SYMBOLS])
                elif request[solver.CONFIG_PROVIDER] == "n":
                    self.assertEqual(["n", "n", "n"], [result[s] for s in solver.MODULE_SYMBOLS])
                else:
                    self.assertEqual("m", result[solver.CONFIG_PROVIDER])
                    for symbol in (solver.CONFIG_SMP, solver.CONFIG_MCCTRL):
                        expected = "n" if request[symbol] == "n" else "m"
                        self.assertEqual(expected, result[symbol])
        self.assertEqual({0: 36, 1: 2, 2: 8, 3: 8}, distribution)

    def test_rust_and_x86_disabled_oracles_are_separate_negatives(self):
        base = {
            solver.CONFIG_MODULES: "y",
            solver.CONFIG_PROVIDER: "y",
            solver.CONFIG_SMP: "y",
            solver.CONFIG_MCCTRL: "y",
            solver.CONFIG_RUST: "y",
            solver.CONFIG_X86_64: "y",
        }
        rust = dict(base)
        rust[solver.CONFIG_RUST] = "n"
        x86 = dict(base)
        x86[solver.CONFIG_X86_64] = "n"
        self.assertEqual(["n"] * 3, [solver.oracle(rust)[s] for s in solver.MODULE_SYMBOLS])
        self.assertEqual(["n"] * 3, [solver.oracle(x86)[s] for s in solver.MODULE_SYMBOLS])

    def test_oracle_rejects_wrong_types_values_and_keys(self):
        request = solver.matrix_requests()[0]
        mutations = []
        wrong_type = dict(request)
        wrong_type[solver.CONFIG_MODULES] = False
        mutations.append(wrong_type)
        wrong_value = dict(request)
        wrong_value[solver.CONFIG_PROVIDER] = "z"
        mutations.append(wrong_value)
        missing = dict(request)
        del missing[solver.CONFIG_MCCTRL]
        mutations.append(missing)
        extra = dict(request)
        extra["CONFIG_EVIL"] = "n"
        mutations.append(extra)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(solver.SolverError):
                    solver.oracle(mutation)

    def test_absent_hidden_project_symbols_resolve_to_n_only(self):
        hidden_menu = (
            b"# CONFIG_MODULES is not set\n"
            b"CONFIG_RUST=y\n"
            b"CONFIG_X86_64=y\n"
        )
        result = solver._extract_result(hidden_menu, "hidden-symbol fixture")
        self.assertEqual("n", result[solver.CONFIG_MODULES])
        self.assertEqual("y", result[solver.CONFIG_RUST])
        self.assertEqual("y", result[solver.CONFIG_X86_64])
        self.assertEqual(
            ["n", "n", "n"],
            [result[symbol] for symbol in solver.MODULE_SYMBOLS],
        )
        provider_disabled = (
            b"CONFIG_MODULES=y\n"
            b"# CONFIG_MCKERNEL_IHK_RUST is not set\n"
            b"CONFIG_RUST=y\n"
            b"CONFIG_X86_64=y\n"
        )
        result = solver._extract_result(
            provider_disabled, "hidden-consumer fixture"
        )
        self.assertEqual(
            ["n", "n", "n"],
            [result[symbol] for symbol in solver.MODULE_SYMBOLS],
        )

    def test_absent_visible_project_symbols_and_prerequisites_fail_closed(self):
        visible_menu = (
            b"CONFIG_MODULES=y\n"
            b"CONFIG_RUST=y\n"
            b"CONFIG_X86_64=y\n"
        )
        with self.assertRaises(solver.SolverError):
            solver._extract_result(visible_menu, "missing-visible-provider fixture")
        visible_consumers = (
            b"CONFIG_MODULES=y\n"
            b"CONFIG_MCKERNEL_IHK_RUST=m\n"
            b"CONFIG_RUST=y\n"
            b"CONFIG_X86_64=y\n"
        )
        with self.assertRaises(solver.SolverError):
            solver._extract_result(
                visible_consumers, "missing-visible-consumers fixture"
            )
        complete_config = (
            b"CONFIG_MODULES=y\n"
            b"# CONFIG_MCKERNEL_IHK_RUST is not set\n"
            b"CONFIG_RUST=y\n"
            b"CONFIG_X86_64=y\n"
        )
        for prerequisite in (
            solver.CONFIG_MODULES,
            solver.CONFIG_RUST,
            solver.CONFIG_X86_64,
        ):
            mutation = b"".join(
                line
                for line in complete_config.splitlines(keepends=True)
                if prerequisite.encode("ascii") not in line
            )
            with self.subTest(missing=prerequisite):
                with self.assertRaises(solver.SolverError):
                    solver._extract_result(mutation, "missing-prerequisite fixture")


class NativeRustKconfigSolverArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="native-rust-kconfig-solver-")
        cls.source = make_source(cls.root)
        cls.seed = make_seed(cls.root)
        cls.environment = make_fake_environment(cls.root)
        cls.matrix_dir = os.path.join(cls.root, "matrix")
        cls.artifact, cls.document = solver.run_solver(
            cls.source, cls.seed, cls.matrix_dir, environ=cls.environment
        )
        with open(cls.artifact, "rb") as stream:
            cls.raw = stream.read()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def rejected_document(self, mutation):
        with self.assertRaises(solver.SolverError):
            solver.validate_matrix_bytes(solver.canonical_json_bytes(mutation))

    def test_runner_emits_canonical_duplicate_free_bound_matrix(self):
        observed = solver.validate_matrix_bytes(self.raw)
        self.assertEqual(self.document, observed)
        self.assertEqual(self.raw, solver.canonical_json_bytes(observed))
        self.assertEqual("captured-unreviewed", observed["status"])
        self.assertEqual(solver.EXPECTED_COUNTS, observed["counts"])
        self.assertEqual(solver.EXPECTED_CLAIMS, observed["claims"])
        self.assertEqual(solver.EXPECTED_LIMITATIONS, observed["limitations"])
        self.assertTrue(all(value is False for value in observed["claims"].values()))
        self.assertEqual(54, len(observed["matrix"]))
        self.assertEqual("6.12", observed["inputs"]["source_makefile"]["linux_version"])
        self.assertEqual(
            "{0:04o}".format(stat.S_IMODE(os.lstat(self.seed).st_mode)),
            observed["inputs"]["seed_config"]["mode"],
        )
        self.assertEqual(
            "{0:04o}".format(stat.S_IMODE(os.lstat(self.source).st_mode)),
            observed["inputs"]["source_tree"]["root_mode"],
        )
        for key in ("source_tree", "staged_kconfig", "seed_config"):
            self.assertRegex(observed["inputs"][key]["sha256"], r"^[0-9a-f]{64}$")

    def test_exact_two_pass_hashes_requests_results_and_counts(self):
        for index, row in enumerate(self.document["matrix"]):
            with self.subTest(case=index):
                self.assertEqual(solver.matrix_requests()[index], row["request"])
                self.assertEqual(solver.oracle(row["request"]), row["result"])
                self.assertEqual(2, len(row["config_sha256_passes"]))
                self.assertEqual(row["config_sha256_passes"][0], row["config_sha256_passes"][1])
                self.assertEqual(row["config_size_passes"][0], row["config_size_passes"][1])
                self.assertTrue(row["byte_identical"])
                self.assertEqual(solver.REPORTED_FACT_SCOPE, row["fact_scope"])
                self.assertEqual("captured-unreviewed", row["status"])
        rust = self.document["negative_checks"]["rust_disabled"]
        self.assertEqual("n", rust["request"][solver.CONFIG_RUST])
        self.assertEqual(["n"] * 3, [rust["result"][s] for s in solver.MODULE_SYMBOLS])
        x86 = self.document["negative_checks"]["x86_64_disabled_fixture"]
        self.assertFalse(x86["executed"])
        self.assertEqual("n", x86["request"][solver.CONFIG_X86_64])
        self.assertEqual("structural-fixture", x86["status"])

    def test_make_command_is_exact_serial_and_uses_fresh_o_directories(self):
        with open(self.environment["FAKE_MAKE_LOG"], "r") as stream:
            rows = [json.loads(line) for line in stream]
        self.assertEqual(110, len(rows))
        output_counts = {}
        for row in rows:
            self.assertEqual(self.source, row["cwd"])
            self.assertEqual("ARCH=x86_64", row["argv"][0])
            self.assertEqual("LLVM=1", row["argv"][1])
            self.assertEqual("olddefconfig", row["argv"][3])
            self.assertTrue(row["argv"][2].startswith("O=" + self.matrix_dir + os.sep))
            self.assertEqual(solver.FIXED_ENVIRONMENT, row["fixed_environment"])
            self.assertEqual([], row["removed_environment_present"])
            output_counts[row["argv"][2]] = output_counts.get(row["argv"][2], 0) + 1
        self.assertEqual(55, len(output_counts))
        self.assertEqual({2}, set(output_counts.values()))

    def test_check_mode_rebinds_all_inputs_and_cli_passes(self):
        checked = solver.check_matrix(self.artifact, self.source, self.seed)
        self.assertEqual(self.document, checked)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            return_code = solver.main(
                [
                    "check",
                    "--matrix",
                    self.artifact,
                    "--source",
                    self.source,
                    "--seed",
                    self.seed,
                ]
            )
        self.assertEqual(0, return_code)
        self.assertIn("CAPTURE-VALIDATED cases=54", output.getvalue())
        self.assertNotIn("PASS", output.getvalue())

    def test_duplicate_noncanonical_and_non_ascii_json_are_rejected(self):
        duplicate = self.raw.replace(b'{"claims":', b'{"claims":{},"claims":', 1)
        variants = (
            duplicate,
            json.dumps(self.document, indent=2, sort_keys=True).encode("ascii") + b"\n",
            self.raw.replace(b"\n", b"\r\n"),
            self.raw[:-1],
            self.raw.replace(b"{", b"{\t", 1),
            self.raw.replace(
                b"captured-unreviewed",
                b"captured-\xe2\x80\xaeunreviewed",
                1,
            ),
        )
        for index, variant in enumerate(variants):
            with self.subTest(index=index):
                with self.assertRaises(solver.SolverError):
                    solver.validate_matrix_bytes(variant)

    def test_schema_type_order_path_hash_result_and_claim_mutations_are_rejected(self):
        mutations = []
        value = copy.deepcopy(self.document)
        value["schema_version"] = True
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["matrix"][0], value["matrix"][1] = value["matrix"][1], value["matrix"][0]
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["inputs"]["staged_kconfig"]["path"] = "drivers/misc/mckernel/../Kconfig"
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["matrix"][0]["config_sha256_passes"][1] = "0" * 64
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["matrix"][27]["result"][solver.CONFIG_PROVIDER] = "m"
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["claims"]["tracker_credit"] = True
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["claims"]["independent_replay_proven"] = True
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["limitations"]["fact_scope"] = "independently reviewed"
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["counts"]["case_count"] = 54.0
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["negative_checks"]["x86_64_disabled_fixture"]["executed"] = True
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["runner"]["argv_template"][1:3] = ["LLVM=1", "ARCH=x86_64"]
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["runner"]["execution"]["serial"] = 1
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["runner"]["fixed_environment"]["TZ"] = "PST8PDT"
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["inputs"]["seed_config"]["mode"] = 600
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["inputs"]["source_tree"]["root_mode"] = "755"
        mutations.append(value)
        value = copy.deepcopy(self.document)
        value["extra"] = False
        mutations.append(value)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.rejected_document(mutation)

    def test_all_distribution_values_reject_float_and_bool_types(self):
        distribution = self.document["counts"]["module_result_distribution"]
        for key in ("0", "1", "2", "3"):
            for kind, replacement in (
                ("float", float(distribution[key])),
                ("bool", bool(distribution[key])),
            ):
                value = copy.deepcopy(self.document)
                value["counts"]["module_result_distribution"][key] = replacement
                with self.subTest(key=key, kind=kind):
                    with self.assertRaises(solver.SolverError):
                        solver.validate_document(value)

    def test_every_reported_size_slot_rejects_float_and_bool_types(self):
        rows = list(enumerate(self.document["matrix"]))
        rows.append(("rust-negative", self.document["negative_checks"]["rust_disabled"]))
        for row_id, row in rows:
            for pass_index in (0, 1):
                original = row["config_size_passes"][pass_index]
                for kind, replacement in (
                    ("float", float(original)),
                    ("bool", bool(original)),
                ):
                    value = copy.deepcopy(self.document)
                    if row_id == "rust-negative":
                        target = value["negative_checks"]["rust_disabled"]
                    else:
                        target = value["matrix"][row_id]
                    target["config_size_passes"][pass_index] = replacement
                    with self.subTest(row=row_id, pass_index=pass_index, kind=kind):
                        with self.assertRaises(solver.SolverError):
                            solver.validate_document(value)

    def test_every_bound_digest_and_mode_rejects_trailing_lf(self):
        input_digests = (
            ("seed_config", "sha256"),
            ("source_makefile", "sha256"),
            ("source_tree", "sha256"),
            ("staged_kconfig", "sha256"),
        )
        for record, field in input_digests:
            value = copy.deepcopy(self.document)
            value["inputs"][record][field] += "\n"
            with self.subTest(scope="input-digest", record=record):
                with self.assertRaises(solver.SolverError):
                    solver.validate_document(value)
        for record, field in (
            ("seed_config", "mode"),
            ("source_tree", "root_mode"),
        ):
            value = copy.deepcopy(self.document)
            value["inputs"][record][field] += "\n"
            with self.subTest(scope="input-mode", record=record):
                with self.assertRaises(solver.SolverError):
                    solver.validate_document(value)
        rows = list(enumerate(self.document["matrix"]))
        rows.append(("rust-negative", self.document["negative_checks"]["rust_disabled"]))
        for row_id, unused_row in rows:
            for pass_index in (0, 1):
                value = copy.deepcopy(self.document)
                if row_id == "rust-negative":
                    target = value["negative_checks"]["rust_disabled"]
                else:
                    target = value["matrix"][row_id]
                target["config_sha256_passes"][pass_index] += "\n"
                with self.subTest(
                    scope="row-digest", row=row_id, pass_index=pass_index
                ):
                    with self.assertRaises(solver.SolverError):
                        solver.validate_document(value)

    def test_check_rejects_seed_and_staged_kconfig_digest_drift(self):
        seed_copy = os.path.join(self.root, "seed-drift.config")
        with open(self.seed, "rb") as stream:
            write_bytes(seed_copy, stream.read() + b"# drift\n")
        with self.assertRaises(solver.SolverError):
            solver.check_matrix(self.artifact, self.source, seed_copy)
        kconfig = os.path.join(self.source, "drivers", "misc", "mckernel", "Kconfig")
        with open(kconfig, "rb") as stream:
            original = stream.read()
        try:
            write_bytes(kconfig, original + b"# digest drift\n")
            with self.assertRaises(solver.SolverError):
                solver.check_matrix(self.artifact, self.source, self.seed)
        finally:
            write_bytes(kconfig, original)

    def test_check_rejects_artifact_symlink_and_wrong_filename(self):
        alias = os.path.join(self.root, "matrix-alias.json")
        os.symlink(self.artifact, alias)
        with self.assertRaises(solver.SolverError):
            solver.check_matrix(alias, self.source, self.seed)
        copied = os.path.join(self.root, "wrong-name.json")
        write_bytes(copied, self.raw)
        with self.assertRaises(solver.SolverError):
            solver.check_matrix(copied, self.source, self.seed)

    def test_check_binds_input_modes_but_not_transported_artifact_mode(self):
        seed_mode = stat.S_IMODE(os.lstat(self.seed).st_mode)
        source_mode = stat.S_IMODE(os.lstat(self.source).st_mode)
        artifact_mode = stat.S_IMODE(os.lstat(self.artifact).st_mode)
        try:
            os.chmod(self.seed, 0o640 if seed_mode != 0o640 else 0o600)
            with self.assertRaises(solver.SolverError):
                solver.check_matrix(self.artifact, self.source, self.seed)
        finally:
            os.chmod(self.seed, seed_mode)
        try:
            os.chmod(self.source, 0o700 if source_mode != 0o700 else 0o755)
            with self.assertRaises(solver.SolverError):
                solver.check_matrix(self.artifact, self.source, self.seed)
        finally:
            os.chmod(self.source, source_mode)
        try:
            os.chmod(self.artifact, 0o600 if artifact_mode != 0o600 else 0o400)
            self.assertEqual(
                self.document,
                solver.check_matrix(self.artifact, self.source, self.seed),
            )
        finally:
            os.chmod(self.artifact, artifact_mode)


class NativeRustKconfigSolverFailureTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="native-rust-kconfig-solver-failure-")
        self.source = make_source(self.root)
        self.seed = make_seed(self.root)
        self.environment = make_fake_environment(self.root)
        self.serial = 0

    def tearDown(self):
        shutil.rmtree(self.root)

    def failed_run(self, environment_updates=None, source=None, seed=None):
        self.serial += 1
        environment = dict(self.environment)
        environment["FAKE_MAKE_LOG"] = os.path.join(self.root, "failure-{0}.log".format(self.serial))
        if environment_updates:
            environment.update(environment_updates)
        matrix = os.path.join(self.root, "matrix-{0}".format(self.serial))
        with self.assertRaises(solver.SolverError):
            solver.run_solver(
                self.source if source is None else source,
                self.seed if seed is None else seed,
                matrix,
                environ=environment,
            )

    def test_make_nonzero_and_missing_command_fail_closed(self):
        self.failed_run({"FAKE_FAIL_AT": "1"})
        self.failed_run({"PATH": os.path.join(self.root, "missing-bin")})

    def test_matrix_basename_with_trailing_lf_is_rejected(self):
        matrix = os.path.join(self.root, "matrix-newline\n")
        with self.assertRaises(solver.SolverError):
            solver.run_solver(
                self.source,
                self.seed,
                matrix,
                environ=self.environment,
            )
        self.assertFalse(os.path.lexists(matrix))

    def test_same_inode_same_size_restored_mtime_mid_read_is_rejected(self):
        path = os.path.join(self.root, "mid-read.config")
        payload = b"A" * (1024 * 1024) + b"B" * (1024 * 1024) + b"\n"
        write_bytes(path, payload)
        before = os.stat(path)
        real_read = os.read
        changed = [False]

        def read_then_mutate(descriptor, count):
            chunk = real_read(descriptor, count)
            if chunk and not changed[0]:
                changed[0] = True
                with open(path, "r+b") as stream:
                    stream.seek(1024 * 1024 + 17)
                    stream.write(b"C")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
            return chunk

        with mock.patch.object(solver.os, "read", side_effect=read_then_mutate):
            with self.assertRaises(solver.SolverError):
                solver._read_regular_file(path, "mid-read config")
        after = os.stat(path)
        self.assertTrue(changed[0])
        self.assertEqual(
            (
                before.st_dev,
                before.st_ino,
                before.st_mode,
                before.st_size,
                before.st_mtime_ns,
            ),
            (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
            ),
        )
        self.assertNotEqual(before.st_ctime_ns, after.st_ctime_ns)

    def test_second_pass_byte_drift_fails_closed(self):
        self.failed_run({"FAKE_DRIFT_AT": "2"})

    def test_symlinked_make_output_fails_closed(self):
        self.failed_run({"FAKE_SYMLINK_AT": "1"})

    def test_x86_output_contradicting_arch_fixture_fails_closed(self):
        self.failed_run({"FAKE_BAD_X86": "1"})

    def test_source_seed_matrix_and_source_entry_symlinks_fail_closed(self):
        source_link = os.path.join(self.root, "source-link")
        os.symlink(self.source, source_link)
        self.failed_run(source=source_link)
        seed_link = os.path.join(self.root, "seed-link.config")
        os.symlink(self.seed, seed_link)
        self.failed_run(seed=seed_link)
        escaping = os.path.join(self.source, "escaping-link")
        os.symlink("/etc/passwd", escaping)
        try:
            self.failed_run()
        finally:
            os.unlink(escaping)
        existing = os.path.join(self.root, "matrix-existing")
        os.mkdir(existing)
        with self.assertRaises(solver.SolverError):
            solver.run_solver(self.source, self.seed, existing, environ=self.environment)

    def test_seed_duplicate_missing_prerequisite_and_bad_bytes_fail_closed(self):
        with open(self.seed, "rb") as stream:
            original = stream.read()
        mutations = (
            original + b"CONFIG_RUST=y\n",
            original.replace(b"CONFIG_RUST=y\n", b"# CONFIG_RUST is not set\n"),
            original.replace(b"CONFIG_X86_64=y\n", b""),
            original.rstrip(b"\n"),
            original.replace(b"CONFIG_MODULES", b"CONFIG_\tMODULES", 1),
            original.replace(b"CONFIG_MODULES", b"CONFIG_\x00MODULES", 1),
            original + b"ARCH=x86_64\n",
        )
        for index, payload in enumerate(mutations):
            path = os.path.join(self.root, "bad-seed-{0}.config".format(index))
            write_bytes(path, payload)
            with self.subTest(index=index):
                self.failed_run(seed=path)

    def test_source_version_and_staged_policy_mutations_fail_closed(self):
        makefile = os.path.join(self.source, "Makefile")
        with open(makefile, "rb") as stream:
            original_makefile = stream.read()
        try:
            write_bytes(makefile, original_makefile.replace(b"PATCHLEVEL = 12", b"PATCHLEVEL = 11"))
            self.failed_run()
        finally:
            write_bytes(makefile, original_makefile)
        kconfig = os.path.join(self.source, "drivers", "misc", "mckernel", "Kconfig")
        with open(kconfig, "rb") as stream:
            original_kconfig = stream.read()
        try:
            write_bytes(kconfig, original_kconfig.replace(b"\tdepends on X86_64\n", b"", 1))
            self.failed_run()
        finally:
            write_bytes(kconfig, original_kconfig)

    def test_requested_config_rejects_duplicate_seed_and_request_type(self):
        with open(self.seed, "rb") as stream:
            seed = stream.read()
        request = solver.matrix_requests()[0]
        with self.assertRaises(solver.SolverError):
            solver.requested_config(seed + b"CONFIG_RUST=y\n", request)
        wrong = dict(request)
        wrong[solver.CONFIG_PROVIDER] = 1
        with self.assertRaises(solver.SolverError):
            solver.requested_config(seed, wrong)


if __name__ == "__main__":
    unittest.main()
