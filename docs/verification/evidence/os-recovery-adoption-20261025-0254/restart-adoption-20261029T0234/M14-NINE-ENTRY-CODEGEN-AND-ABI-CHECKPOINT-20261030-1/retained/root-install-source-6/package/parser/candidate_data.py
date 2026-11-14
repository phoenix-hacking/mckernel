"""Functional OS source-only DATA parsing; no authentication or release API.

No filesystem observations, subprocesses, mounts, collector or driver calls.
Every supervisor assertion is untrusted DATA, even when internally consistent.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath

CONTRACT_BYTES = (Path(__file__).parent / 'contract.json').read_bytes()
CONTRACT_SHA256 = hashlib.sha256(CONTRACT_BYTES).hexdigest()
CONTRACT = json.loads(CONTRACT_BYTES)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def shape(value, keys):
    require(type(value) is dict and set(value) == set(keys.split()), 'record shape')


def string(value):
    require(type(value) is str and value and '\0' not in value, 'nonempty string')
    return value


def integer(value, minimum=1):
    require(type(value) is int and value >= minimum, 'integer identity')
    return value


def path(value):
    string(value)
    p = PurePosixPath(value)
    require(p.is_absolute() and str(p) == value and '..' not in p.parts and not value.startswith('//'), 'canonical path')
    return p


def digest(value):
    require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'sha256')
    return value


@dataclass(frozen=True)
class Identity:
    device: int
    inode: int
    kind: str


def identity(value, kind=None):
    shape(value, 'device inode kind')
    require(value['kind'] in ('file', 'directory') and (kind is None or value['kind'] == kind), 'identity kind')
    return Identity(integer(value['device'], 0), integer(value['inode']), value['kind'])


@dataclass(frozen=True)
class MountData:
    host: str
    target: str
    access: str
    identity: Identity
    ancestry: tuple
    mount_id: int
    parent_mount_id: int
    content_sha256: str


@dataclass(frozen=True)
class CandidateData:
    """Consistency-checked statements ONLY. Never an authenticated receipt."""
    synthetic: bool
    owner: str
    pid: int
    uid: int
    nonce: str
    lease_sha256: str
    custody_sha256: str
    exclusion: str
    mounts: tuple
    pre_shadow: tuple
    pre_shadow_sha256: str
    view_sha256: str
    contract_sha256: str
    authority: None = None
    status: str = 'UNAUTHENTICATED_CANDIDATE_DATA_ONLY'


def parse_candidate_data(raw):
    """Return immutable DATA; callers need separate authentication and admission.

    The function establishes no source quiescence, custody, mount enforcement,
    freshness, lifetime, output exclusivity, compilation or native acceptance.
    """
    def unique(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, 'duplicate JSON key')
            result[k] = v
        return result
    require(type(raw) is bytes, 'bytes input')
    d = json.loads(raw, object_pairs_hook=unique)
    shape(d, 'synthetic contract_sha256 custody mounts pre_shadow effective_view')
    require(type(d['synthetic']) is bool, 'synthetic tag')
    require(d['contract_sha256'] == CONTRACT_SHA256, 'contract binding')
    c = d['custody']
    shape(c, 'owner pid uid nonce lease_sha256 custody_sha256 exclusion')
    owner, nonce = string(c['owner']), string(c['nonce'])
    pid, uid = integer(c['pid']), integer(c['uid'], 0)
    lease, custody = digest(c['lease_sha256']), digest(c['custody_sha256'])
    require(c['exclusion'] == 'source-writers-excluded-and-work-exclusive', 'custody claim')
    rows = d['mounts']
    require(type(rows) is list and len(rows) == 16, 'exact16 mount count')
    mounts, root_ids, hosts, mount_ids, ancestor_ids = [], set(), set(), {}, {}
    for row, expected in zip(rows, CONTRACT['mounts']):
        shape(row, 'host target access identity ancestry mount_id parent_mount_id content_sha256')
        target, host = str(path(row['target'])), str(path(row['host']))
        require(target == expected['target'], 'target order or duplicate')
        require(row['access'] == expected['access'], 'access')
        require(expected['host'] is None or host == expected['host'], 'known host binding')
        require(host not in hosts, 'host alias'); hosts.add(host)
        ident = identity(row['identity'], 'file' if expected['sha256'] else 'directory')
        key = (ident.device, ident.inode)
        require(key not in root_ids, 'inode alias'); root_ids.add(key)
        content = digest(row['content_sha256'])
        require(expected['sha256'] is None or content == expected['sha256'], 'known content binding')
        ancestry = row['ancestry']
        expected_paths = list(reversed(PurePosixPath(host).parents))
        require(type(ancestry) is list and len(ancestry) == len(expected_paths), 'ancestry completeness')
        parsed_ancestry = []
        seen = set()
        for a, ap in zip(ancestry, expected_paths):
            shape(a, 'path identity')
            require(str(path(a['path'])) == str(ap), 'ancestry path')
            ai = identity(a['identity'], 'directory'); ak = (ai.device, ai.inode)
            require(ak != key and ak not in seen, 'ancestry alias'); seen.add(ak)
            require(a['path'] not in ancestor_ids or ancestor_ids[a['path']] == ai, 'ancestry identity mismatch')
            ancestor_ids[a['path']] = ai
            parsed_ancestry.append((a['path'], ai))
        mid, parent = integer(row['mount_id']), integer(row['parent_mount_id'])
        require(mid not in mount_ids.values() and mid != parent, 'mount id alias')
        parents = [m for m in mounts if PurePosixPath(m.target) in PurePosixPath(target).parents]
        if parents:
            require(parent == max(parents, key=lambda m: len(m.target)).mount_id, 'parent mount identity')
        mount_ids[target] = mid
        mounts.append(MountData(host, target, row['access'], ident, tuple(parsed_ancestry), mid, parent, content))
    # A host mounted root may occur in another source's ancestry; bind it exactly.
    for m in mounts:
        require(m.host not in ancestor_ids or ancestor_ids[m.host] == m.identity, 'host parent identity')
    pre = d['pre_shadow']
    shape(pre, 'parent_identity members snapshot_sha256')
    rust = next(m for m in mounts if m.target == '/src/kernel/rust')
    require(identity(pre['parent_identity'], 'directory') == rust.identity, 'pre-shadow parent identity')
    digest(pre['snapshot_sha256'])
    require(type(pre['members']) is dict and set(pre['members']) == set(CONTRACT['rust_parent_members']), 'full pre-shadow membership')
    parsed_pre, pre_ids = [], set()
    for name, sha in CONTRACT['rust_parent_members'].items():
        member = pre['members'][name]; shape(member, 'identity sha256')
        mi = identity(member['identity'], 'file'); mk = (mi.device, mi.inode)
        require(mk not in root_ids and mk not in pre_ids, 'pre-shadow inode alias'); pre_ids.add(mk)
        require(member['sha256'] == sha, 'pre-shadow bytes')
        parsed_pre.append((name, mi, sha))
    view = d['effective_view']; shape(view, 'mounts_sha256 entries')
    digest(view['mounts_sha256'])
    require(type(view['entries']) is list and len(view['entries']) == 16, 'effective view closure')
    for entry, m in zip(view['entries'], mounts):
        shape(entry, 'target identity mount_id access content_sha256')
        require(entry['target'] == m.target and identity(entry['identity']) == m.identity and type(entry['mount_id']) is int and entry['mount_id'] == m.mount_id and entry['access'] == m.access and entry['content_sha256'] == m.content_sha256, 'effective view binding')
    return CandidateData(d['synthetic'], owner, pid, uid, nonce, lease, custody, c['exclusion'], tuple(mounts), tuple(parsed_pre), pre['snapshot_sha256'], view['mounts_sha256'], CONTRACT_SHA256)
