#!/usr/bin/env python3
"""Validate and replay the non-crediting RK-006 patch authority."""

from __future__ import print_function

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile


AUTHORITY_PATH = "host-kernel/rocky/rk006-patch-authority-v1.json"
AUTHORITY_ID = "rocky-10.2-rk-006-layered-patch-authority-v1"
SOURCE_LOCK_PATH = "host-kernel/rocky/source-lock.json"
SOURCE_LOCK_SHA256 = "707ee40466ac0bb0cd0600383bba0b13fc1146e7080034786bf5668a95b27682"
SOURCE_LOCK_ID = "rocky-10.2-x86_64-kernel-6.12.0-211.44.1.el10_2-source-v1"
PARENT_AUTHORITY_PATH = "host-kernel/kbuild/parent-integration-v1.json"
PARENT_AUTHORITY_SHA256 = "c806e6cda3be3e6f4b92cef35a0d5369738bae5b87e32ed4f486489d3435db2f"
FIXTURE_ROOT = "scripts/tests/fixtures/rust-core-rocky-6.12"
TARGET_FIXTURE = "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs"
TARGET_FIXTURE_SHA256 = "9c21a1b67751db98e407439b77d014be6b92ba3cf6457fde6a4118a798f4fa05"
INITIAL_CLOSURE_SHA256 = "d2da4c4b8eb24a055ab636c43538168148c08b9ef4476138cf6a19124d575b3f"

CLAIM_SCOPE = (
    "Bounded RK-006 source classification, semantic policy, and repository-fixture "
    "replay only. This authority never awards RK-006 or tracker credit and does "
    "not claim a current-head production build, external full-source replay, "
    "independent review, or durable archival."
)
BLOCKERS = [
    "Independent review has not approved this RK-006 authority or its patch authorship, license, and provenance decisions; authorship for the two headerless repository overlays and standalone license for the parent-integration patch remain unestablished.",
    "A current-head exact Rocky build with exact compiler and tool identities, including full external parent-file preimages, has not bound the applied postimages to this authority.",
    "The authority manifest, replay logs, patched source closure, build logs, and artifacts are not durably archived.",
]
FORBIDDEN_POLICY_TOKENS = ["mckernel", "ihk", "mcctrl", "mcexec"]
ONLY_NEW_SOURCE_PATH = "rust/kernel/miscdevice.rs"


class AuthorityError(Exception):
    """Raised when the authority fails closed."""


_PATCH_DATA = (
    ("compat-001", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0001-x86-rust-set-rustc-abi-x86-softfloat.patch", "85069fa5d4e1de8a0d0172480604c74deba0caeafd34268a6735d069599e5113", "linux-kernel-community", "linux-commit:6273a058383e05465083b535ed9469f2c8a48321", "patch-header", ("scripts/generate_rust_target.rs",), "4e5a79cb1be45badd28e10d79bb3723798d7877677913f25d3dddf8ca32da23c"),
    ("compat-002", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch", "c52bde4ace32fbd908b6c5ed5e4ac1881effd6e9ebd5813e7e083d74a5f34997", "linux-kernel-community", "linux-commit:8851e27d2cb947ea8bbbe8e812068f7bf5cbd00b", "patch-header", ("scripts/generate_rust_target.rs",), "38fd436fbc3610106cc5596350756fef67621ae68496c95356f1dcab8fa20e53"),
    ("compat-003", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0003-kbuild-rust-add-rustc-min-version.patch", "4af4b725292a080a9bf69f37308cb4099e957674001f0fc83239f4be29f07ec1", "linux-kernel-community", "linux-commit:1814e71a4e9c20bd69dbe1e007d31c0ab2c237a2", "patch-header", ("Documentation/kbuild/makefiles.rst", "arch/arm64/Makefile", "scripts/Makefile.compiler"), "94a8ccb817439618be957a8e02d944cf0e8a7c69b8d911dbfcc77846c35781ac"),
    ("compat-004", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0004-rust-compile-libcore-edition-2024.patch", "3ef23cf99a4523a6045a29b70f49ba0080242d7b219db7f0bca58b4f7d73fbb7", "linux-kernel-community", "linux-commit:60d8db49ef143c04f7daf90dafa3347a7af3b4c7", "patch-header", ("rust/Makefile", "scripts/generate_rust_analyzer.py"), "2409e94bfb3a7b2a44a34fe0c9877ca274e0bab44d4a5b3c86f2e6ac34a04cd8"),
    ("compat-005", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0005-rust-clean-unnecessary-transmutes-lint.patch", "0ba29993d78fea5db3c0ff8dbf41bf8a6c08b00d9803fc85da7805e698ac8c33", "linux-kernel-community", "linux-commit:376b73292a262124c8aed10026e9da23e92554b2", "patch-header", ("init/Kconfig", "rust/bindings/lib.rs", "rust/uapi/lib.rs"), "8f78d08ecbb4f80fa6affbc7d7fad6659c6b62f4892bd58797e678a59751d5b5"),
    ("compat-006", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0006-rust-init-allow-dead-code-rust-1.89.patch", "315ec61d17c5d3cc97c6123f30bcffa08befcc00c487efaa5e6eda38333d29c5", "linux-kernel-community", "linux-commit:5d2d34f36724585801937e76f81a69ab97cd045b", "patch-header", ("rust/kernel/init/macros.rs",), "9ece288150ecca04f3d747caeccb9e0cd244bb87a0d25f5156c91fe2539b7bc1"),
    ("compat-007", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0007-rust-use-used-compiler-rust-1.89.patch", "d9a58b1123e5f5522efb7ad7b7837c406b955c1a1c4a7a38f0d2faa4dd4285fc", "linux-kernel-community", "linux-commit:d9ebd928288bb82df8efeb3a34f2cd31883f440e", "patch-header", ("rust/Makefile", "rust/kernel/lib.rs", "rust/macros/module.rs", "scripts/Makefile.build"), "929fc11fe56030a36745601cd0bd835f8de74e780429e3692018b52cc5e86579"),
    ("compat-008", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0008-rust-enable-arbitrary-self-types-rust-1.92.patch", "ab3f6adaed3fcb65669ffc0baccdb3d7a9b7e3df9d0c5889228c775585daacaa", "linux-kernel-community", "linux-commit:e18d5b42489311bc86d7ce5fb0f19af067495589", "patch-header", ("rust/kernel/lib.rs", "rust/kernel/list/arc.rs", "rust/kernel/sync/arc.rs", "scripts/Makefile.build"), "acbe669bc6271a4c2354e4b52c6b45016665dc55a2bd42b4a1536a87637ebff2"),
    ("compat-009", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0009-rust-block-drop-removed-merge-flag.patch", "076b0b48effba9bed12cb00a4c93318353aa26344f14b0b1bba5508c55a1bcfb", "linux-kernel-community", "linux-commit:31d813a3b8cbde2d09ba4dee282ca29096541006", "patch-header", ("rust/kernel/block/mq/tag_set.rs",), "14cd8bb90a27ae6addd9e341f2db4da377ceb0b1e475d0303d5044fcf1342ca2"),
    ("compat-010", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0010-kbuild-disable-default-const-init-unsafe.patch", "2781f4eac05a806a58e76a035f2dba45f137a9147512c87cf9f63b1deb40c7e0", "linux-kernel-community", "linux-commit:511ceee89966ce906ca8989523e1a67ba6de44c1", "patch-header", ("scripts/Makefile.extrawarn",), "e61cbd31a972a7ed60d487a0e5cce2ba0451e9ba0e1be7a32b16b6493ae24a59"),
    ("compat-011", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0011-mm-ksm-fix-clang-21-uninitialized.patch", "2104f602c62bbda355089fb0210647b39d511e77bbdb9857e5c092c004f490a1", "linux-kernel-community", "linux-commit:f7ff0324760013762088f70d74ed1ddb7edffb13", "patch-header", ("mm/ksm.c",), "c1c8ac7e120b247480738391081b49b5b6e7795451651988c96e35a48f967633"),
    ("compat-012", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0012-netfs-mark-nonstring-lookup-tables.patch", "3aeb8de2d5eee43f56268475b8911e6e14eef59e3b8007b4719b8c4ef0a1b691", "linux-kernel-community", "linux-commit:58db1c3cd0ce857e7210b0a95908900c25c28c3e", "patch-header", ("fs/netfs/fscache_cache.c", "fs/netfs/fscache_cookie.c"), "33946fc834edd3c227dc7740f15f943bb9b21f416ccf360778689c3075b7c989"),
    ("compat-013", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0013-lib-crypto-mark-binary-vectors-nonstring.patch", "329e86bdadf721f366b58582bf893df451a25e1f5cb91715bb789e10c242f021", "linux-kernel-community", "linux-commit:e202196b8aa249d78ab87eae56bbe0e71e3dc39c", "patch-header", ("lib/crypto/aescfb.c", "lib/crypto/aesgcm.c"), "b4a1416244fcb3eab93b45195ef6e0e2f20a03aff5d5bfde9fb51b110120d792"),
    ("compat-014", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0014-gcc-15-mark-byte-arrays-nonstring.patch", "e98032b0d88ea5dbaffdbdf39a16423fded48dbed41adec29cc232782ba6d24b", "linux-kernel-community", "linux-commit:05e8d261a34e5c637e37be55c26e42cf5c75ee5c", "patch-header", ("drivers/iio/magnetometer/ak8974.c", "drivers/net/wireless/ath/carl9170/fw.c", "fs/cachefiles/key.c"), "5a40e7315afb7dec8b9b14d57f18cbc2c3e62ce5081e5d7982c38ab5b8c06742"),
    ("compat-015", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0015-gcc-15-demote-unterminated-string-warning.patch", "b07d58736bfe7e9ef5f9c3c4ce2807514f2cd01ab1146620fc09eb4f98ac8f29", "linux-kernel-community", "linux-commit:9f58537e9b8f07d56aca68308dc73db60fbc7ad3", "patch-header", ("Makefile",), "21bcab27d9a23a006e7c5cab5cb5ec355d40c5743da91112b8d34ecbceaafadd"),
    ("compat-016", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0016-gcc-15-disable-unterminated-string-warning.patch", "ea3a2c85b9dc1c15d3307c3958512b812d56297930d58fc6912adfb2ea3e7284", "linux-kernel-community", "linux-commit:d66cf772bebd789448121cdfc42734fb042c9c4b", "patch-header", ("Makefile",), "f71f377c349024d8cc9984c57ebfb7d17c5e849cafe5d2d838e833c1b83e1beb"),
    ("compat-017", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0017-kbuild-use-cc-disable-warning.patch", "890a11c4540d4c003773482c47858a946156e4cf0d2e04d3a9ed8e1a9382fd4b", "linux-kernel-community", "linux-commit:3f856d5d84467c7fba0bf3cca405089c497e37eb", "patch-header", ("Makefile", "arch/loongarch/kernel/Makefile", "arch/loongarch/kvm/Makefile", "arch/riscv/kernel/Makefile", "scripts/Makefile.extrawarn"), "bd04f1e1ec02e2d3f54793f3b03a11bef6d3317cd109b93e5373b8b8030a62eb"),
    ("compat-018", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0018-kbuild-order-unterminated-string-disable.patch", "e271fa6f30bb3b39a24ae2f926dfa067577997ecf2076e412b5575a4d785021e", "linux-kernel-community", "linux-commit:dd8a734155ae28094d27b96c00a478fa0ee6d5d7", "patch-header", ("Makefile", "scripts/Makefile.extrawarn"), "4d152730f8fe602a7196238dda74910c45bda086c79aa69da1db29b178389f41"),
    ("generic-001", "generic-rust-abstraction-binding", "host-kernel/rocky/patches/0019-rust-types-add-opaque-try-ffi-init.patch", "bc9b84c4c8bf36b7fac02dd3d04e1a170b86ee143b76739a6eed3e564cdebc2b", "linux-kernel-community", "linux-commit:a69dc41a4211b0da311ae3a3b79dd4497c9dfb60", "linux-submission-and-target-file", ("rust/kernel/types.rs",), "a637a644d836ca4440bd2e8f48dc8bfc2fb00f2c27dd5b7f38bfd8cd1451dabf"),
    ("generic-002", "generic-rust-abstraction-binding", "host-kernel/rocky/patches/0020-rust-miscdevice-add-base-abstraction.patch", "d377b5bd91d507e383b8673beac42381b9b6c37a47bba7955c768a8f6ddaad25", "linux-kernel-community", "linux-commit:f893691e742688ae21ad597c5bba13bef54706cd", "linux-submission-and-target-file", ("rust/bindings/bindings_helper.h", "rust/kernel/lib.rs", "rust/kernel/miscdevice.rs"), "ec47be691ce9329bf79332fa907e167f882dec646bcefdc2a0e9239cdda85fe2"),
    ("compat-019", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0021-objtool-recognize-rust-1.92-panic-const.patch", "6eb8dd4789a5b01a3f8e00ea45dab9debb7d23bb7a8c4af5b2cfdc181656633a", "local-rocky-exact-build-compatibility", "github-actions:run=31644047766,job=94273299611,artifact=9160078637", "patch-header", ("tools/objtool/check.c",), "ecc9a41ded6a40b26bd2e74d695a7417b4d351d4faa4b3766f31ef8881cea367"),
    ("compat-020", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0022-x86-pvh-annotate-noendbr.patch", "2f07f4030312ce1df38ed78615c94bfb99c7e084d27611de96d38bcf47237e48", "local-rocky-exact-build-compatibility", "github-actions:run=31605746750,job=94144112731,artifact=9145918955", "patch-header", ("arch/x86/platform/pvh/head.S",), "8e72893143934486d79fed7550464f0c07cbf0c24eab25b3e3b0c0f95ce4ca17"),
    ("compat-021", "compiler-kernel-compatibility", "host-kernel/rocky/patches/0023-rust-update-no-alloc-shim-marker-rust-1.92.patch", "aeb6af53a40049a009c9973d910e4c8a6286075b88512db051778e5a4595a77b", "local-rocky-exact-build-compatibility", "github-actions:run=32082343363,job=95547626904,artifact=9305826810", "patch-header", ("rust/kernel/alloc/allocator.rs", "rust/kernel/lib.rs"), "0155ea0d05d540fc7ce0aefde08c559ac792ca69b0401b85e5dd92059bf0b3d2"),
    ("parent-001", "project-parent-integration", "host-kernel/kbuild/patches/0001-drivers-misc-add-mckernel-rust-host-modules.patch", "25b0724a2523c3fd5d6d8b824b72c6e6b19c2b16edebaa6719b53c22d4d5c7d9", "mckernel-repository-overlay", "parent-integration-v1:c806e6cda3be3e6f4b92cef35a0d5369738bae5b87e32ed4f486489d3435db2f", "unreviewed-bound-linux-parent-targets", ("drivers/misc/Makefile", "drivers/misc/Kconfig"), "18b2a097a21c8d7da38da36aca3f287b49d317cef67d12599e064718272635b3"),
    ("generic-003", "generic-rust-abstraction-binding", "host-kernel/kbuild/patches/0002-rust-bindings-expose-module-parameters.patch", "e01b48d89e4126eb3c31b355491ec95e3f31458de79ffd6e28d1bae71ddec14c", "mckernel-repository-overlay", "repository-overlay:e01b48d89e4126eb3c31b355491ec95e3f31458de79ffd6e28d1bae71ddec14c", "linux-target-file", ("rust/bindings/bindings_helper.h",), "39715db0bf0716e69e68cc0ff25b120242537692bc58283b60916a875226fb18"),
)

EXPECTED_PATCHES = []
for _order, _data in enumerate(_PATCH_DATA, 1):
    _entry = {
        "id": _data[0],
        "layer": _data[1],
        "license_basis": _data[6],
        "license_expression": (
            None if _data[0] == "parent-001" else
            "GPL-2.0" if _data[6] in (
                "linux-submission-and-target-file", "linux-target-file"
            ) else "GPL-2.0-only"
        ),
        "order": _order,
        "origin": _data[4],
        "path": _data[2],
        "postimage_closure_sha256": _data[8],
        "provenance": _data[5],
        "sha256": _data[3],
        "touched_paths": list(_data[7]),
    }
    EXPECTED_PATCHES.append(_entry)

EXPECTED_LAYERS = [
    {
        "id": "compiler-kernel-compatibility",
        "patch_count": 21,
        "scope": "compiler and kernel compatibility only; no project policy",
    },
    {
        "id": "generic-rust-abstraction-binding",
        "patch_count": 3,
        "scope": "generic Rust abstractions and bindings only; no project policy",
    },
    {
        "id": "project-parent-integration",
        "patch_count": 1,
        "scope": "separate exact parent Kconfig/Kbuild insertion; excluded from the generic layer",
    },
]

EXPECTED_C_HUNK_DIGESTS = [
    {"patch_id": "compat-011", "path": "mm/ksm.c", "sha256": "638b669131254d3801c9c654fbf9fe8ba552cb572af388036bc5f028a8db5f6c"},
    {"patch_id": "compat-012", "path": "fs/netfs/fscache_cache.c", "sha256": "74282bfc0a62d8b62e5d9f45f1064f0db8ac2b3850f0cabf2fa9dff145d06c0d"},
    {"patch_id": "compat-012", "path": "fs/netfs/fscache_cookie.c", "sha256": "541536bf085c7f4ad48a6fa2ebecc75d528734913935a57029e2a53ff6ad3ea0"},
    {"patch_id": "compat-013", "path": "lib/crypto/aescfb.c", "sha256": "72c3dcc901ed3e3b3cc6cb6d758898e0b227a3a1fcc4f05ad006dc8600f3b161"},
    {"patch_id": "compat-013", "path": "lib/crypto/aesgcm.c", "sha256": "d648fb131bc0bf729bf4920d6668151be2b7072e4ac905bdb2dc7bd3ea2243fc"},
    {"patch_id": "compat-014", "path": "drivers/iio/magnetometer/ak8974.c", "sha256": "4f6458e2d4e30e7d6ca3245f825a4fe0657f975248da25d7169c44299b3b9536"},
    {"patch_id": "compat-014", "path": "drivers/net/wireless/ath/carl9170/fw.c", "sha256": "398971e9054850696963452cee74c41653c0710e598e6e69d887f794e6986060"},
    {"patch_id": "compat-014", "path": "fs/cachefiles/key.c", "sha256": "e4ecbf912d1a216560976c57d0c8ae338912b6886144de4ee198a92dfd109005"},
    {"patch_id": "generic-002", "path": "rust/bindings/bindings_helper.h", "sha256": "25efbe3bdd7cd4ab47123c11998f7f314be09676e182aea7cd5bc32d3e3aea20"},
    {"patch_id": "compat-019", "path": "tools/objtool/check.c", "sha256": "e2c2b10fab33410f86256ba05f55c6da994bd5491df0227d47feddb132b97ce0"},
    {"patch_id": "generic-003", "path": "rust/bindings/bindings_helper.h", "sha256": "1df6fd85120ef18f862ad4fb8d9d7abdd9bb3cbc814256ef4baae96d4a4c90ea"},
]

EXPECTED_SOURCE_BINDING = {
    "fixture_preimage_closure_sha256": INITIAL_CLOSURE_SHA256,
    "fixture_root": FIXTURE_ROOT,
    "generator_fixture_path": TARGET_FIXTURE,
    "generator_fixture_sha256": TARGET_FIXTURE_SHA256,
    "kernel_archive_sha256": "4a174d47b8874a2139efcd1ac1ab2d6b80ae7a0ca62f0ae4596fd20cf62a3533",
    "parent_integration_authority_path": PARENT_AUTHORITY_PATH,
    "parent_integration_authority_sha256": PARENT_AUTHORITY_SHA256,
    "source_lock_id": SOURCE_LOCK_ID,
    "source_lock_path": SOURCE_LOCK_PATH,
    "source_lock_sha256": SOURCE_LOCK_SHA256,
}

EXPECTED_SEMANTIC_POLICY = {
    "audited_c_hunk_digests": EXPECTED_C_HUNK_DIGESTS,
    "export_symbol_injection_allowed": False,
    "forbidden_generic_policy_tokens": FORBIDDEN_POLICY_TOKENS,
    "new_project_c_helpers_allowed": False,
    "only_allowed_new_source_path": ONLY_NEW_SOURCE_PATH,
    "parent_integration_exception": (
        "Only the two digest-bound parent Kconfig/Kbuild insertion lines are allowed; "
        "the parent patch is not generic Linux-core policy."
    ),
}

EXPECTED_REPLAY = {
    "command": "patch -p1 --batch --forward --fuzz=0 --no-backup-if-mismatch",
    "external_current_head_build_proof": False,
    "final_postimage_closure_sha256": "39715db0bf0716e69e68cc0ff25b120242537692bc58283b60916a875226fb18",
    "full_external_parent_preimage_execution_proof": False,
    "parent_seed_scope": (
        "Repository-bounded minimal drivers/misc Makefile and Kconfig context; the "
        "full parent preimage hashes remain bound by parent-integration-v1 but are "
        "not present as repository fixtures."
    ),
    "second_application_must_fail": True,
}

EXPECTED_GATE = {
    "credit_eligible": False,
    "gate_id": "RK-006",
    "gate_status_claimed": "TODO",
    "tracker_credit": False,
}

EXPECTED_REVIEW = {
    "durable_archive_complete": False,
    "independent_review_complete": False,
}

EXPECTED_TOP_KEYS = {
    "authority_id", "claim_scope", "gate", "layers", "patches", "remaining_blockers",
    "replay", "review", "schema_version", "semantic_policy", "source_binding",
}
PATCH_KEYS = {
    "id", "layer", "license_basis", "license_expression", "order", "origin", "path",
    "postimage_closure_sha256", "provenance", "sha256", "touched_paths",
}


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuthorityError("duplicate JSON key: {}".format(key))
        result[key] = value
    return result


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=_reject_duplicate_pairs)
    except (OSError, UnicodeError, ValueError) as exc:
        if isinstance(exc, AuthorityError):
            raise
        raise AuthorityError("cannot load {}: {}".format(path, exc))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise AuthorityError("cannot read {}: {}".format(path, exc))


def require_type(value, expected, label):
    if type(value) is not expected:
        raise AuthorityError("{} must have exact type {}".format(label, expected.__name__))


def _strict_equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(
            _strict_equal(actual[key], expected[key]) for key in expected
        )
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _strict_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def require_exact(actual, expected, label):
    if not _strict_equal(actual, expected):
        raise AuthorityError("{} does not match the canonical authority".format(label))


def require_keys(value, keys, label):
    require_type(value, dict, label)
    if set(value) != set(keys):
        raise AuthorityError("{} has a non-canonical schema".format(label))


def safe_relative_path(value, label):
    require_type(value, str, label)
    if not value or "\\" in value or "\x00" in value:
        raise AuthorityError("{} is not a safe POSIX path".format(label))
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or any(part in ("", ".", "..") for part in candidate.parts):
        raise AuthorityError("{} is not a safe repository-relative path".format(label))
    if str(candidate) != value:
        raise AuthorityError("{} is not normalized".format(label))
    return candidate


def safe_repository_file(repo, relative, label):
    candidate = safe_relative_path(relative, label)
    current = repo
    for part in candidate.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise AuthorityError("{} is unavailable: {}".format(label, exc))
        if stat.S_ISLNK(mode):
            raise AuthorityError("{} traverses a symlink".format(label))
    if not stat.S_ISREG(mode):
        raise AuthorityError("{} is not a regular file".format(label))
    return current


def safe_repository_directory(repo, relative, label):
    candidate = safe_relative_path(relative, label)
    current = repo
    for part in candidate.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise AuthorityError("{} is unavailable: {}".format(label, exc))
        if stat.S_ISLNK(mode):
            raise AuthorityError("{} traverses a symlink".format(label))
    if not stat.S_ISDIR(mode):
        raise AuthorityError("{} is not a directory".format(label))
    return current


def safe_explicit_regular_file(path, label):
    candidate = Path(path)
    if any(part in ("", "..") for part in candidate.parts):
        raise AuthorityError("{} has an unsafe path component".format(label))
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise AuthorityError("{} is unavailable: {}".format(label, exc))
        if stat.S_ISLNK(mode):
            raise AuthorityError("{} traverses a symlink".format(label))
    if not stat.S_ISREG(mode):
        raise AuthorityError("{} must be a regular file".format(label))
    return current


def _parse_diff_path(value, prefix, label):
    if value == "/dev/null":
        return None
    if not value.startswith(prefix):
        raise AuthorityError("{} lacks {} prefix".format(label, prefix))
    path = value[len(prefix):]
    safe_relative_path(path, label)
    return path


def _normalize_added_code(text):
    """Apply C translation-phase line splicing and remove comments safely."""
    text = re.sub(r"\\[ \t]*\r?\n", "", text)
    output = []
    index = 0
    state = "normal"
    quote = None
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "block-comment":
            if char == "*" and following == "/":
                output.append(" ")
                index += 2
                state = "normal"
            else:
                if char == "\n":
                    output.append("\n")
                index += 1
            continue
        if state == "line-comment":
            if char == "\n":
                output.append("\n")
                state = "normal"
            index += 1
            continue
        if state == "quoted":
            output.append(char)
            if char == "\\" and following:
                output.append(following)
                index += 2
                continue
            if char == quote:
                state = "normal"
                quote = None
            index += 1
            continue
        if char == "/" and following == "*":
            state = "block-comment"
            index += 2
            continue
        if char == "/" and following == "/":
            state = "line-comment"
            index += 2
            continue
        if char in ('"', "'"):
            state = "quoted"
            quote = char
        output.append(char)
        index += 1
    if state == "block-comment":
        raise AuthorityError("unterminated block comment in added hunk")
    normalized = "".join(output)
    string_pair = re.compile(
        r'"((?:\\.|[^"\\])*)"[ \t\r\n]*"((?:\\.|[^"\\])*)"'
    )
    while string_pair.search(normalized):
        normalized = string_pair.sub(lambda match: '"{}{}"'.format(
            match.group(1), match.group(2)
        ), normalized)
    return normalized


def _reject_new_c_helpers(path, added_lines):
    if not path.endswith((".c", ".cc", ".cpp", ".h")):
        return
    code = _normalize_added_code("\n".join(added_lines))
    if re.search(r"(?m)^\s*#\s*define\s+[A-Za-z_][A-Za-z0-9_]*\s*\(", code):
        raise AuthorityError("new function-like C macro helper is forbidden: {}".format(path))
    function_definition = re.compile(
        r"(?m)^\s*"
        r"(?:[A-Za-z_][A-Za-z0-9_]*(?:[ \t\r\n]+|[ \t\r\n]*\*+[ \t\r\n]*)){1,8}"
        r"[A-Za-z_][A-Za-z0-9_]*[ \t\r\n]*\([^;{}]*\)[ \t\r\n]*(?:[;{]|$)"
    )
    if function_definition.search(code):
        raise AuthorityError("new C function helper or prototype is forbidden: {}".format(path))
    for match in re.finditer(
        r"(?m)^\s*#\s*define\s+[A-Za-z_][A-Za-z0-9_]*[ \t]+(.+)$", code
    ):
        if function_definition.search(match.group(1)):
            raise AuthorityError("object-like macro generates a C helper: {}".format(path))
    if re.search(
        r"\b(?:[A-Z0-9_]*DEFINE[A-Z0-9_]*|BPF_CALL_[0-9]+)\s*\(", code
    ):
        raise AuthorityError("function-generating C macro is forbidden: {}".format(path))


def inspect_patch_bytes(data, layer, expected_touched=None):
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise AuthorityError("patch is not UTF-8: {}".format(exc))
    if "\x00" in text or "GIT binary patch" in text or "Binary files " in text:
        raise AuthorityError("binary or NUL-bearing patch is forbidden")
    forbidden_metadata = (
        "old mode ", "new mode ", "deleted file mode ", "similarity index ",
        "rename from ", "rename to ", "copy from ", "copy to ",
    )
    lines = text.splitlines()
    for line in lines:
        if line.startswith(forbidden_metadata) or line == "new file mode 120000":
            raise AuthorityError("mode, rename, copy, deletion, or symlink patch is forbidden")

    diff_headers = []
    old_paths = []
    new_paths = []
    created_paths = []
    added_lines = []
    added_by_path = {}
    removed_by_path = {}
    in_hunk = False
    current_new = None
    for line in lines:
        if line.startswith("diff --git "):
            match = re.match(r"^diff --git (a/[^ ]+) (b/[^ ]+)$", line)
            if not match:
                raise AuthorityError("unsafe or malformed diff header")
            old = _parse_diff_path(match.group(1), "a/", "diff old path")
            new = _parse_diff_path(match.group(2), "b/", "diff new path")
            if old != new:
                raise AuthorityError("patch retargeting or rename is forbidden")
            if new in diff_headers:
                raise AuthorityError("duplicate touched path in patch")
            diff_headers.append(new)
            added_by_path[new] = []
            removed_by_path[new] = []
            current_new = new
            in_hunk = False
        elif line.startswith("--- "):
            old_paths.append(_parse_diff_path(line[4:].split("\t", 1)[0], "a/", "--- path"))
            in_hunk = False
        elif line.startswith("+++ "):
            new_paths.append(_parse_diff_path(line[4:].split("\t", 1)[0], "b/", "+++ path"))
            in_hunk = False
        elif line.startswith("new file mode "):
            if line != "new file mode 100644" or current_new is None:
                raise AuthorityError("only regular 100644 new files are allowed")
            created_paths.append(current_new)
        elif line.startswith("@@ "):
            hunk = re.match(
                r"^@@ -([0-9]+)(?:,([0-9]+))? \+[0-9]+(?:,[0-9]+)? @@",
                line,
            )
            if not hunk:
                raise AuthorityError("malformed unified-diff hunk header")
            old_count = int(hunk.group(2) if hunk.group(2) is not None else "1")
            if old_count == 0 and current_new not in created_paths:
                raise AuthorityError("zero-preimage hunk lacks exact new-file metadata")
            in_hunk = True
        elif in_hunk and line.startswith("+"):
            added_lines.append(line[1:])
            if current_new is None:
                raise AuthorityError("added hunk lacks a diff target")
            added_by_path[current_new].append(line[1:])
        elif in_hunk and line.startswith("-"):
            if current_new is None:
                raise AuthorityError("removed hunk lacks a diff target")
            removed_by_path[current_new].append(line[1:])

    if not diff_headers or len(old_paths) != len(diff_headers) or len(new_paths) != len(diff_headers):
        raise AuthorityError("patch diff/header closure is incomplete")
    for index, path in enumerate(diff_headers):
        old = old_paths[index]
        new = new_paths[index]
        if new != path or (old is not None and old != path):
            raise AuthorityError("patch body retargets a diff header")
        if old is None and path not in created_paths:
            raise AuthorityError("new path lacks a regular new-file declaration")
        if path in created_paths and old is not None:
            raise AuthorityError("new-file declaration lacks a /dev/null preimage")
    if len(created_paths) != len(set(created_paths)):
        raise AuthorityError("duplicate new-file declaration")
    if any(not added_by_path[path] for path in created_paths):
        raise AuthorityError("new file has no added-hunk payload")
    if any(path.endswith((".c", ".cc", ".cpp", ".h")) for path in created_paths):
        raise AuthorityError("new C or C-header helper is forbidden")
    if any(path != ONLY_NEW_SOURCE_PATH for path in created_paths):
        raise AuthorityError("unexpected new source path")
    if created_paths and layer != "generic-rust-abstraction-binding":
        raise AuthorityError("new source exists outside the generic Rust layer")

    added_text = "\n".join(added_lines)
    normalized_added = re.sub(r"\s*##\s*", "", _normalize_added_code(added_text))
    export_family = re.compile(
        r"\b[A-Za-z_]*EXPORT[A-Za-z0-9_]*SYMBOL[A-Za-z0-9_]*\b",
        re.IGNORECASE,
    )
    if export_family.search(normalized_added):
        raise AuthorityError("EXPORT_SYMBOL injection is forbidden")
    if layer != "project-parent-integration":
        for token in FORBIDDEN_POLICY_TOKENS:
            if token.lower() in normalized_added.lower():
                raise AuthorityError("project policy token in generic/core patch: {}".format(token))
    else:
        expected_parent_additions = {
            "drivers/misc/Makefile": [
                "obj-$(CONFIG_MCKERNEL_IHK_RUST)\t+= mckernel/"
            ],
            "drivers/misc/Kconfig": [
                'source "drivers/misc/mckernel/Kconfig"'
            ],
        }
        if added_by_path != expected_parent_additions or any(removed_by_path.values()):
            raise AuthorityError("parent integration additions exceed the exact exception")
    for path, path_added_lines in added_by_path.items():
        _reject_new_c_helpers(path, path_added_lines)
    if expected_touched is not None and diff_headers != list(expected_touched):
        raise AuthorityError("patch touched-path closure mismatch")
    return {
        "added_lines": added_lines,
        "added_by_path": added_by_path,
        "created_paths": created_paths,
        "removed_by_path": removed_by_path,
        "touched_paths": diff_headers,
    }


def _fixture_has_gpl_2_signal(fixture_dir, relative):
    path = fixture_dir / relative
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise AuthorityError("license target is unavailable: {}: {}".format(relative, exc))
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise AuthorityError("license target is not a regular file: {}".format(relative))
    header = path.read_bytes()[:256]
    markers = (
        b"// SPDX-License-Identifier: GPL-2.0\n",
        b"/* SPDX-License-Identifier: GPL-2.0 */\n",
    )
    if not any(marker in header for marker in markers):
        raise AuthorityError("target lacks the bound GPL-2.0 SPDX signal: {}".format(relative))


def _verify_provenance(row, text, parent_authority, fixture_dir, inspection):
    provenance = row["provenance"]
    if provenance.startswith("linux-commit:"):
        if row["origin"] != "linux-kernel-community":
            raise AuthorityError("{} Linux provenance has the wrong origin".format(row["id"]))
        commit = provenance.split(":", 1)[1]
        if not text.startswith("From {} Mon Sep 17 00:00:00 2001\n".format(commit)):
            raise AuthorityError("{} provenance commit mismatch".format(row["id"]))
        if any(marker not in text for marker in (
            "\nFrom: ", "\nDate: ", "\nSubject: ", "\nSigned-off-by: "
        )):
            raise AuthorityError("{} lacks authorship provenance".format(row["id"]))
    elif provenance.startswith("github-actions:"):
        if row["origin"] != "local-rocky-exact-build-compatibility":
            raise AuthorityError("{} local provenance has the wrong origin".format(row["id"]))
        match = re.match(r"^github-actions:run=([0-9]+),job=([0-9]+),artifact=([0-9]+)$", provenance)
        if not match:
            raise AuthorityError("invalid local provenance")
        run_id, job_id, artifact_id = match.groups()
        if "Observed-Run-ID: {}".format(run_id) in text:
            markers = (
                "Observed-Run-ID: {}".format(run_id),
                "Observed-Job-ID: {}".format(job_id),
                "Observed-Artifact-ID: {}".format(artifact_id),
            )
        else:
            markers = (
                "Failure-Run: {}".format(run_id),
                "Failure-Job: {}".format(job_id),
                "Failure-Artifact: {}".format(artifact_id),
            )
        for marker in markers:
            if marker not in text:
                raise AuthorityError("{} local provenance mismatch: {}".format(row["id"], marker))
        if "\nFrom: " not in text or "\nSigned-off-by: " not in text:
            raise AuthorityError("{} local authorship provenance is incomplete".format(row["id"]))
    elif provenance.startswith("parent-integration-v1:"):
        if row["origin"] != "mckernel-repository-overlay" or not text:
            raise AuthorityError("{} parent overlay origin is invalid".format(row["id"]))
        digest = provenance.split(":", 1)[1]
        if digest != PARENT_AUTHORITY_SHA256:
            raise AuthorityError("{} parent authority provenance mismatch".format(row["id"]))
        patch = parent_authority.get("patch", {})
        require_exact(patch.get("repository_path"), row["path"], "parent patch path")
        require_exact(patch.get("sha256"), row["sha256"], "parent patch digest")
        require_exact(parent_authority.get("credit_eligible"), False, "parent credit")
    elif provenance.startswith("repository-overlay:"):
        if row["origin"] != "mckernel-repository-overlay" or not text:
            raise AuthorityError("{} repository overlay origin is invalid".format(row["id"]))
        if provenance.split(":", 1)[1] != row["sha256"]:
            raise AuthorityError("{} repository overlay digest mismatch".format(row["id"]))
    else:
        raise AuthorityError("{} has an unsupported provenance scheme".format(row["id"]))

    basis = row["license_basis"]
    if basis == "patch-header":
        if row["license_expression"] != "GPL-2.0-only":
            raise AuthorityError("{} patch-header expression mismatch".format(row["id"]))
        if "\nLicense: GPL-2.0-only\n" not in text:
            raise AuthorityError("{} patch-header license mismatch".format(row["id"]))
    elif basis == "linux-submission-and-target-file":
        if row["license_expression"] != "GPL-2.0" or not provenance.startswith("linux-commit:"):
            raise AuthorityError("{} Linux submission license basis mismatch".format(row["id"]))
        if "\nLink: https://" not in text:
            raise AuthorityError("{} lacks its bound Linux submission link".format(row["id"]))
        for relative in row["touched_paths"]:
            if relative in inspection["created_paths"]:
                if "// SPDX-License-Identifier: GPL-2.0" not in inspection["added_by_path"][relative]:
                    raise AuthorityError("{} new file lacks its GPL-2.0 SPDX signal".format(row["id"]))
            else:
                _fixture_has_gpl_2_signal(fixture_dir, relative)
    elif basis == "linux-target-file":
        if row["license_expression"] != "GPL-2.0" or inspection["created_paths"]:
            raise AuthorityError("{} target-file license basis mismatch".format(row["id"]))
        for relative in row["touched_paths"]:
            _fixture_has_gpl_2_signal(fixture_dir, relative)
    elif basis == "unreviewed-bound-linux-parent-targets":
        if row["id"] != "parent-001" or row["license_expression"] is not None:
            raise AuthorityError("{} unreviewed parent license signal mismatch".format(row["id"]))
        if not provenance.startswith("parent-integration-v1:"):
            raise AuthorityError("{} unreviewed license lacks parent binding".format(row["id"]))
    else:
        raise AuthorityError("{} has an unsupported license basis".format(row["id"]))


def _validate_manifest(manifest):
    require_keys(manifest, EXPECTED_TOP_KEYS, "manifest")
    require_exact(manifest["schema_version"], 1, "schema version")
    require_exact(manifest["authority_id"], AUTHORITY_ID, "authority id")
    require_exact(manifest["claim_scope"], CLAIM_SCOPE, "claim scope")
    require_exact(manifest["gate"], EXPECTED_GATE, "gate")
    require_exact(manifest["layers"], EXPECTED_LAYERS, "layers")
    require_exact(manifest["source_binding"], EXPECTED_SOURCE_BINDING, "source binding")
    require_exact(manifest["semantic_policy"], EXPECTED_SEMANTIC_POLICY, "semantic policy")
    require_exact(manifest["replay"], EXPECTED_REPLAY, "replay")
    require_exact(manifest["remaining_blockers"], BLOCKERS, "remaining blockers")
    require_exact(manifest["review"], EXPECTED_REVIEW, "review")
    require_type(manifest["patches"], list, "patches")
    if len(manifest["patches"]) != 25:
        raise AuthorityError("authority must contain exactly 25 patch rows")
    for index, row in enumerate(manifest["patches"]):
        require_keys(row, PATCH_KEYS, "patch row {}".format(index + 1))
    require_exact(manifest["patches"], EXPECTED_PATCHES, "ordered patch authority")
    counts = {}
    paths = []
    identifiers = []
    for row in manifest["patches"]:
        counts[row["layer"]] = counts.get(row["layer"], 0) + 1
        paths.append(row["path"])
        identifiers.append(row["id"])
    require_exact(counts, {
        "compiler-kernel-compatibility": 21,
        "generic-rust-abstraction-binding": 3,
        "project-parent-integration": 1,
    }, "layer counts")
    if len(paths) != len(set(paths)) or len(identifiers) != len(set(identifiers)):
        raise AuthorityError("duplicate patch path or identifier")


def _verify_bound_inputs(repo, manifest):
    source_lock = safe_repository_file(repo, SOURCE_LOCK_PATH, "source lock")
    if sha256_file(source_lock) != SOURCE_LOCK_SHA256:
        raise AuthorityError("source lock digest mismatch")
    source = load_json(source_lock)
    require_exact(source.get("lock_id"), SOURCE_LOCK_ID, "source lock id")
    require_exact(source.get("embedded_objects", [None, None, {}])[2].get("sha256"),
                  EXPECTED_SOURCE_BINDING["kernel_archive_sha256"], "kernel archive")
    parent = safe_repository_file(repo, PARENT_AUTHORITY_PATH, "parent authority")
    if sha256_file(parent) != PARENT_AUTHORITY_SHA256:
        raise AuthorityError("parent integration authority digest mismatch")
    parent_authority = load_json(parent)
    target_fixture = safe_repository_file(repo, TARGET_FIXTURE, "target fixture")
    if sha256_file(target_fixture) != TARGET_FIXTURE_SHA256:
        raise AuthorityError("target fixture digest mismatch")
    fixture_dir = safe_repository_directory(repo, FIXTURE_ROOT, "fixture root")
    for base, directories, files in os.walk(str(fixture_dir), followlinks=False):
        for name in directories + files:
            candidate = Path(base) / name
            if candidate.is_symlink():
                raise AuthorityError("fixture tree contains a symlink")

    patch_paths = []
    expected_c_hunks = {
        (entry["patch_id"], entry["path"]): entry["sha256"]
        for entry in EXPECTED_C_HUNK_DIGESTS
    }
    observed_c_hunks = set()
    for row in manifest["patches"]:
        path = safe_repository_file(repo, row["path"], "patch {}".format(row["id"]))
        data = path.read_bytes()
        if sha256_bytes(data) != row["sha256"]:
            raise AuthorityError("{} digest mismatch".format(row["id"]))
        inspection = inspect_patch_bytes(data, row["layer"], row["touched_paths"])
        for touched_path, added in inspection["added_by_path"].items():
            if touched_path.endswith((".c", ".cc", ".cpp", ".h")):
                key = (row["id"], touched_path)
                if key not in expected_c_hunks:
                    raise AuthorityError("unaudited C/C-header added hunk: {} {}".format(*key))
                digest = sha256_bytes("\n".join(added).encode("utf-8"))
                if digest != expected_c_hunks[key]:
                    raise AuthorityError("audited C/C-header hunk digest mismatch: {} {}".format(*key))
                observed_c_hunks.add(key)
        _verify_provenance(
            row,
            data.decode("utf-8", errors="strict"),
            parent_authority,
            fixture_dir,
            inspection,
        )
        if inspection["created_paths"] and row["id"] != "generic-002":
            raise AuthorityError("only generic-002 may create the one generic Rust source")
        patch_paths.append(path)
    if observed_c_hunks != set(expected_c_hunks):
        raise AuthorityError("audited C/C-header hunk closure is incomplete")
    return fixture_dir, target_fixture, patch_paths


def _closure_digest(root, touched_paths):
    rows = []
    for relative in sorted(touched_paths):
        safe_relative_path(relative, "closure path")
        path = root / relative
        if path.exists():
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                raise AuthorityError("non-regular replay closure member: {}".format(relative))
            data = path.read_bytes()
            rows.append({
                "mode": stat.S_IMODE(mode),
                "path": relative,
                "sha256": sha256_bytes(data),
                "size": len(data),
            })
        else:
            rows.append({"mode": None, "path": relative, "sha256": None, "size": None})
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(canonical)


def _run_patch(patch_program, root, patch_path, dry_run=False):
    command = [
        patch_program, "-p1", "--batch", "--forward", "--fuzz=0",
        "--no-backup-if-mismatch",
    ]
    if dry_run:
        command.append("--dry-run")
    command.extend(["-i", str(patch_path)])
    return subprocess.run(
        command,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )


def _replay(repo, manifest, fixture_dir, target_fixture, patch_paths):
    patch_program = shutil.which("patch")
    if patch_program is None:
        raise AuthorityError("GNU patch is required for fuzz=0 replay")
    touched = []
    for row in manifest["patches"]:
        for relative in row["touched_paths"]:
            if relative not in touched:
                touched.append(relative)
    with tempfile.TemporaryDirectory(prefix="rk006-authority-") as directory:
        root = Path(directory) / "linux"
        shutil.copytree(str(fixture_dir), str(root))
        target = root / "scripts/generate_rust_target.rs"
        target.write_bytes(target_fixture.read_bytes())
        target.chmod(0o644)
        misc = root / "drivers/misc"
        misc.mkdir(parents=True, exist_ok=True)
        (misc / "Makefile").write_text(
            "obj-$(CONFIG_NSM)\t\t+= nsm.o\n"
            "obj-$(CONFIG_MARVELL_CN10K_DPI)\t+= mrvl_cn10k_dpi.o\n"
            "obj-y\t\t\t\t+= keba/\n",
            encoding="utf-8",
        )
        (misc / "Kconfig").write_text(
            'source "drivers/misc/pvpanic/Kconfig"\n'
            'source "drivers/misc/mchp_pci1xxxx/Kconfig"\n'
            'source "drivers/misc/keba/Kconfig"\n'
            "endmenu\n",
            encoding="utf-8",
        )
        (misc / "Makefile").chmod(0o644)
        (misc / "Kconfig").chmod(0o644)
        missing_preimages = sorted(
            relative for relative in touched if not (root / relative).exists()
        )
        if missing_preimages != [ONLY_NEW_SOURCE_PATH]:
            raise AuthorityError("unexpected replay preimage absence: {}".format(missing_preimages))
        if _closure_digest(root, touched) != INITIAL_CLOSURE_SHA256:
            raise AuthorityError("repository fixture preimage closure mismatch")
        for row, patch_path in zip(manifest["patches"], patch_paths):
            result = _run_patch(patch_program, root, patch_path)
            if result.returncode != 0:
                raise AuthorityError(
                    "{} failed fuzz=0 replay: {}{}".format(
                        row["id"], result.stdout, result.stderr
                    )
                )
            actual = _closure_digest(root, touched)
            if actual != row["postimage_closure_sha256"]:
                raise AuthorityError("{} postimage closure mismatch".format(row["id"]))
        for row, patch_path in zip(manifest["patches"], patch_paths):
            result = _run_patch(patch_program, root, patch_path, dry_run=True)
            if result.returncode == 0:
                raise AuthorityError("{} unexpectedly applies a second time".format(row["id"]))
        leftovers = [
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.name.endswith((".orig", ".rej"))
        ]
        if leftovers:
            raise AuthorityError("patch replay left reject/backup files: {}".format(leftovers))
        final_digest = _closure_digest(root, touched)
        if final_digest != EXPECTED_REPLAY["final_postimage_closure_sha256"]:
            raise AuthorityError("final postimage closure mismatch")
    return len(touched)


def validate(repo, manifest_path=None, replay=True):
    repo = Path(repo).resolve()
    if manifest_path is None:
        manifest_path = safe_repository_file(repo, AUTHORITY_PATH, "authority manifest")
    else:
        manifest_path = safe_explicit_regular_file(manifest_path, "authority manifest")
    manifest = load_json(manifest_path)
    _validate_manifest(manifest)
    fixture_dir, target_fixture, patch_paths = _verify_bound_inputs(repo, manifest)
    touched_count = None
    if replay:
        touched_count = _replay(repo, manifest, fixture_dir, target_fixture, patch_paths)
    return {
        "authority_id": AUTHORITY_ID,
        "credit_eligible": False,
        "layer_counts": {"compatibility": 21, "generic": 3, "parent": 1},
        "patch_count": 25,
        "touched_path_count": touched_count,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--manifest")
    parser.add_argument("--no-replay", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = validate(args.repo, args.manifest, replay=not args.no_replay)
    except AuthorityError as exc:
        print("RK-006 patch authority: FAIL: {}".format(exc), file=sys.stderr)
        return 1
    print(
        "RK-006 patch authority: VALID (non-crediting; {} patches; 21/3/1 layers; {} touched paths)".format(
            report["patch_count"],
            report["touched_path_count"] if report["touched_path_count"] is not None else "not replayed",
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
