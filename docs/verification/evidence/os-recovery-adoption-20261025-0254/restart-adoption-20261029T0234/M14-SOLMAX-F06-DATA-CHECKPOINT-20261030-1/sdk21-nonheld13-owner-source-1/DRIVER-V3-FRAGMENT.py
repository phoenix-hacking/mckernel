# Exact policy is bound by the parent and checked without emitting inherited values.
CLEAN_ENV = {'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','LC_ALL':'C',
             'TMPDIR':'/tmp','HOSTNAME':'mckernel-sdk13'}
SOURCE_MAP = Path('/work/sdk13-source-map.json')
MOUNT_MANIFEST = Path('/work/sdk13-effective-mounts.json')
MAX_MOUNTINFO = 4 * 1024 * 1024
MAX_MAP = 64 * 1024 * 1024
MAX_ENTRIES = 500000
MAX_BYTES = 32 * 1024**3


def read_regular(path, maximum, expected_sha=None, identity=None, collect=True):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>maximum:
            raise ValueError('mounted file type or size mismatch: '+str(path))
        if identity is not None and (before.st_dev,before.st_ino,before.st_mode)!=(identity['device'],identity['inode'],identity['mode']):
            raise ValueError('mounted file identity mismatch: '+str(path))
        digest=hashlib.sha256();chunks=[];length=0
        while True:
            chunk=os.read(fd,65536)
            if not chunk: break
            length+=len(chunk)
            if length>maximum: raise ValueError('mounted file growth: '+str(path))
            digest.update(chunk)
            if collect: chunks.append(chunk)
        end=os.fstat(fd); named=os.lstat(path)
        keys=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')
        if length!=before.st_size or any(getattr(before,k)!=getattr(end,k) or getattr(before,k)!=getattr(named,k) for k in keys):
            raise ValueError('mounted file changed during read: '+str(path))
        if expected_sha is not None and digest.hexdigest()!=expected_sha:
            raise ValueError('mounted file content mismatch: '+str(path))
        return b''.join(chunks) if collect else length
    finally:os.close(fd)


def decode_mount_path(raw):
    # mountinfo escapes only these four characters. Unknown escapes fail closed.
    replacements={'040':' ','011':'\t','012':'\n','134':'\\'}
    out=[];i=0
    while i<len(raw):
        if raw[i]=='\\':
            code=raw[i+1:i+4]
            if len(code)!=3 or code not in replacements: raise ValueError('invalid mountinfo escape')
            out.append(replacements[code]);i+=4
        else:out.append(raw[i]);i+=1
    return ''.join(out)


def validate_mountinfo(raw, expected):
    if len(raw)>MAX_MOUNTINFO:raise ValueError('mountinfo too large')
    text=raw.decode('utf8'); seen={}
    for line in text.splitlines():
        fields=line.split(' ')
        if len(fields)<10 or '-' not in fields:raise ValueError('malformed mountinfo')
        target=decode_mount_path(fields[4]);opts=fields[5].split(',')
        if target in seen:raise ValueError('duplicate effective mount point')
        seen[target]=opts
    for target,readonly in expected.items():
        opts=seen.get(target)
        if opts is None or ('ro' not in opts if readonly else 'rw' not in opts):
            raise ValueError('missing or wrong effective mount: '+target)
    for target in seen:
        if (target=='/src' or target.startswith('/src/') or target=='/work' or target.startswith('/work/')) and target not in expected:
            raise ValueError('unexpected nested mount: '+target)
    return len(seen)


def masked(path, shadows):
    return any(path==x or path.startswith(x+'/') for x in shadows)


def validate_tree(target, tree, shadows, counters):
    root=Path(target);rows=tree['entries']
    if not isinstance(rows,list) or len(rows)>MAX_ENTRIES:raise ValueError('tree entry bound')
    expected={}
    for row in rows:
        rel=row.get('relative'); kind=row.get('kind')
        if not isinstance(rel,str) or rel in ('','.') or rel.startswith('/') or '..' in Path(rel).parts or str(Path(rel))!=rel:
            raise ValueError('invalid manifest tree path')
        full=target+'/'+rel
        if masked(full,shadows):continue
        if rel in expected or kind not in ('file','dir','symlink'):raise ValueError('invalid tree entry')
        expected[rel]=row
    actual=set()
    def walk_error(exc): raise exc
    for current,dirs,files in os.walk(root,topdown=True,followlinks=False,onerror=walk_error):
        dirs.sort();files.sort();kept=[]
        for name in dirs+files:
            path=Path(current)/name; rel=path.relative_to(root).as_posix();full=target+'/'+rel
            if masked(full,shadows):continue
            row=expected.get(rel)
            if row is None:raise ValueError('unexpected tree path: '+full)
            st=os.lstat(path);actual.add(rel);counters['entries']+=1
            if counters['entries']>MAX_ENTRIES:raise ValueError('source entry bound')
            if stat.S_ISLNK(st.st_mode):
                if row.get('kind')!='symlink' or os.readlink(path)!=row.get('target'):raise ValueError('tree symlink mismatch: '+full)
                resolved=path.resolve(strict=True)
                if resolved!=root and root not in resolved.parents:raise ValueError('tree symlink escapes mounted root: '+full)
            elif stat.S_ISDIR(st.st_mode):
                if row.get('kind')!='dir':raise ValueError('tree directory mismatch: '+full)
                kept.append(name)
            elif stat.S_ISREG(st.st_mode):
                if row.get('kind')!='file' or st.st_size!=row.get('bytes') or not isinstance(row.get('sha256'),str) or len(row['sha256'])!=64:raise ValueError('tree file size/hash mismatch: '+full)
                counters['bytes']+=st.st_size
                if counters['bytes']>MAX_BYTES:raise ValueError('source byte bound')
                read_regular(path,st.st_size,row['sha256'],collect=False)
            else:raise ValueError('unsupported tree file type: '+full)
        dirs[:]=kept
    if actual!=set(expected):raise ValueError('tree inventory mismatch: '+target)


def validate_effective_view(profile, source_map_sha, manifest_sha, manifest_identity, driver_sha):
    if dict(os.environ)!=CLEAN_ENV:raise ValueError('container environment differs')
    args_identity={'device':manifest_identity[0],'inode':manifest_identity[1],'mode':manifest_identity[2]}
    manifest=json.loads(read_regular(MOUNT_MANIFEST,8*1024*1024,manifest_sha,args_identity))
    if manifest.get('schema')!='mckernel.sdk13.effective-mounts.v1' or manifest.get('profile_sha256')!=PROFILE_SHA256 or manifest.get('source_map_sha256')!=source_map_sha or manifest.get('driver_sha256')!=driver_sha:
        raise ValueError('mount manifest bindings differ')
    source_map=json.loads(read_regular(SOURCE_MAP,MAX_MAP,source_map_sha))
    if source_map.get('schema')!='mckernel.sdk13.source-map.v1' or source_map.get('profile_sha256')!=PROFILE_SHA256:
        raise ValueError('source map binding differs')
    read_regular(Path(__file__),8*1024*1024,driver_sha)
    expected_mounts={};manifest_rows=manifest.get('mounts')
    if not isinstance(manifest_rows,list) or len(manifest_rows)!=33:raise ValueError('mount manifest count')
    rows=profile['readonly_shared_inputs']+profile['readonly_config_and_eight_objects']
    expected_targets=['/work']+[row['container'] for row in rows]+['/work/sdk13-profile.json','/work/sdk13-driver.py','/work/sdk13-source-map.json']
    if [r.get('target') for r in manifest_rows]!=expected_targets:raise ValueError('mount manifest order differs')
    for i,row in enumerate(manifest_rows):
        target=row['target']; readonly=i!=0
        if row.get('readonly') is not readonly:raise ValueError('mount read-only flag differs')
        st=os.lstat(target)
        if (st.st_dev,st.st_ino,st.st_mode)!=(row.get('device'),row.get('inode'),row.get('mode')):
            raise ValueError('mounted source identity differs: '+target)
        expected_mounts[target]=readonly
    expected_mounts[str(MOUNT_MANIFEST)]=True
    fd=os.open('/proc/self/mountinfo',os.O_RDONLY|os.O_CLOEXEC)
    try:
        chunks=[];total=0
        while True:
            chunk=os.read(fd,65536)
            if not chunk:break
            total+=len(chunk)
            if total>MAX_MOUNTINFO:raise ValueError('mountinfo too large')
            chunks.append(chunk)
    finally:os.close(fd)
    mount_count=validate_mountinfo(b''.join(chunks),expected_mounts)
    for row in rows:
        if 'sha256' in row:
            length=read_regular(Path(row['container']),max(1,row.get('bytes',MAX_BYTES)),row['sha256'],collect=False)
            if 'bytes' in row and length!=row['bytes']:raise ValueError('mounted source length differs')
    trees=source_map.get('trees')
    if not isinstance(trees,dict) or set(trees)!={'/src','/src/kernel/rust','/nightly'}:raise ValueError('tree map differs')
    roots={r['container']:r['host'] for r in rows if r['container'] in trees}
    if any(trees[t].get('root')!=roots.get(t) for t in trees):raise ValueError('tree root binding differs')
    counters={'entries':0,'bytes':0}
    all_targets=list(expected_mounts)
    for target in ('/src','/src/kernel/rust','/nightly'):
        shadows=[x for x in all_targets if x.startswith(target+'/')]
        validate_tree(target,trees[target],shadows,counters)
    return {'status':'PASS_EFFECTIVE_MOUNTS_SOURCE_ENV','mount_count':mount_count,
            'verified_tree_entries':counters['entries'],'verified_tree_bytes':counters['bytes'],
            'profile_sha256':PROFILE_SHA256,'source_map_sha256':source_map_sha,
            'mount_manifest_sha256':manifest_sha,'driver_sha256':driver_sha}
