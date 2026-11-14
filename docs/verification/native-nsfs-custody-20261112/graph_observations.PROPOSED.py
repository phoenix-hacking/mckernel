"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Direct graph observations only; no mount or process control and no admission.
"""
import hashlib
import json
import os
import re
import stat
import time
from pathlib import Path, PurePosixPath

CONTRACT_PATH = Path(__file__).parent / 'parser' / 'contract.json'
CONTRACT_SHA = 'd4b38335f7d1af1998b9999a676ae5eee40b2b640021a144d19169328d68e0fd'
CHILDREN = ('/src/kernel/rust/f03_perf_group_cleanup.rs', '/src/kernel/rust/xpmem_helpers.rs')


def require(ok, message):
    if not ok: raise ValueError(message)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data): return hashlib.sha256(data).hexdigest()


def boot_ns(): return time.clock_gettime_ns(time.CLOCK_BOOTTIME)


def stable(st): return st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def ident(st):
    require(stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode), 'regular file/directory required')
    return dict(device=st.st_dev, inode=st.st_ino, kind='directory' if stat.S_ISDIR(st.st_mode) else 'file')


def process(pid):
    require(type(pid) is int and pid > 0, 'process id')
    row = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
    require(len(row) >= 20 and row[0] not in ('Z', 'X', 'x'), 'target unavailable')
    ns = os.stat('/proc/%d/ns/mnt' % pid)
    return (row[19], ns.st_dev, ns.st_ino)


def decode_path(text):
    # mountinfo permits exactly the kernel's escaped whitespace/backslash octets.
    def replace(match):
        code = match.group(1)
        require(code in ('040', '011', '012', '134'), 'unknown mountinfo escape')
        return chr(int(code, 8))
    result = re.sub(r'\\([0-7]{3})', replace, text)
    require('\\' not in re.sub(r'\\(?:040|011|012|134)', '', text), 'bad mountinfo escape')
    return result


def _mount_covers(path, point):
    return path == point or path.startswith(point.rstrip('/') + '/')


class MountTable(dict):
    """Visible rows plus the complete kernel record set, without mount control.

    The flat dict keeps the registered callers' three-field wire values.
    all_rows retains hidden records and every original field for equality.
    Visibility follows parent-mounted pathname traversal, never row/ID order.
    """
    def __init__(self, records):
        self.by_id = {row['mount_id']: row for row in records}
        require(len(self.by_id) == len(records), 'duplicate mount id')
        self.all_rows = tuple(tuple(row['fields']) for row in
                              sorted(records, key=lambda row: row['mount_id']))
        self.children = {key: [] for key in self.by_id}
        anchors = []
        for row in records:
            ident = row['mount_id']; parent = row['parent_mount_id']
            if parent == ident or parent not in self.by_id:
                require(row['point'] == '/', 'mount parent outside visible root')
                anchors.append(ident)
            else:
                require(_mount_covers(row['point'], self.by_id[parent]['point']),
                        'mount parent path mismatch')
                self.children[parent].append(ident)
        require(len(anchors) == 1, 'ambiguous mount namespace root')
        self.root_id = anchors[0]
        # Linux's unattached/root mount uses mnt_parent == itself. Only that
        # unique '/' anchor may terminate here; every other cycle is rejected.
        for ident in self.by_id:
            current = ident; seen = set()
            while current != self.root_id:
                require(current not in seen, 'cyclic mount topology')
                seen.add(current)
                current = self.by_id[current]['parent_mount_id']
                require(current in self.by_id, 'unbound mount parent')
        visible = {}
        for point in sorted({row['point'] for row in records}):
            row = self.resolve(point)
            if row['point'] == point:
                visible[point] = {key: row[key] for key in
                                  ('mount_id', 'parent_mount_id', 'access')}
        super().__init__(visible)

    def resolve(self, path):
        p = PurePosixPath(path)
        require(p.is_absolute() and str(p) == path and '..' not in p.parts,
                'noncanonical mount lookup path')
        current = self.root_id; seen = set()
        while True:
            require(current not in seen, 'cyclic visible mount stack')
            seen.add(current)
            children = [self.by_id[key] for key in self.children[current]
                        if _mount_covers(path, self.by_id[key]['point'])]
            if not children:
                return self.by_id[current]
            # Traversal encounters the first mounted ancestor component.
            # Its mounted tree then hides lower-parent descendant mounts.
            first_length = min(len(row['point']) for row in children)
            first = [row for row in children if len(row['point']) == first_length]
            require(len(first) == 1, 'ambiguous visible mount stack')
            current = first[0]['mount_id']

    def __eq__(self, other):
        return (isinstance(other, dict) and
                getattr(other, 'all_rows', None) == self.all_rows and
                dict.__eq__(self, other))

    def __ne__(self, other):
        return not self == other


def parse_mountinfo(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 8 * 1024 * 1024,
            'mountinfo input size')
    records = []; ids = set()
    for line in raw.decode('utf-8').splitlines():
        fields = line.split(' ')
        require('-' in fields and len(fields) >= 10, 'malformed mountinfo')
        sep = fields.index('-')
        require(sep >= 6 and len(fields) == sep + 4 and fields[0].isdigit() and
                fields[1].isdigit(), 'mountinfo fields')
        ident = int(fields[0]); parent = int(fields[1])
        require(ident > 0 and ident not in ids, 'duplicate or invalid mount id')
        ids.add(ident)
        require(re.fullmatch(r'[0-9]+:[0-9]+', fields[2]) is not None,
                'mount device fields')
        device = tuple(int(value) for value in fields[2].split(':'))
        root = decode_path(fields[3]); point = decode_path(fields[4])
        # nsfs.show_path emits its namespace tag/inode instead of a pathname.
        # Current supported HOST rows are mnt:[positive unsigned ns_common.inum].
        nsfs_root = (fields[sep + 1] == 'nsfs' and
                     re.fullmatch(r'mnt:\[[1-9][0-9]{0,9}\]', root) is not None and
                     int(root[5:-1]) <= 0xffffffff)
        require((root.startswith('/') or nsfs_root) and point.startswith('/'),
                'mount path fields')
        opts = fields[5].split(',')
        require(('ro' in opts) != ('rw' in opts), 'ambiguous mount access')
        records.append(dict(mount_id=ident, parent_mount_id=parent, device=device,
                            root=root, point=point, access='ro' if 'ro' in opts else 'rw',
                            fields=tuple(fields)))
    return MountTable(records)


def mount_id(fd):
    raw=Path('/proc/self/fdinfo/%d'%fd).read_text()
    if len(raw)>65536:raise ValueError('fdinfo oversized')
    values=[line.split(':',1)[1].strip() for line in raw.splitlines() if line.startswith('mnt_id:')]
    if len(values)!=1 or not values[0].isdigit() or int(values[0])<=0:
        raise ValueError('descriptor mount id unavailable')
    return int(values[0])


def source_mount(table, path, fd):
    """Join a real already-owned source FD to its uniquely visible mount.

    Caller opened this exact canonical path without symlink substitution and
    retains the FD; this helper never opens, closes, mounts or changes flags.
    """
    require(isinstance(table, MountTable) and type(fd) is int and fd >= 0,
            'actual mount table and held source descriptor required')
    before = os.fstat(fd); observed = mount_id(fd)
    require(stable(os.fstat(fd)) == stable(before), 'held source changed during mount observation')
    row = table.resolve(path)
    require(observed == row['mount_id'] and observed in table.by_id,
            'held source mount is not the visible covering mount')
    require((os.major(before.st_dev), os.minor(before.st_dev)) == row['device'],
            'held source device differs from visible mount')
    require(row['point'] in table and table[row['point']]['mount_id'] == observed,
            'visible source mount row missing')
    return dict(mountpoint=row['point'], mount_id=row['mount_id'],
                parent_mount_id=row['parent_mount_id'], access=row['access'])


def read_mountinfo(pid, expected):
    require(process(pid) == expected, 'target changed before mountinfo')
    with open('/proc/%d/mountinfo' % pid, 'rb') as stream:
        raw = stream.read(8 * 1024 * 1024 + 1)
    require(len(raw) <= 8 * 1024 * 1024 and process(pid) == expected,
            'target changed during mountinfo')
    table = parse_mountinfo(raw)
    require(process(pid) == expected, 'target changed while parsing mountinfo')
    return table


def direct_path(path):
    p = PurePosixPath(path)
    require(p.is_absolute() and str(p) == path and '..' not in p.parts, 'noncanonical host path')
    ancestry = []
    for parent in reversed(p.parents):
        st = os.lstat(str(parent))
        require(stat.S_ISDIR(st.st_mode), 'symlink or non-directory ancestry')
        ancestry.append(dict(path=str(parent), identity=ident(st)))
    st = os.lstat(path)
    ident(st)
    return st, ancestry


def file_sha(path):
    before = os.lstat(path)
    require(stat.S_ISREG(before.st_mode), 'not regular')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        require(stable(os.fstat(fd)) == stable(before), 'file changed before read')
        h = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk: break
            h.update(chunk)
        require(stable(os.fstat(fd)) == stable(before), 'file changed during read')
        return h.hexdigest()
    finally: os.close(fd)


def _walk_error(error):
    raise error


def inventory(root):
    """Canonical recursive identity/content inventory, never follows symlinks."""
    result = []
    total = 0
    held = {}
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=_walk_error):
        held[base] = stable(os.lstat(base))
        dirs.sort(); files.sort()
        names = sorted(dirs + files)
        for name in names:
            path = os.path.join(base, name)
            rel = os.path.relpath(path, root)
            st = os.lstat(path)
            held[path] = stable(st)
            require(len(result) < 500000, 'inventory entry cap')
            if stat.S_ISLNK(st.st_mode):
                if name in dirs: dirs.remove(name)
                result.append([rel, 'symlink', st.st_dev, st.st_ino, os.readlink(path)])
            elif stat.S_ISDIR(st.st_mode):
                result.append([rel, 'directory', st.st_dev, st.st_ino])
            elif stat.S_ISREG(st.st_mode):
                total += st.st_size
                require(total <= 8 * 1024**3, 'inventory byte cap')
                result.append([rel, 'file', st.st_dev, st.st_ino, file_sha(path)])
            else: raise ValueError('unsupported inventory inode')
    require(all(stable(os.lstat(path)) == stamp for path,stamp in held.items()), 'inventory inode changed during scan')
    return sha(canonical(result))


def contract():
    data = CONTRACT_PATH.read_bytes()
    require(sha(data) == CONTRACT_SHA, 'contract changed')
    return json.loads(data)


def snapshot_before_children(pid, expected):
    """Capture real unshadowed parent bytes and identities, before child mounts.

    Caller must separately hold actual privileged-writer exclusion throughout.
    """
    c = contract(); table = read_mountinfo(pid, expected)
    require(all(x not in table for x in CHILDREN), 'child mount already present')
    root = next(row['host'] for row in c['mounts'] if row['target'] == '/src/kernel/rust')
    st, _ = direct_path(root)
    require(stat.S_ISDIR(st.st_mode), 'rust parent absent')
    members = {}
    expected_names = set(c['rust_parent_members'])
    dirs_expected = {str(parent) for name in expected_names for parent in PurePosixPath(name).parents if str(parent) != '.'}
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=_walk_error):
        dirs.sort(); files.sort()
        for name in dirs:
            path = os.path.join(base, name); rel = os.path.relpath(path, root)
            require(rel in dirs_expected and stat.S_ISDIR(os.lstat(path).st_mode), 'extra or symlink directory')
        for name in files:
            path = os.path.join(base, name); rel = os.path.relpath(path, root)
            require(rel in expected_names and stat.S_ISREG(os.lstat(path).st_mode), 'extra or nonregular member')
            s = os.lstat(path); actual = file_sha(path)
            require(actual == c['rust_parent_members'][rel], 'preimage bytes differ')
            members[rel] = dict(identity=ident(s), sha256=actual)
    require(set(members) == expected_names and process(pid) == expected, 'pre-shadow membership or process changed')
    require(all(x not in read_mountinfo(pid, expected) for x in CHILDREN), 'child mount appeared during snapshot')
    return dict(parent_identity=ident(st), members=members, snapshot_sha256=sha(canonical(members))), boot_ns()


def capture_graph(pid, expected, hosts, pre_shadow, content_cache=None):
    """Read all 16 effective mount rows; no authority is inferred from data."""
    c = contract(); table = read_mountinfo(pid, expected)
    require(set(hosts) == {row['target'] for row in c['mounts']}, 'complete host map required')
    rows, view, ids = [], [], set()
    for spec in c['mounts']:
        target = spec['target']; host = hosts[target]
        require(spec['host'] is None or spec['host'] == host, 'host differs from pinned source')
        st, ancestry = direct_path(host)
        key = (st.st_dev, st.st_ino)
        require(key not in ids, 'source identity alias'); ids.add(key)
        mount = table.get(target)
        require(mount is not None and mount['access'] == spec['access'], 'mount missing or access differs')
        visible = os.stat('/proc/%d/root%s' % (pid, target))
        require((visible.st_dev, visible.st_ino, stat.S_IFMT(visible.st_mode)) == (st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode)), 'effective identity differs')
        if target != '/work' and content_cache is not None:
            require(target in content_cache, 'immutable epoch content missing')
            content = content_cache[target]
        else:
            content = file_sha(host) if stat.S_ISREG(st.st_mode) else inventory(host)
        require(spec['sha256'] is None or content == spec['sha256'], 'file content differs')
        row = dict(host=host, target=target, access=mount['access'], identity=ident(st), ancestry=ancestry,
                   mount_id=mount['mount_id'], parent_mount_id=mount['parent_mount_id'], content_sha256=content)
        rows.append(row)
        view.append(dict(target=target, identity=ident(visible), mount_id=mount['mount_id'], access=mount['access'], content_sha256=content))
    require(process(pid) == expected and read_mountinfo(pid, expected) == table, 'mount topology changed during capture')
    require(pre_shadow['parent_identity'] == next(r['identity'] for r in rows if r['target'] == '/src/kernel/rust'), 'parent custody differs')
    return rows, dict(mounts_sha256=sha(canonical(view)), entries=view)
