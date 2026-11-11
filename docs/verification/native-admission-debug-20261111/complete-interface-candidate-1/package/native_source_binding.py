"""Exact regular-file source custody for the one named native signal request.

Uses the recovered registered source/epoch providers. It never selects the old
16-mount/157-member graph or treats a controller account reply as permission.
Every changed immutable bit has a durable first prior-flags row, and restoration
requires this admission's actual positive native completion.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import time
import graph_observations as obs
import inplace_custody as source
import immutable_epoch
import native_resource_admission as native
from ownership_latch import CustodyLatch

UNKNOWN = []


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def file_key(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid,
            st.st_nlink, st.st_size, st.st_mtime_ns)


class NativeWorkLatch(CustodyLatch):
    """Keep original durable source publication under fresh native work caps."""
    def __init__(self,admission):
        super().__init__('OWNER_HELD');self.admission=admission

    def publish(self,token,action,*handles):
        self.admission.verify()
        def still_live():
            # apply_plan already persisted prior flags. Recheck after that I/O
            # and any controller round trip, immediately before its real ioctl.
            self.admission._clocks(required_seconds=native.RETIREMENT_RESERVE_SECONDS)
            return action()
        return super().publish(token,still_live,*handles)


class NativeSourceCustody:
    def __init__(self, admission):
        # Supervisor preallocates and retains this object before any open.
        self.state = 'INITIALIZING'
        self.admission = admission
        self.fds = {}; self.before = {}; self.plan = {}
        self.epoch = None; self.journal = None; self.manifest_fd = None
        self.namespace_fd = None; self.failure = None
        self.effective = None; self.effective_sha256 = None
        self.closed_fds = set(); self.close_errors = []
        need(type(admission) is native.NativeAdmission and admission.state == 'CLAIMED',
             'actual named native admission required')
        admission.verify()
        self.lease, self.root_fd = admission.lease, admission.root_fd
        self.latch = NativeWorkLatch(admission)
        spec = admission.cfg['native']['source_manifest']
        need(type(spec) is dict and set(spec) == {'path', 'sha256'}, 'source manifest pin')
        self.manifest_fd, raw = native.root_bootstrap.pinned_root_file(spec['path'], spec['sha256'])
        self.manifest_sha256 = spec['sha256']
        manifest = json.loads(raw, object_pairs_hook=source.unique)
        need(type(manifest) is dict and set(manifest) ==
             {'sources', 'inode_plan_sha256', 'mount_map_sha256'}, 'exact source manifest shape')
        for key in ('inode_plan_sha256', 'mount_map_sha256'):
            native.graph_producer.wire.sha256_hex(manifest[key])
        self.manifest = manifest
        rows = manifest['sources']
        need(type(rows) is list and bool(rows), 'nonempty actual source cut required')
        self.rows = rows
        self.namespace_fd = os.open('/proc/self/ns/mnt', os.O_RDONLY | os.O_CLOEXEC)
        st = os.fstat(self.namespace_fd); self.namespace = (st.st_dev, st.st_ino)
        process = obs.process(os.getpid())
        need((process[1], process[2]) == self.namespace, 'actual source namespace')
        self.mounts = obs.read_mountinfo(os.getpid(), process)
        selected_mounts = {}; seen = {}
        for row in rows:
            need(type(row) is dict and set(row) == {'target', 'host', 'content_sha256'},
                 'source regular-file row shape')
            # Actual DiagnosticOwner uses identical absolute bind destinations.
            need(row['target'] == row['host'] and row['host'] not in self.fds,
                 'unique identical source/target path required')
            native.graph_producer.wire.sha256_hex(row['content_sha256'])
            fd = source.open_exact(row['host']); self.fds[row['host']] = fd
            st = os.fstat(fd)
            need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, 'regular-file source cut only')
            need(source.digest_path(row['host'], st) == row['content_sha256'], 'source bytes differ')
            self.before[row['host']] = file_key(st)
            source.enumerate_source(fd, row['host'], st.st_dev, self.plan, seen)
            ancestors = [p for p in self.mounts if row['host'] == p or row['host'].startswith(p.rstrip('/') + '/')]
            need(bool(ancestors), 'source mount ancestry missing')
            point = max(ancestors, key=len)
            selected_mounts[row['host']] = dict(mountpoint=point, **self.mounts[point])
        self.plan_bytes = canonical({p: list(self.plan[p]) for p in sorted(self.plan)})
        mount_bytes = canonical({'namespace': list(self.namespace), 'roots': selected_mounts})
        need(hashlib.sha256(self.plan_bytes).hexdigest() == manifest['inode_plan_sha256'],
             'Root-admitted first inode/prior-flags plan differs')
        need(hashlib.sha256(mount_bytes).hexdigest() == manifest['mount_map_sha256'],
             'Root-admitted actual mount plan differs')
        need(obs.process(os.getpid()) == process and
             obs.read_mountinfo(os.getpid(), process) == self.mounts, 'source preflight topology changed')
        self.state = 'PREPARED'

    def acquire(self):
        need(self.state == 'PREPARED', 'source custody single acquisition')
        self.admission.verify(required_seconds=self.admission.deadline_seconds+native.COMPLETION_RESERVE_SECONDS)
        token = self.latch.begin('OWNER_HELD')
        name = 'NATIVE-SOURCE-FLAGS-' + self.lease.nonce + '.jsonl'
        self.journal = os.open(name, os.O_WRONLY | os.O_APPEND | os.O_CREAT |
                               os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                               0o600, dir_fd=self.root_fd)
        self._record('INTENT')
        self.state = 'FREEZING'
        try:
            source.apply_plan(self.plan, self.journal, self.lease, self.latch, token)
            roots = {r['target']: r['host'] for r in self.rows}
            hashes = {r['target']: r['content_sha256'] for r in self.rows}
            self.epoch = immutable_epoch.ImmutableEpoch.__new__(immutable_epoch.ImmutableEpoch)
            self.latch.retain(self.epoch)
            self.epoch.__init__(roots, hashes, self.admission.caps['boot'])
            self._verify_files()
            self.admission.verify()
            self.latch.commit(token, 'SOURCE_HELD', self)
            self.state = 'HELD'; self._record('HELD')
            return self
        except BaseException as error:
            self.retain_unknown(error); raise

    def _record(self, status):
        row = dict(status=status, nonce=self.lease.nonce, scope='CURRENT_NAMED_SOURCE_CUT_ONLY',
                   lease_sha256=self.lease.lease_sha256,
                   source_manifest_sha256=self.manifest_sha256)
        source.write_all(self.journal, canonical(row) + b'\n')
        os.fsync(self.journal); os.fsync(self.root_fd)

    def _verify_files(self):
        self.lease.verify()
        ns = os.fstat(self.namespace_fd)
        process = obs.process(os.getpid())
        need((ns.st_dev, ns.st_ino) == self.namespace == (process[1], process[2]),
             'source namespace identity changed')
        need(obs.read_mountinfo(os.getpid(), process) == self.mounts,
             'source mount topology changed')
        for row in self.rows:
            path = row['host']; st = os.fstat(self.fds[path])
            named = source.open_exact(path)
            try:
                need(file_key(st) == self.before[path] == file_key(os.fstat(named)),
                     'held source inode/path changed')
                need(source.flags(self.fds[path]) & source.IMMUTABLE, 'source immutable bit lost')
            finally:
                os.close(named)

    def verify(self, cleanup=False):
        need(self.state == 'HELD', 'source custody not held')
        self.admission.verify(cleanup=cleanup)
        self._verify_files()
        if not cleanup:
            need(self.epoch is not None, 'source epoch absent')
            self.epoch.verify()
            self.admission._clocks(required_seconds=native.RETIREMENT_RESERVE_SECONDS)
        # Cleanup validates every exact held inode/immutable bit and mount
        # topology even after work/account deadlines; it grants no further work.
        return self

    def collect(self):
        self.verify()
        owner = self.admission.owner
        diagnostic, actual = owner_module_manifest(owner)
        need(actual == owner.manifest, 'strict named manifest changed')
        required = {owner.manifest_path}
        required.update(ref['path'] for ref in actual['artifacts'].values())
        required.update(ref['path'] for ref in actual['modules'])
        required.update(owner.admitted_source_paths)
        required.update(self.admission.source_members)
        need(required <= set(self.fds), 'consumed diagnostic source/artifact file omitted from cut')
        return canonical(dict(kind='named-native-source-collection-v1', authority=None,
                              nonce=self.lease.nonce, manifest=actual,
                              manifest_sha256=owner.manifest_sha256,
                              source_manifest_sha256=self.manifest_sha256,
                              source_rows=self.rows))

    def observe_effective(self, row):
        """Called only after the actual owner verifies its real created inspect."""
        self.verify()
        owner = self.admission.owner
        need(self.effective is None and row.get('Id') == owner.container and
             row.get('Image') == owner.owner_image and
             row.get('State', {}).get('Status') == 'created' and
             row['State'].get('Running') is False, 'actual created native view required')
        expected = [(owner.owner_repo, owner.owner_repo, True),
                    (owner.owner_scratch, owner.owner_scratch, True),
                    (str(owner.parent), str(owner.parent), False),
                    (owner.source_package, owner.source_package, True)]
        actual = []
        for mount in row.get('Mounts', []):
            if mount.get('Type') == 'tmpfs':
                need(mount.get('Destination') == '/tmp' and mount.get('RW') is True,
                     'native temporary mount differs')
                continue
            need(mount.get('Type') == 'bind' and type(mount.get('RW')) is bool and
                 mount.get('Propagation') == 'rprivate', 'actual native bind kind')
            actual.append((mount.get('Source'), mount.get('Destination'), not mount['RW']))
        need(sorted(actual) == sorted(expected), 'actual exact four native binds differ')
        root_only={owner.admission_owner_module.IMAGE_RECORD}
        for target in self.fds:
            if target in root_only:
                # The genuine outer preflight consumes this exact pinned image
                # metadata on HOST only; it is not falsely called container RO.
                continue
            covering = [x for x in actual if target == x[1] or target.startswith(x[1].rstrip('/') + '/')]
            need(bool(covering) and max(covering, key=lambda x: len(x[1]))[2] is True,
                 'source cut not in an actual readonly effective bind')
        self.effective = dict(root_only_sources=sorted(root_only), container=owner.container, image=row['Image'],
                              mounts=sorted(actual), state='created',
                              source_manifest_sha256=self.manifest_sha256)
        self.effective_sha256 = hashlib.sha256(canonical(self.effective)).hexdigest()
        return self.effective

    def restore(self, completion):
        need(type(completion) is native.NativeCompletion and
             completion is self.admission.completion and completion.admission is self.admission and
             self.admission.state == 'TERMINAL_CLEAN', 'actual current native completion required')
        self.verify(cleanup=True)
        self.state = 'RESTORING'
        try:
            self._record('RESTORE_BEGIN_AFTER_NATIVE_TERMINAL')
            for path in sorted(self.plan):
                self.lease.verify()
                fd = self.fds[path]; device, inode, kind, original = self.plan[path]
                st = os.fstat(fd)
                named = source.open_exact(path)
                try:
                    need((st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode)) ==
                         (device, inode, kind) and file_key(st) == file_key(os.fstat(named)),
                         'source restoration identity differs')
                    need(source.flags(fd) == (original | source.IMMUTABLE),
                         'source flags changed outside this operation')
                    # Only this exact admission's added bit is restored. A prior
                    # immutable source stays immutable; no old scope is thawed.
                    if not original & source.IMMUTABLE:
                        fcntl.ioctl(fd, source.SETFLAGS, struct.pack('I', original))
                    need(source.flags(fd) == original, 'source prior flags not restored')
                    source.write_all(self.journal, canonical(dict(status='RESTORED_INODE',
                        nonce=self.lease.nonce, path=path, device=device, inode=inode,
                        original_flags=original)) + b'\n'); os.fsync(self.journal)
                finally:
                    os.close(named)
            self._record('RESTORED_CURRENT_SOURCE_CUT_ONLY')
            self.state = 'RESTORED'
            return self
        except BaseException as error:
            self.retain_unknown(error); raise

    def close_restored(self):
        need(self.state == 'RESTORED', 'unrestored source cannot close custody')
        errors = []
        descriptors = list(self.fds.values()) + [self.namespace_fd, self.manifest_fd, self.journal]
        if self.epoch is not None:
            descriptors.append(self.epoch.namespace_fd)
        for fd in descriptors:
            if fd is None or fd in self.closed_fds:
                continue
            # Record a close attempt first: uncertainty never retries a number.
            self.closed_fds.add(fd)
            try: os.close(fd)
            except BaseException as error: errors.append((fd, error))
        self.close_errors = errors
        if errors:
            self.retain_unknown('source close uncertain'); raise RuntimeError('source closure uncertain')
        self.state = 'CLOSED_RESTORED'

    def retain_unknown(self, error):
        self.failure = error; self.state = 'UNKNOWN_RETAINED'; self.latch.fail(error, self)
        if self not in UNKNOWN: UNKNOWN.append(self)
        self.admission.retain_unknown(error)


def owner_module_manifest(owner):
    return owner.admission_owner_module.bound_manifest(owner.manifest_path, owner.manifest_sha256)
