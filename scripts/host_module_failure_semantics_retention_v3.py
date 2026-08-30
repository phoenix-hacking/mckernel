"""Retain and classify raw host-module semantic evidence without path races.

This helper is intentionally separate from semantic acceptance.  It runs from
an ``always()`` evidence collector, copies every safely readable member of the
raw bundle pair through held no-follow descriptors, and records why the pair
is absent, incomplete, verified, or invalid.  A retained pair is called
verified only when its checksum sidecar is canonical and its tar bytes pass
the v3 canonical raw-bundle decoder.
"""

from __future__ import print_function

import argparse
import os
from pathlib import Path
import sys

import host_module_failure_semantics_v3 as semantics


BUNDLE_NAME = "host-module-failure-semantics-v3-raw.tar"
SIDECAR_NAME = BUNDLE_NAME + ".sha256"
STATUS_NAME = "host-module-failure-semantics-v3-retention-v1.json"


class RetentionError(Exception):
    pass


def _lexists(path):
    return os.path.lexists(str(path))


def _hold(path, label, maximum):
    try:
        return semantics.hold_confined_object(path, label, maximum)
    except semantics.SemanticsV3Error as exc:
        raise RetentionError(str(exc))


def _publish(path, label, data):
    target = None
    authority = None
    try:
        target = semantics.prepare_empty_output_target(path, label)
        authority = target.create(data)
        authority.replay()
    except semantics.SemanticsV3Error as exc:
        raise RetentionError(str(exc))
    finally:
        if authority is not None:
            authority.close()
        if target is not None:
            target.close()


def _status_bytes(record):
    return semantics.canonical_bytes(record)


def retain(build_dir, evidence_dir):
    build_dir = semantics.lexical_absolute_root(build_dir, "retention build directory")
    evidence_dir = semantics.lexical_absolute_root(
        evidence_dir, "retention evidence directory"
    )
    if not evidence_dir.is_dir() or evidence_dir.is_symlink():
        raise RetentionError("evidence directory must be a real directory")

    source_paths = {
        BUNDLE_NAME: build_dir / BUNDLE_NAME,
        SIDECAR_NAME: build_dir / SIDECAR_NAME,
    }
    presence = dict(
        (name, _lexists(path)) for name, path in source_paths.items()
    )
    authorities = {}
    retained = {}
    errors = []
    limits = {
        BUNDLE_NAME: semantics.MAX_RAW_BUNDLE_BYTES,
        SIDECAR_NAME: 4096,
    }

    try:
        for name in (BUNDLE_NAME, SIDECAR_NAME):
            if not presence[name]:
                continue
            try:
                authorities[name] = _hold(
                    source_paths[name], "raw retention " + name, limits[name]
                )
            except RetentionError as exc:
                errors.append({"name": name, "reason": str(exc)})

        for name in (BUNDLE_NAME, SIDECAR_NAME):
            authority = authorities.get(name)
            if authority is None:
                continue
            authority.replay()
            _publish(
                evidence_dir / name,
                "retained raw semantic evidence " + name,
                authority.data,
            )
            authority.replay()
            retained[name] = {
                "sha256": semantics.sha256_bytes(authority.data),
                "size": len(authority.data),
            }

        if not presence[BUNDLE_NAME] and not presence[SIDECAR_NAME]:
            state = "absent"
        elif set(authorities) != {BUNDLE_NAME, SIDECAR_NAME}:
            state = "invalid" if errors else "incomplete"
        else:
            bundle_data = authorities[BUNDLE_NAME].data
            sidecar_data = authorities[SIDECAR_NAME].data
            expected = semantics.raw_sidecar_bytes(BUNDLE_NAME, bundle_data)
            if sidecar_data != expected:
                state = "invalid"
                errors.append({
                    "name": SIDECAR_NAME,
                    "reason": "checksum sidecar is non-canonical or stale",
                })
            else:
                try:
                    semantics.decode_raw_bundle(bundle_data, sidecar_data)
                except semantics.SemanticsV3Error as exc:
                    state = "invalid"
                    errors.append({
                        "name": BUNDLE_NAME,
                        "reason": str(exc),
                    })
                else:
                    state = "verified"

        record = {
            "errors": errors,
            "presence": presence,
            "retained": retained,
            "schema_version": 1,
            "state": state,
        }
        _publish(
            evidence_dir / STATUS_NAME,
            "raw semantic retention status",
            _status_bytes(record),
        )
        return record
    finally:
        for authority in authorities.values():
            authority.close()


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", required=True)
    parser.add_argument("--evidence-dir", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = retain(args.build_dir, args.evidence_dir)
    except (OSError, RetentionError, semantics.SemanticsV3Error) as exc:
        print("raw semantic evidence retention failed: {0}".format(exc), file=sys.stderr)
        return 2
    print(result["state"])
    return 0 if result["state"] == "verified" else 1


if __name__ == "__main__":
    sys.exit(main())
