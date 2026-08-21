import copy
import io
import json
import os
import tarfile
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import host_module_failure_semantics_v3 as semantics


EMPTY_SHA = semantics.sha256_bytes(b"")


class SyntheticRawFixture:
    def __init__(self):
        self.payloads = {}
        self.sources = {}
        self.unresolved = []
        self.invocations = []
        self.files = []
        self.c_toolchains = []
        object_record = {"bytes": 4, "sha256": semantics.sha256_bytes(b"OBJ\n")}
        for number in range(semantics.EXPECTED_C_SOURCE_COUNT):
            source = "synthetic/c{0}.c".format(number)
            argv = [
                "gcc", "-c", "-o", "/tmp/c{0}.o".format(number),
                "/repo/" + source,
            ]
            compiler = {
                "bytes": 10,
                "invoked_as": "gcc",
                "resolved_path": "/usr/bin/gcc",
                "sha256": "1" * 64,
                "version_first_line": "gcc synthetic",
                "version_stderr_sha256": EMPTY_SHA,
                "version_stdout_sha256": "2" * 64,
            }
            self.sources[source] = {
                "compile_argv": argv,
                "digests": {"compiler_sha256": "1" * 64},
                "language": "c",
                "module": "mcctrl",
                "preprocessor": compiler,
                "source": source,
            }
            self.unresolved.append(
                {
                    "function": "f{0}".format(number),
                    "kind": "return_value_error_domain_unresolved",
                    "line": number + 1,
                    "source": source,
                }
            )
            dumps = {}
            prefix = "c/{0}".format(number)
            for label, _, _ in semantics.C_DUMP_OPTIONS:
                path = "{0}/{1}.txt".format(prefix, label)
                data = (label + "\n").encode("ascii")
                self.payloads[path] = data
                binding = {"bytes": len(data), "path": path, "sha256": semantics.sha256_bytes(data)}
                dumps[label] = dict(binding)
                self.files.append({"kind": "c_" + label, "source": source, **binding})
            baseline_argv = [
                "gcc", "-c", "-fno-diagnostics-color", "-o", "$OUTPUT",
                "$REPO/" + source,
            ]
            replay_argv = ["gcc", "-c"] + [
                option for _, option, _ in semantics.C_DUMP_OPTIONS
            ] + [
                "-fno-diagnostics-color", "-o", "$OUTPUT", "$REPO/" + source,
            ]
            self.invocations.append(
                {
                    "baseline_stderr_sha256": EMPTY_SHA,
                    "baseline_stdout_sha256": EMPTY_SHA,
                    "compiler_sha256": "1" * 64,
                    "dumps": dumps,
                    "language": "c",
                    "normalized_baseline_argv": baseline_argv,
                    "normalized_baseline_argv_sha256": semantics.sha256_bytes(
                        semantics.canonical_bytes(baseline_argv)
                    ),
                    "normalized_replay_argv": replay_argv,
                    "normalized_replay_argv_sha256": semantics.sha256_bytes(
                        semantics.canonical_bytes(replay_argv)
                    ),
                    "production_object": dict(object_record),
                    "production_object_kind": "recorded_profile_side_effect_free_replay",
                    "recorded_argv": argv,
                    "recorded_argv_sha256": semantics.sha256_bytes(semantics.canonical_bytes(argv)),
                    "replay_object": dict(object_record),
                    "object_byte_equality": True,
                    "source": source,
                    "stderr_sha256": EMPTY_SHA,
                    "stdout_sha256": EMPTY_SHA,
                    "two_run_normalized_determinism": True,
                }
            )
            self.c_toolchains.append({"compiler": compiler, "source": source})

        rust_source = "executer/kernel/mcctrl/rust/mcctrl_helpers.rs"
        rust_argv = [
            "/home/validator/.cargo/bin/rustc", "--emit=obj=/tmp/rust.o",
            "/repo/" + rust_source,
        ]
        rust_compiler = {
            "bytes": 645792,
            "invoked_as": rust_argv[0],
            "launcher": {
                "bytes": 20838840,
                "resolved_path": "/home/validator/.cargo/bin/rustup",
                "sha256": semantics.EXPECTED_RUST["launcher_sha256"],
            },
            "resolved_path": "/toolchain/bin/rustc",
            "sha256": semantics.EXPECTED_RUST["compiler_sha256"],
            "version_first_line": semantics.EXPECTED_RUST["version_first_line"],
            "version_stderr_sha256": EMPTY_SHA,
            "version_stdout_sha256": "3" * 64,
        }
        self.sources[rust_source] = {
            "compile_argv": rust_argv,
            "digests": {
                "compiler_sha256": semantics.EXPECTED_RUST["compiler_sha256"],
                "recorded_compile_argv_sha256": semantics.EXPECTED_RUST["argv_sha256"],
            },
            "language": "rust",
            "module": "mcctrl",
            "recorded_compiler": rust_compiler,
            "source": rust_source,
        }
        mir_path = "rust/mir/demo.mir"
        mir_data = b"fn demo() {\n bb0: { return; }\n}\n"
        self.payloads[mir_path] = mir_data
        mir_binding = {
            "bytes": len(mir_data),
            "compiler_path": "crate.demo.built.after.mir",
            "path": mir_path,
            "sha256": semantics.sha256_bytes(mir_data),
        }
        self.files.append(
            {
                "bytes": mir_binding["bytes"],
                "kind": "rust_mir",
                "path": mir_binding["path"],
                "sha256": mir_binding["sha256"],
                "source": rust_source,
            }
        )
        rust_replay = [
            rust_argv[0], "--emit=obj=$OUTPUT", "$REPO/" + rust_source,
            "-Zdump-mir=all", "-Zdump-mir-exclude-pass-number",
            "-Zdump-mir-dir=$SEMANTIC/mir",
        ]
        self.invocations.append(
            {
                "compiler_sha256": semantics.EXPECTED_RUST["compiler_sha256"],
                "language": "rust",
                "mir_files": [mir_binding],
                "normalized_replay_argv": rust_replay,
                "normalized_replay_argv_sha256": semantics.sha256_bytes(semantics.canonical_bytes(rust_replay)),
                "production_object": dict(object_record),
                "production_object_kind": "built_rust_object",
                "recorded_argv": rust_argv,
                "recorded_argv_sha256": semantics.sha256_bytes(semantics.canonical_bytes(rust_argv)),
                "replay_object": dict(object_record),
                "object_byte_equality": True,
                "source": rust_source,
                "stderr_sha256": EMPTY_SHA,
                "stdout_sha256": EMPTY_SHA,
                "two_run_normalized_determinism": True,
            }
        )
        self.inputs = {
            "authority_mode": semantics.flows_v2.HISTORICAL_AUTHORITY_MODE,
            "flow_v1": {
                "profile": "v1",
                "schema_version": 1,
                "unresolved_paths": self.unresolved,
            },
            "flow_v1_file": {"artifact_bytes": 1, "artifact_sha256": "4" * 64},
            "flow_v2": {"profile": "v2", "schema_version": 2},
            "flow_v2_file": {"artifact_bytes": 2, "artifact_sha256": "5" * 64},
            "hfs": {"profile": "hfs", "schema_version": 1},
            "hfs_file": {"artifact_bytes": 3, "artifact_sha256": "6" * 64},
            "sources": self.sources,
        }
        self.manifest = {
            "authority_mode": self.inputs["authority_mode"],
            "compiler_invocations": sorted(self.invocations, key=lambda item: (item["language"], item["source"])),
            "files": sorted(self.files, key=lambda item: item["path"]),
            "generator": "scripts/host_module_failure_semantics_v3.py",
            "inputs": semantics.manifest_input_bindings(self.inputs),
            "profile": semantics.RAW_PROFILE,
            "schema_version": semantics.RAW_SCHEMA_VERSION,
            "toolchains": {
                "c": sorted(self.c_toolchains, key=lambda item: item["source"]),
                "rust": {
                    "compiler": rust_compiler,
                    "mir_option_probe": {
                        "stderr_sha256": EMPTY_SHA,
                        "stdout_sha256": "7" * 64,
                    },
                },
            },
        }
        self.payloads["manifest.json"] = semantics.canonical_bytes(self.manifest)


class CanonicalBundleTests(unittest.TestCase):
    def raw_pair(self, root):
        bundle_root = root / "bundle-authority"
        sidecar_root = root / "sidecar-authority"
        bundle_root.mkdir()
        sidecar_root.mkdir()
        bundle_data = semantics.canonical_tar({"manifest.json": b"{}\n"})
        bundle = bundle_root / "raw.tar"
        sidecar = sidecar_root / "raw.tar.sha256"
        bundle.write_bytes(bundle_data)
        sidecar.write_bytes(semantics.raw_sidecar_bytes(bundle.name, bundle_data))
        return bundle, sidecar

    def test_canonical_tar_and_sidecar_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payloads = {"manifest.json": b"{}\n", "raw/demo.txt": b"demo\n"}
            bundle = semantics.canonical_tar(payloads)
            bundle_path = root / "bundle.tar"
            sidecar_path = root / "bundle.tar.sha256"
            bundle_path.write_bytes(bundle)
            sidecar_path.write_bytes(semantics.raw_sidecar_bytes(bundle_path.name, bundle))
            manifest, observed, record = semantics.read_raw_bundle(bundle_path, sidecar_path)
            self.assertEqual(manifest, {})
            self.assertEqual(observed, payloads)
            self.assertEqual(record["artifact_sha256"], semantics.sha256_bytes(bundle))

    def test_checksum_path_and_digest_mutations_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = semantics.canonical_tar({"manifest.json": b"{}\n"})
            bundle_path = root / "bundle.tar"
            sidecar_path = root / "bundle.tar.sha256"
            bundle_path.write_bytes(bundle)
            for value in (
                ("0" * 64 + "  bundle.tar\n").encode("ascii"),
                (semantics.sha256_bytes(bundle) + "  other.tar\n").encode("ascii"),
            ):
                sidecar_path.write_bytes(value)
                with self.assertRaisesRegex(semantics.SemanticsV3Error, "sidecar"):
                    semantics.read_raw_bundle(bundle_path, sidecar_path)

    def test_symlink_bundle_and_traversal_member_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real.tar"
            real.write_bytes(semantics.canonical_tar({"manifest.json": b"{}\n"}))
            link = root / "link.tar"
            link.symlink_to(real)
            sidecar = root / "link.tar.sha256"
            sidecar.write_bytes(semantics.raw_sidecar_bytes(link.name, real.read_bytes()))
            with self.assertRaisesRegex(semantics.SemanticsV3Error, "non-symlink"):
                semantics.read_raw_bundle(link, sidecar)
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                info = tarfile.TarInfo("../escape")
                info.size = 1
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(b"x"))
            real.write_bytes(stream.getvalue())
            sidecar.write_bytes(semantics.raw_sidecar_bytes(real.name, real.read_bytes()))
            with self.assertRaisesRegex(semantics.SemanticsV3Error, "metadata"):
                semantics.read_raw_bundle(real, sidecar)

    def test_noncanonical_tar_metadata_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                info = tarfile.TarInfo("manifest.json")
                info.size = 3
                info.mode = 0o600
                info.mtime = 9
                archive.addfile(info, io.BytesIO(b"{}\n"))
            bundle = root / "bundle.tar"
            sidecar = root / "bundle.tar.sha256"
            bundle.write_bytes(stream.getvalue())
            sidecar.write_bytes(semantics.raw_sidecar_bytes(bundle.name, bundle.read_bytes()))
            with self.assertRaisesRegex(semantics.SemanticsV3Error, "metadata"):
                semantics.read_raw_bundle(bundle, sidecar)

    def test_large_bundle_same_inode_mid_read_splice_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            size = 2 * 1024 * 1024
            tar_a = semantics.canonical_tar(
                {"manifest.json": b"{}\n", "raw/large.bin": b"A" * size}
            )
            tar_b = semantics.canonical_tar(
                {"manifest.json": b"{}\n", "raw/large.bin": b"B" * size}
            )
            splice = tar_a[:1024 * 1024] + tar_b[1024 * 1024:]
            with tarfile.open(fileobj=io.BytesIO(splice), mode="r:") as archive:
                splice_payloads = {
                    member.name: archive.extractfile(member).read()
                    for member in archive.getmembers()
                }
            self.assertEqual(semantics.canonical_tar(splice_payloads), splice)
            self.assertNotEqual(splice, tar_a)
            self.assertNotEqual(splice, tar_b)
            bundle = root / "raw.tar"
            sidecar = root / "raw.tar.sha256"
            bundle.write_bytes(tar_a)
            sidecar.write_bytes(semantics.raw_sidecar_bytes(bundle.name, splice))
            metadata = bundle.stat()
            identity = (metadata.st_dev, metadata.st_ino)
            real_read = semantics.os.read
            spliced = [False]

            def hooked_read(descriptor, count):
                data = real_read(descriptor, count)
                observed = os.fstat(descriptor)
                if (
                    not spliced[0]
                    and (observed.st_dev, observed.st_ino) == identity
                    and len(data) == 1024 * 1024
                ):
                    with bundle.open("r+b") as handle:
                        handle.seek(0)
                        handle.write(tar_b)
                        handle.flush()
                        os.fsync(handle.fileno())
                    spliced[0] = True
                return data

            with mock.patch.object(semantics.os, "read", side_effect=hooked_read):
                with self.assertRaisesRegex(
                    semantics.SemanticsV3Error, "identity changed|bytes changed"
                ):
                    semantics.read_raw_bundle(bundle, sidecar)
            self.assertTrue(spliced[0])

    def test_sidecar_same_inode_short_read_splice_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle_data = semantics.canonical_tar({"manifest.json": b"{}\n"})
            bundle = root / "raw.tar"
            sidecar = root / "raw.tar.sha256"
            expected = semantics.raw_sidecar_bytes(bundle.name, bundle_data)
            split = 11
            initial = expected[:split] + b"X" * (len(expected) - split)
            replacement = b"Y" * split + expected[split:]
            bundle.write_bytes(bundle_data)
            sidecar.write_bytes(initial)
            metadata = sidecar.stat()
            identity = (metadata.st_dev, metadata.st_ino)
            real_read = semantics.os.read
            spliced = [False]

            def hooked_read(descriptor, count):
                observed = os.fstat(descriptor)
                if (
                    not spliced[0]
                    and (observed.st_dev, observed.st_ino) == identity
                ):
                    data = real_read(descriptor, split)
                    with sidecar.open("r+b") as handle:
                        handle.seek(0)
                        handle.write(replacement)
                        handle.flush()
                        os.fsync(handle.fileno())
                    spliced[0] = True
                    return data
                return real_read(descriptor, count)

            with mock.patch.object(semantics.os, "read", side_effect=hooked_read):
                with self.assertRaisesRegex(
                    semantics.SemanticsV3Error, "identity changed|bytes changed"
                ):
                    semantics.read_raw_bundle(bundle, sidecar)
            self.assertTrue(spliced[0])

    def test_bundle_and_sidecar_path_and_inode_races_fail(self):
        for target_name in ("bundle", "sidecar"):
            for mutation_name in (
                "leaf_symlink", "ancestor_symlink", "same_byte_inode", "in_place"
            ):
                with self.subTest(target=target_name, mutation=mutation_name):
                    with tempfile.TemporaryDirectory() as temporary:
                        root = Path(temporary)
                        bundle, sidecar = self.raw_pair(root)
                        target = bundle if target_name == "bundle" else sidecar
                        original = target.read_bytes()
                        replacement = root / (
                            target_name + "-same-byte-replacement"
                        )
                        replacement.write_bytes(original)
                        external_root = root / (target_name + "-external-root")
                        external_root.mkdir()
                        (external_root / target.name).write_bytes(original)
                        real_sidecar_bytes = semantics.raw_sidecar_bytes
                        real_decode = semantics.decode_raw_bundle
                        mutated = [False]

                        def mutate():
                            if mutation_name == "leaf_symlink":
                                held = target.with_name(target.name + ".held")
                                target.rename(held)
                                target.symlink_to(external_root / target.name)
                            elif mutation_name == "ancestor_symlink":
                                held = target.parent.with_name(
                                    target.parent.name + "-held"
                                )
                                target.parent.rename(held)
                                target.parent.symlink_to(
                                    external_root, target_is_directory=True
                                )
                            elif mutation_name == "same_byte_inode":
                                os.replace(str(replacement), str(target))
                            else:
                                changed = (b"1" if original[:1] != b"1" else b"0")
                                with target.open("r+b") as handle:
                                    handle.write(changed)
                                    handle.flush()
                                    os.fsync(handle.fileno())

                        def hooked_sidecar_bytes(bundle_name, bundle_data):
                            data = real_sidecar_bytes(bundle_name, bundle_data)
                            if not mutated[0]:
                                mutate()
                                mutated[0] = True
                            return data

                        def hooked_decode(bundle_data, sidecar_data):
                            data = real_decode(bundle_data, sidecar_data)
                            if not mutated[0]:
                                mutate()
                                mutated[0] = True
                            return data

                        patcher = mock.patch.object(
                            semantics,
                            (
                                "decode_raw_bundle"
                                if mutation_name == "in_place"
                                else "raw_sidecar_bytes"
                            ),
                            side_effect=(
                                hooked_decode
                                if mutation_name == "in_place"
                                else hooked_sidecar_bytes
                            ),
                        )
                        with patcher:
                            with self.assertRaisesRegex(
                                semantics.SemanticsV3Error,
                                "identity changed|bytes changed|invalid size",
                            ):
                                semantics.read_raw_bundle(bundle, sidecar)
                        self.assertTrue(mutated[0])


class CompilerArgumentTests(unittest.TestCase):
    def test_c_replay_preserves_profile_and_redirects_only_side_effects(self):
        original = [
            "gcc", "-O2", "-Wp,-MD,/tmp/a.d", "-c", "-MF", "/tmp/a.d",
            "-o", "/tmp/a.o", "/src/a.c",
        ]
        replay = semantics.reconstruct_c_argv(original, 8, Path("/tmp/out.o"))
        self.assertIn("-O2", replay)
        self.assertNotIn("/tmp/a.d", replay)
        self.assertNotIn("/tmp/a.o", replay)
        self.assertEqual(replay[-1], "/src/a.c")
        for _, option, _ in semantics.C_DUMP_OPTIONS:
            self.assertIn(option, replay)
        baseline = semantics.reconstruct_c_baseline_argv(
            original, 8, Path("/tmp/baseline.o")
        )
        for _, option, _ in semantics.C_DUMP_OPTIONS:
            self.assertNotIn(option, baseline)
        self.assertIn("-O2", baseline)

    def test_c_unsafe_response_lto_and_existing_dump_fail(self):
        for argv, message in (
            (["gcc", "@evil", "-c", "/src/a.c"], "unsafe"),
            (["gcc", "-flto", "-c", "/src/a.c"], "unsupported"),
            (["gcc", "-fdump-tree-vrp", "-c", "/src/a.c"], "unsupported"),
        ):
            with self.assertRaisesRegex(semantics.SemanticsV3Error, message):
                semantics.reconstruct_c_argv(argv, len(argv) - 1, Path("/tmp/out.o"))

    def test_rust_replay_redirects_object_and_adds_private_mir_dir(self):
        original = ["rustc", "--crate-name", "demo", "--emit=obj=/tmp/a.o", "/src/a.rs"]
        replay = semantics.reconstruct_rust_argv(original, Path("/tmp/b.o"), Path("/tmp/mir"))
        self.assertEqual(replay[:3], original[:3])
        self.assertIn("--emit=obj=/tmp/b.o", replay)
        self.assertIn("-Zdump-mir=all", replay)
        self.assertEqual(replay[-1], "-Zdump-mir-dir=/tmp/mir")

    def test_rust_response_existing_mir_and_ambiguous_object_fail(self):
        for argv, message in (
            (["rustc", "@evil", "--emit=obj=/tmp/a.o", "/src/a.rs"], "response"),
            (["rustc", "-Zdump-mir=all", "--emit=obj=/tmp/a.o", "/src/a.rs"], "already"),
            (["rustc", "/src/a.rs"], "ambiguous"),
        ):
            with self.assertRaisesRegex(semantics.SemanticsV3Error, message):
                semantics.reconstruct_rust_argv(argv, Path("/tmp/b.o"), Path("/tmp/mir"))

    def test_recorded_output_parser_rejects_multiple_outputs(self):
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "ambiguous"):
            semantics.compiler_output_path(
                ["gcc", "-o", "/tmp/a.o", "--output=/tmp/b.o", "/src/a.c"],
                "c", "/",
            )

    def test_recorded_source_index_accepts_lexical_parent_components(self):
        argv = [
            "gcc", "-I/repo/ihk/ikc", "-c", "-o", "/tmp/a.o",
            "/repo/ihk/linux/core/../../ikc/linux.c",
        ]
        self.assertEqual(
            semantics.invocation_source_index(argv, "ihk/ikc/linux.c"), 5
        )

    def test_recorded_object_output_is_lexically_confined(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            kernel = root / "kernel"
            build = root / "build"
            kernel.mkdir()
            build.mkdir()
            self.assertEqual(
                semantics.compiler_output_path(
                    ["rustc", "--emit=obj=relative.o", "source.rs"],
                    "rust", kernel, (build,),
                ),
                kernel / "relative.o",
            )
            absolute = build / "absolute.o"
            self.assertEqual(
                semantics.compiler_output_path(
                    ["rustc", "--emit=obj=" + str(absolute), "source.rs"],
                    "rust", kernel, (build,),
                ),
                absolute,
            )
            for argv, language, message in (
                (["rustc", "--emit=obj=../escape.o", "source.rs"], "rust", "dot"),
                (["gcc", "-c", "-o", "../escape.o", "source.c"], "c", "dot"),
                (["rustc", "--emit=obj=" + str(root / "escape.o"), "source.rs"], "rust", "escapes"),
            ):
                with self.assertRaisesRegex(semantics.SemanticsV3Error, message):
                    semantics.compiler_output_path(
                        argv, language, kernel, (build,)
                    )


class ObjectReadBoundaryTests(unittest.TestCase):
    def rust_record(self, output):
        compiler = {
            "bytes": 1,
            "invoked_as": "rustc",
            "resolved_path": "/toolchain/rustc",
            "sha256": "a" * 64,
            "version_first_line": "rustc synthetic",
            "version_stderr_sha256": semantics.sha256_bytes(b""),
            "version_stdout_sha256": "b" * 64,
        }
        return {
            "compile_argv": ["rustc", "--emit=obj=" + output, "source.rs"],
            "recorded_compiler": compiler,
        }, compiler

    def capture(self, record, compiler, kernel, build, temporary):
        with mock.patch.object(
            semantics.sites, "compiler_provenance", return_value=compiler
        ), mock.patch.object(
            semantics,
            "probe_rust_mir_options",
            return_value={
                "stderr_sha256": semantics.sha256_bytes(b""),
                "stdout_sha256": semantics.sha256_bytes(b"probe"),
            },
        ):
            return semantics.capture_rust_source(
                record, kernel, build, (), temporary, {}
            )

    def test_capture_rust_rejects_relative_and_absolute_object_leaf_symlinks(self):
        for absolute in (False, True):
            with self.subTest(absolute=absolute), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                kernel = root / "kernel"
                build = root / "build"
                semantic = root / "semantic"
                external = root / "external.o"
                kernel.mkdir()
                build.mkdir()
                semantic.mkdir()
                external.write_bytes(b"EXTERNAL\n")
                leaf = (build if absolute else kernel) / "production.o"
                leaf.symlink_to(external)
                output = str(leaf) if absolute else "production.o"
                record, compiler = self.rust_record(output)
                with self.assertRaisesRegex(semantics.SemanticsV3Error, "symlink"):
                    self.capture(record, compiler, kernel, build, semantic)

    def test_capture_rust_rejects_hardlinked_object_leaf(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            kernel = root / "kernel"
            build = root / "build"
            semantic = root / "semantic"
            external = root / "external.o"
            kernel.mkdir()
            build.mkdir()
            semantic.mkdir()
            external.write_bytes(b"EXTERNAL\n")
            os.link(str(external), str(kernel / "production.o"))
            record, compiler = self.rust_record("production.o")
            with self.assertRaisesRegex(semantics.SemanticsV3Error, "single-link"):
                self.capture(record, compiler, kernel, build, semantic)

    def capture_race(self, mutation, message):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            kernel = root / "kernel"
            build = root / "build"
            objects = kernel / "objects"
            semantic = root / "semantic"
            kernel.mkdir()
            build.mkdir()
            objects.mkdir()
            semantic.mkdir()
            leaf = objects / "production.o"
            original = b"ORIGINAL-OBJECT\n"
            leaf.write_bytes(original)
            record, compiler = self.rust_record("objects/production.o")
            real_read = semantics.read_fd_bytes
            calls = [0]

            def hooked(descriptor, maximum):
                data = real_read(descriptor, maximum)
                calls[0] += 1
                if calls[0] == 1:
                    mutation(root, objects, leaf, original)
                return data

            with mock.patch.object(semantics, "read_fd_bytes", side_effect=hooked):
                with self.assertRaisesRegex(semantics.SemanticsV3Error, message):
                    self.capture(record, compiler, kernel, build, semantic)

    def test_capture_rust_rejects_object_ancestor_swap(self):
        def mutate(root, objects, leaf, original):
            moved = root / "objects-held"
            objects.rename(moved)
            external = root / "external"
            external.mkdir()
            (external / "production.o").write_bytes(original)
            objects.symlink_to(external, target_is_directory=True)

        self.capture_race(mutate, "identity changed")

    def test_capture_rust_rejects_same_byte_inode_replacement(self):
        def mutate(root, objects, leaf, original):
            leaf.unlink()
            leaf.write_bytes(original)

        self.capture_race(mutate, "identity changed")

    def test_capture_rust_holds_production_identity_across_both_replays(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            kernel = root / "kernel"
            build = root / "build"
            semantic = root / "semantic"
            kernel.mkdir()
            build.mkdir()
            semantic.mkdir()
            leaf = kernel / "production.o"
            original = b"ORIGINAL-OBJECT\n"
            leaf.write_bytes(original)
            record, compiler = self.rust_record("production.o")
            object_record = {
                "bytes": len(original),
                "sha256": semantics.sha256_bytes(original),
            }
            calls = [0]

            def fake_run(record_value, kernel_value, roots, run_dir, environment):
                calls[0] += 1
                if calls[0] == 1:
                    leaf.unlink()
                    leaf.write_bytes(original)
                return {
                    "argv": ["rustc"],
                    "mir": {"crate.demo.built.after.mir": b"mir\n"},
                    "object": dict(object_record),
                    "object_data": original,
                    "stderr_sha256": semantics.sha256_bytes(b""),
                    "stdout_sha256": semantics.sha256_bytes(b""),
                }

            with mock.patch.object(
                semantics, "one_rust_run", side_effect=fake_run
            ):
                with self.assertRaisesRegex(semantics.SemanticsV3Error, "identity changed"):
                    self.capture(record, compiler, kernel, build, semantic)

    def test_capture_rust_rejects_in_place_object_mutation(self):
        def mutate(root, objects, leaf, original):
            leaf.write_bytes(b"MUTATED-OBJECT!\n")

        self.capture_race(mutate, "identity changed|bytes changed")

    def test_c_replay_object_reader_rejects_compiler_symlink_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            kernel = root / "kernel"
            run_dir = root / "run"
            external = root / "external.o"
            kernel.mkdir()
            run_dir.mkdir()
            external.write_bytes(b"EXTERNAL\n")
            record = {
                "compile_argv": [
                    "gcc", "-c", "-o", str(root / "recorded.o"), "/src/a.c"
                ]
            }

            def fake_compiler(argv, cwd, environment):
                output = Path(argv[argv.index("-o") + 1])
                output.symlink_to(external)
                return types.SimpleNamespace(stdout=b"", stderr=b"")

            with mock.patch.object(
                semantics, "run_compiler", side_effect=fake_compiler
            ):
                with self.assertRaisesRegex(semantics.SemanticsV3Error, "symlink"):
                    semantics.one_c_run(
                        record, Path("/src/a.c"), 4, kernel, (), run_dir, {}
                    )

    def test_c_baseline_identity_is_held_across_semantic_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            kernel = root / "kernel"
            run_dir = root / "run"
            kernel.mkdir()
            run_dir.mkdir()
            original = b"OBJECT\n"
            record = {
                "compile_argv": [
                    "gcc", "-c", "-o", str(root / "recorded.o"), "/src/a.c"
                ]
            }
            calls = [0]

            def fake_compiler(argv, cwd, environment):
                calls[0] += 1
                output = Path(argv[argv.index("-o") + 1])
                output.write_bytes(original)
                if calls[0] == 2:
                    baseline = run_dir / "baseline.o"
                    baseline.unlink()
                    baseline.write_bytes(original)
                    for _, _, suffix in semantics.C_DUMP_OPTIONS:
                        (run_dir / ("semantic.c.001t" + suffix)).write_bytes(b"dump\n")
                return types.SimpleNamespace(stdout=b"", stderr=b"")

            with mock.patch.object(
                semantics, "run_compiler", side_effect=fake_compiler
            ):
                with self.assertRaisesRegex(semantics.SemanticsV3Error, "identity changed"):
                    semantics.one_c_run(
                        record, Path("/src/a.c"), 4, kernel, (), run_dir, {}
                    )


class RawManifestMutationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = SyntheticRawFixture()

    def validate(self, manifest=None, payloads=None):
        return semantics.validate_raw_manifest(
            manifest or self.fixture.manifest,
            payloads or self.fixture.payloads,
            self.fixture.inputs,
        )

    def test_synthetic_manifest_is_deterministic_and_exact(self):
        first = semantics.canonical_bytes(self.fixture.manifest)
        second = semantics.canonical_bytes(copy.deepcopy(self.fixture.manifest))
        self.assertEqual(first, second)
        observed = self.validate()
        self.assertEqual(len(observed), semantics.EXPECTED_C_SOURCE_COUNT + 1)

    def test_schema_mutation_fails(self):
        manifest = copy.deepcopy(self.fixture.manifest)
        manifest["unexpected"] = False
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "schema"):
            self.validate(manifest)

    def test_numeric_bool_and_float_aliases_fail_direct_validation(self):
        mutations = (
            (("schema_version",), True),
            (("schema_version",), 1.0),
            (("inputs", "failure_sites_v1", "schema_version"), True),
            (("inputs", "failure_sites_v1", "artifact_bytes"), 3.0),
            (("files", 0, "bytes"), True),
            (("compiler_invocations", 0, "production_object", "bytes"), 4.0),
            (("toolchains", "c", 0, "compiler", "bytes"), True),
        )
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                manifest = copy.deepcopy(self.fixture.manifest)
                target = manifest
                for component in path[:-1]:
                    target = target[component]
                target[path[-1]] = value
                with self.assertRaisesRegex(
                    semantics.SemanticsV3Error, "integer|floating-point"
                ):
                    self.validate(manifest)

    def test_boolean_fields_reject_integer_aliases(self):
        for field in ("object_byte_equality", "two_run_normalized_determinism"):
            manifest = copy.deepcopy(self.fixture.manifest)
            manifest["compiler_invocations"][0][field] = 1
            with self.assertRaisesRegex(semantics.SemanticsV3Error, "boolean"):
                self.validate(manifest)

    def test_coherently_rebuilt_bundle_rejects_bool_and_float_schema_versions(self):
        for value in (True, 1.0):
            with self.subTest(value=value):
                manifest = copy.deepcopy(self.fixture.manifest)
                manifest["schema_version"] = value
                payloads = dict(self.fixture.payloads)
                payloads["manifest.json"] = semantics.canonical_bytes(manifest)
                bundle_data = semantics.canonical_tar(payloads)
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    bundle = root / "raw.tar"
                    sidecar = root / "raw.tar.sha256"
                    bundle.write_bytes(bundle_data)
                    sidecar.write_bytes(
                        semantics.raw_sidecar_bytes(bundle.name, bundle_data)
                    )
                    observed, observed_payloads, _ = semantics.read_raw_bundle(
                        bundle, sidecar
                    )
                    with self.assertRaisesRegex(
                        semantics.SemanticsV3Error, "exact integer|floating-point"
                    ):
                        semantics.validate_raw_manifest(
                            observed, observed_payloads, self.fixture.inputs
                        )

    def test_coherently_rebuilt_bundle_rejects_nonfinite_number(self):
        manifest = copy.deepcopy(self.fixture.manifest)
        manifest["schema_version"] = float("nan")
        manifest_data = (
            json.dumps(
                manifest, allow_nan=True, sort_keys=True, separators=(",", ":")
            )
            + "\n"
        ).encode("utf-8")
        payloads = dict(self.fixture.payloads)
        payloads["manifest.json"] = manifest_data
        bundle_data = semantics.canonical_tar(payloads)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "raw.tar"
            sidecar = root / "raw.tar.sha256"
            bundle.write_bytes(bundle_data)
            sidecar.write_bytes(semantics.raw_sidecar_bytes(bundle.name, bundle_data))
            with self.assertRaisesRegex(semantics.SemanticsV3Error, "non-finite"):
                semantics.read_raw_bundle(bundle, sidecar)

    def test_toolchain_mutation_fails(self):
        manifest = copy.deepcopy(self.fixture.manifest)
        manifest["toolchains"]["rust"]["compiler"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "toolchain"):
            self.validate(manifest)

    def test_recorded_argv_mutation_fails_even_with_recomputed_digest(self):
        manifest = copy.deepcopy(self.fixture.manifest)
        invocation = manifest["compiler_invocations"][0]
        invocation["recorded_argv"].append("-fno-builtin")
        invocation["recorded_argv_sha256"] = semantics.sha256_bytes(
            semantics.canonical_bytes(invocation["recorded_argv"])
        )
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "authority"):
            self.validate(manifest)

    def test_normalized_argv_mutation_fails_even_with_recomputed_digest(self):
        manifest = copy.deepcopy(self.fixture.manifest)
        invocation = manifest["compiler_invocations"][0]
        invocation["normalized_replay_argv"].append("-fplugin=/tmp/hostile.so")
        invocation["normalized_replay_argv_sha256"] = semantics.sha256_bytes(
            semantics.canonical_bytes(invocation["normalized_replay_argv"])
        )
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "preserve"):
            self.validate(manifest)

        manifest = copy.deepcopy(self.fixture.manifest)
        invocation = manifest["compiler_invocations"][0]
        invocation["normalized_replay_argv"][-1] = "/repo/" + invocation["source"]
        invocation["normalized_replay_argv_sha256"] = semantics.sha256_bytes(
            semantics.canonical_bytes(invocation["normalized_replay_argv"])
        )
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "repository source"):
            self.validate(manifest)

    def test_file_source_and_kind_mutations_fail(self):
        for field, value in (("source", "synthetic/c1.c"), ("kind", "c_ssa")):
            manifest = copy.deepcopy(self.fixture.manifest)
            manifest["files"][0][field] = value
            with self.assertRaisesRegex(semantics.SemanticsV3Error, "file authority"):
                self.validate(manifest)

    def test_rust_compiler_path_mutation_fails(self):
        manifest = copy.deepcopy(self.fixture.manifest)
        rust = [
            item for item in manifest["compiler_invocations"]
            if item["language"] == "rust"
        ][0]
        rust["mir_files"][0]["compiler_path"] = "../hostile.built.after.mir"
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "safe relative path"):
            self.validate(manifest)

    def test_object_equality_mutation_fails(self):
        manifest = copy.deepcopy(self.fixture.manifest)
        manifest["compiler_invocations"][0]["replay_object"]["sha256"] = "9" * 64
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "differs"):
            self.validate(manifest)

    def test_payload_digest_and_path_mutations_fail(self):
        payloads = dict(self.fixture.payloads)
        first = sorted(payloads)[0]
        payloads[first] += b"mutation"
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "digest"):
            self.validate(payloads=payloads)
        manifest = copy.deepcopy(self.fixture.manifest)
        manifest["files"][0]["path"] = "../escape"
        with self.assertRaises(semantics.SemanticsV3Error):
            self.validate(manifest)


class MirAndDomainParserTests(unittest.TestCase):
    MIR = b"""fn demo() -> i32 {
    scope 1 at $REPO/executer/kernel/mcctrl/rust/mcctrl_helpers.rs:10:5: 10:12;
    bb0: {
        _0 = const -22_i32; // scope 1 at $REPO/executer/kernel/mcctrl/rust/mcctrl_helpers.rs:10:5: 10:12
        switchInt(_1) -> [0: bb1, otherwise: bb2];
    }
    bb1: {
        return;
    }
    bb2 (cleanup): {
        unreachable;
    }
}
"""

    def test_mir_parser_binds_owner_cfg_spans_and_reachability(self):
        body = semantics.parse_mir_body(self.MIR, "crate.demo.built.after.mir")
        self.assertEqual(body["owner"], "demo")
        self.assertEqual(body["reachable"], {0, 1, 2})
        self.assertEqual(body["blocks"][0]["successors"], [1, 2])
        self.assertTrue(
            any(semantics.span_contains(span, 10, 5, 12) for span in body["blocks"][0]["spans"])
        )
        semantics.require_digest(body["cfg_sha256"], "CFG")

    def test_unknown_terminator_and_missing_successor_fail(self):
        unknown = self.MIR.replace(b"return;", b"mystery;")
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "terminator"):
            semantics.parse_mir_body(unknown, "crate.demo.built.after.mir")
        missing = self.MIR.replace(b"otherwise: bb2", b"otherwise: bb9")
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "unknown basic block"):
            semantics.parse_mir_body(missing, "crate.demo.built.after.mir")

    def test_source_span_boundary_mutation_is_not_contained(self):
        span = {
            "start_line": 10, "start_column": 5,
            "end_line": 10, "end_column": 12, "path": "demo.rs",
        }
        self.assertTrue(semantics.span_contains(span, 10, 5, 12))
        self.assertTrue(semantics.span_equals_token(span, 10, 5, 12))
        self.assertFalse(semantics.span_contains(span, 10, 4, 12))
        self.assertFalse(semantics.span_contains(span, 10, 5, 13))
        self.assertFalse(semantics.span_equals_token(span, 10, 5, 11))

    def test_vrp_interval_parser_records_but_does_not_infer_semantics(self):
        terminal = {"expression": "return _7;"}
        parsed = semantics.vrp_intervals(b"_7: int [-22, 0]\n", terminal)
        self.assertEqual(parsed, [{"high": "0", "low": "-22", "ssa_name": "_7"}])
        self.assertFalse(semantics.ANALYSIS_CLAIM["semantic_error_domains_proven"])
        self.assertIn("205_c_returns_require_semantic_oracle", semantics.BLOCKERS)

    def test_mir_negative_errno_accepts_literal_and_unary_negation_only(self):
        self.assertTrue(semantics.mir_contains_negative_errno("_0 = const -22_i32;", 22))
        self.assertTrue(semantics.mir_contains_negative_errno("_0 = Neg(const 22_i64);", 22))
        self.assertFalse(semantics.mir_contains_negative_errno("_0 = const 22_i32;", 22))
        self.assertFalse(semantics.mir_contains_negative_errno("_0 = const -14_i32;", 22))
        self.assertFalse(semantics.mir_contains_negative_errno("_0 = const 0; // -22", 22))

    def test_mir_parser_rejects_multiple_owners(self):
        hostile = self.MIR + b"\nfn second() {\n bb0: { return; }\n}\n"
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "unique owner"):
            semantics.parse_mir_body(hostile, "crate.demo.built.after.mir")

    def test_errno_constant_parser_rejects_duplicates(self):
        self.assertEqual(semantics.errno_constants(b"const EINVAL: c_int = 22;\n"), {"EINVAL": 22})
        with self.assertRaisesRegex(semantics.SemanticsV3Error, "duplicated"):
            semantics.errno_constants(
                b"const EINVAL: c_int = 22;\nconst EINVAL: c_int = 23;\n"
            )


if __name__ == "__main__":
    unittest.main()
