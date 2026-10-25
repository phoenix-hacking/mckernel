"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite deduplicated retention only; no compiler, extraction, deletion or runtime change.
"""
from pathlib import Path
import gzip
import hashlib
import io
import json
import os
import stat
import tarfile

D = Path(__file__).resolve().parent
PLAN = D / "EXACT-CURRENT277-RETENTION-ARCHIVE-PLAN.NOT-GRANTED.json"
PLAN_SHA = "280cb972eef57622376b8bffaca624ca7f4214fcb58521fdd192066a46c830da"
raw_plan = PLAN.read_bytes()
assert hashlib.sha256(raw_plan).hexdigest() == PLAN_SHA
plan = json.loads(raw_plan)
assert os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {0}
O = D / "output-1"
assert O.is_dir() and not list(O.iterdir())


class HashedReader:
    def __init__(self, stream):
        self.stream = stream
        self.hash = hashlib.sha256()
        self.size = 0

    def read(self, count):
        value = self.stream.read(count)
        self.hash.update(value)
        self.size += len(value)
        return value


def member_info(name, size):
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o600
    info.uid = info.gid = 1000
    info.mtime = 0
    return info


results = []
for shard in plan["shards"]:
    fragment = dict(
        scope=plan["scope"], shard=shard["id"], items=shard["items"],
        restoration="Verify payloadSHA, then restore required aliases from each regular member. "
                    "Original path/mode/mtime provenance retained; no source deletion authorized.",
    )
    manifest = (json.dumps(fragment, indent=2, sort_keys=True) + "\n").encode()
    assert len(manifest) == shard["manifest_bytes"]
    target = O / shard["output"]
    with target.open("xb") as raw_output:
        with gzip.GzipFile(filename="", mode="wb", compresslevel=6, mtime=0,
                           fileobj=raw_output) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.USTAR_FORMAT) as archive:
                archive.addfile(member_info("MANIFEST.json", len(manifest)), io.BytesIO(manifest))
                for item in shard["items"]:
                    descriptor = os.open(item["source"], os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
                    with os.fdopen(descriptor, "rb") as source:
                        before = os.fstat(source.fileno())
                        assert stat.S_ISREG(before.st_mode) and before.st_size == item["bytes"]
                        reader = HashedReader(source)
                        archive.addfile(member_info(item["member"], item["bytes"]), reader)
                        assert reader.size == item["bytes"] and reader.hash.hexdigest() == item["sha256"]
                        after = os.fstat(source.fileno())
                        for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink"):
                            assert getattr(before, field) == getattr(after, field)
        raw_output.flush()
        os.fsync(raw_output.fileno())
    assert target.stat().st_size <= shard["conservative_gzip_worst_bytes"] < plan["file_limit_bytes"]
    # Read back every member and payload, without extracting or modifying original files.
    expected = {item["member"]: item for item in shard["items"]}
    seen = set()
    with tarfile.open(target, "r|gz") as archive:
        for member in archive:
            assert member.isfile() and member.name not in seen
            seen.add(member.name)
            stream = archive.extractfile(member)
            if member.name == "MANIFEST.json":
                assert stream.read() == manifest
                continue
            item = expected[member.name]
            reader = HashedReader(stream)
            while reader.read(1 << 20):
                pass
            assert reader.size == item["bytes"] and reader.hash.hexdigest() == item["sha256"]
    assert seen == set(expected) | {"MANIFEST.json"}
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    results.append(dict(path=str(target), bytes=target.stat().st_size,
                        sha256=digest.hexdigest(), payload_members=len(expected),
                        all_members_readback_verified=True))
report = dict(scope=plan["scope"], status="PASS_FINITE_CURRENT277_ARCHIVE_AND_FULL_READBACK",
              plan_sha256=PLAN_SHA, archives=results, source_deletions=0,
              compiler_commands=0, SDK=False, native=False)
with (D / "ACTUAL-CURRENT277-ARCHIVES-READBACK.json").open("x") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps(dict(status=report["status"], archives=len(results),
                      compressed_bytes=sum(item["bytes"] for item in results))))
