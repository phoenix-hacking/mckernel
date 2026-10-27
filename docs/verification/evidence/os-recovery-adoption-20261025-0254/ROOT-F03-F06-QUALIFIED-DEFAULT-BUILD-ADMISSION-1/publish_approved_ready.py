"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Finite metadata publication after Root receives actual independent execution PASS
for the exact input SHA supplied on the CLI. Does not review, launch or retry.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def reference(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def write_new(path, value):
    with path.open('xb') as stream:
        stream.write(encode(value))
        stream.flush()
        os.fsync(stream.fileno())


def publish(preparation, approved_input_sha):
    preparation = Path(preparation)
    if preparation.resolve(strict=True) != preparation:
        raise ValueError('real absolute preparation directory required')
    source = preparation / 'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json'
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != approved_input_sha:
        raise ValueError('exact independently approved input SHA required')
    grant = json.loads(raw)
    if (grant['author'] != '/root' or grant['maximum_invocations'] != 1
            or grant['decision'] != 'GRANT_ONE_CURRENT290_BUILD_ONLY'
            or grant['review'] is not None
            or grant['root_docker_client_only'] is not True):
        raise ValueError('exact new build-only grant required')
    resource_ref = grant['resource_authority']
    resource_path = Path(resource_ref['path'])
    if reference(resource_path) != resource_ref:
        raise ValueError('unchanged reviewed resource authority required')
    resource = json.loads(resource_path.read_bytes())
    if not 0 <= time.time() - resource['observed_at_epoch'] <= 120:
        raise ValueError('resource snapshot expired; never extend or replay')
    review_path = preparation / 'ACTUAL-INDEPENDENT-BUILD-EXECUTION-REVIEW.json'
    grant_path = preparation / 'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json'
    ready_path = preparation / 'HOLDER/ROOT-BUILD-GRANT.READY.json'
    if any(os.path.lexists(path) for path in (review_path, grant_path, ready_path)):
        raise ValueError('review, grant and READY must all be fresh')
    fields = ['nonce', 'runner', 'profile', 'worker', 'resource_authority',
              'input_export_authority', 'fresh_output_root',
              'native_custody_clearance', 'docker_client_prefix',
              'root_docker_client_only']
    review = {key: grant[key] for key in fields}
    review.update(decision='PASS_EXACT_BUILD_ONLY_EXECUTION', independent=True,
                  reviewer='/root/custody_release_review',
                  coexistence_decision='REVIEWED_POSTCLEANUP_ONE_HEAVY',
                  root_attested_actual_approved_input_sha256=approved_input_sha)
    write_new(review_path, review)
    grant['review'] = reference(review_path)
    write_new(grant_path, grant)
    write_new(ready_path, dict(author='/root', nonce=grant['nonce'],
                               grant=reference(grant_path)))
    return dict(status='ROOT_APPROVED_READY_PUBLISHED_ONCE', nonce=grant['nonce'])


if __name__ == '__main__':
    if os.getuid() != 1000 or os.geteuid() != 1000 or len(sys.argv) != 3:
        raise SystemExit('UID1000; publish_approved_ready.py PREPARATION ACTUAL_APPROVED_INPUT_SHA')
    print(json.dumps(publish(Path(sys.argv[1]), sys.argv[2]), sort_keys=True))
