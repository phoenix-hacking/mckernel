"""Finite SAME-inode runtime preparation around the existing named native Root main.
Source proposal only. Root alone issues this combined command after review/admission.
"""
import datetime,fcntl,hashlib,json,math,os,pathlib,resource,signal,stat,struct,sys,time,types
BOOTSTRAP_BYTES=b'"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\nSource-only bootstrap primitives; no install, operation or controller is started.\n"""\nimport fcntl\nimport base64\nimport hashlib\nimport os\nimport resource\nimport socket\nimport stat\nimport struct\nimport sys\nimport types\n\nFS_IOC_GETFLAGS = 0x80086601\nFS_IMMUTABLE_FL = 0x10\n\n\ndef immutable(fd):\n    data=bytearray(4)\n    fcntl.ioctl(fd,FS_IOC_GETFLAGS,data,True)\n    return bool(struct.unpack(\'I\',data)[0] & FS_IMMUTABLE_FL)\n\n\ndef _pinned_file(path, expected_sha, limit=2*1024*1024):\n    """Return retained FD and exact verified bytes; no symlink path components."""\n    if type(path) is not str or not path.startswith(\'/\') or \'//\' in path:\n        raise ValueError(\'root absolute path required\')\n    parts=path.split(\'/\')[1:]\n    if not parts or any(part in (\'\',\'.\',\'..\') for part in parts): raise ValueError(\'bad path\')\n    root=os.open(\'/\',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)\n    try:\n        for index,part in enumerate(parts):\n            st=os.fstat(root)\n            if st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022 or not stat.S_ISDIR(st.st_mode):\n                raise ValueError(\'untrusted source ancestry\')\n            flags=os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW\n            if index<len(parts)-1:flags|=os.O_DIRECTORY\n            child=os.open(part,flags,dir_fd=root)\n            os.close(root);root=child\n        s=os.fstat(root)\n        if (not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_nlink!=1 or\n            stat.S_IMODE(s.st_mode)&0o022 or not immutable(root) or s.st_size>limit):\n            raise ValueError(\'source is not immutable root-owned file\')\n        raw=b\'\'\n        while len(raw)<=limit:\n            chunk=os.read(root,65536)\n            if not chunk:break\n            raw+=chunk\n        if len(raw)>limit or hashlib.sha256(raw).hexdigest()!=expected_sha:\n            raise ValueError(\'source bytes mismatch\')\n        after=os.fstat(root)\n        if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):\n            raise ValueError(\'source changed\')\n        return root,raw\n    except BaseException:\n        os.close(root)\n        raise\n\n\ndef pinned_root_file(path,expected_sha,limit=2*1024*1024):\n    if os.geteuid()!=0:raise ValueError(\'root required\')\n    return _pinned_file(path,expected_sha,limit)\n\n\ndef pinned_validator_file(path,expected_sha,limit=2*1024*1024):\n    if os.getuid()!=1000 or os.geteuid()!=1000:raise ValueError(\'ordinary validator required\')\n    return _pinned_file(path,expected_sha,limit)\n\n\ndef load_verified_validator_module(name,path,expected_sha):\n    fd,raw=pinned_validator_file(path,expected_sha)\n    module=types.ModuleType(name);module.__file__=path\n    if name in sys.modules:os.close(fd);raise ValueError(\'module already loaded\')\n    sys.modules[name]=module\n    try:\n        exec(compile(raw,path,\'exec\'),module.__dict__)\n        return fd,module\n    except BaseException:\n        sys.modules.pop(name,None);os.close(fd);raise\n\n\ndef load_verified_module(name,path,expected_sha):\n    """Execute exactly the bytes read from a held immutable root-owned FD."""\n    fd,raw=pinned_root_file(path,expected_sha)\n    module=types.ModuleType(name);module.__file__=path\n    sys.modules[name]=module\n    try:\n        exec(compile(raw,path,\'exec\'),module.__dict__)\n        return fd,module\n    except BaseException:\n        sys.modules.pop(name,None);os.close(fd);raise\n\n\nSUPERVISOR_INLINE = r"""import base64,json,os,sys,types\nm=types.ModuleType(\'root_bootstrap\');m.__file__=\'<verified-bootstrap-bytes>\';sys.modules[\'root_bootstrap\']=m\nexec(compile(base64.b64decode(sys.argv[1],validate=True),m.__file__,\'exec\'),m.__dict__)\nfd,raw=m.pinned_root_file(sys.argv[2],sys.argv[3]);hold=[fd]\ndef unique(pairs):\n d={}\n for k,v in pairs:\n  if k in d:raise ValueError(\'duplicate loader key\')\n  d[k]=v\n return d\nconfig=json.loads(raw,object_pairs_hook=unique)\nnative=config.get(\'kind\')==\'mckernel-native-signal-loader-v1\'\nkeys={\'modules\',\'extra_files\',\'operation_config_path\',\'operation_config_sha\',\'runtime\'}\nif set(config)!=(keys|{\'kind\'} if native else keys):raise ValueError(\'loader config\')\nnames=(\'ownership_latch\',\'custody_protocol_v2\',\'graph_observations\',\'pidfd_compat\',\'runtime_binding\',\'pidfd_custody\',\'deferred_fork\',\'inplace_custody\',\'immutable_epoch\',\'adapter\',\'materializer\',\'source_freeze\',\'split_inventory\',\'union_server_guarded\',\'graph_producer\',\'graph_server\',\'operation_supervisor\',\'supervisor_entry\')\nnative_names=(\'native_current_owner\',\'native_diagnostic_container_owner\',\'native_resource_admission\',\'native_source_binding\',\'compositor\',\'operation_watchdog\') if native else ()\nif set(config[\'modules\'])!=set(names)|set(native_names):raise ValueError(\'module set\')\nchecker=os.path.join(os.path.dirname(config[\'modules\'][\'materializer\'][\'path\']),\'verify_scripts_fd.py\')\nif native:\n local=os.path.dirname(config[\'modules\'][\'materializer\'][\'path\'])\n transitive={checker,os.path.join(local,\'verified_owner_loader.py\'),os.path.join(local,\'union_owner.py\'),os.path.join(local,\'root_owner_entry.py\')}\n if set(config[\'extra_files\'])!=transitive:raise ValueError(\'native registered transitive source closure\')\nelse:\n if set(config[\'extra_files\'])!={checker}:raise ValueError(\'checker source closure\')\nfor path,sha in config[\'extra_files\'].items():\n fd,_=m.pinned_root_file(path,sha);hold.append(fd)\nfor name in names+native_names:\n spec=config[\'modules\'][name]\n if set(spec)!={\'path\',\'sha256\'}:raise ValueError(\'module pin\')\n fd,mod=m.load_verified_module(name,spec[\'path\'],spec[\'sha256\']);hold.append(fd)\nif config[\'modules\'][\'supervisor_entry\'][\'path\']!=sys.argv[4]:raise ValueError(\'entry path\')\nif set(config[\'runtime\'])!={\'path\',\'sha256\'}:raise ValueError(\'runtime binding\')\nsys.modules[\'runtime_binding\'].verify_current(config[\'runtime\'][\'path\'],config[\'runtime\'][\'sha256\'])\nroot_fd=int(os.environ[\'MCKERNEL_OPERATION_ROOT_FD\']);lease_fd=int(os.environ[\'MCKERNEL_OPERATION_LEASE_FD\'])\nsys.modules[\'supervisor_entry\'].run(config[\'operation_config_path\'],config[\'operation_config_sha\'],root_fd,lease_fd)\n"""\n\n\ndef supervisor_argv(executable,verified_bootstrap_bytes,loader_manifest,loader_sha,entry_path):\n    """Use parent-verified bytes in argv; child executes exactly those bytes."""\n    if type(verified_bootstrap_bytes) is not bytes or not verified_bootstrap_bytes:\n        raise ValueError(\'verified bootstrap bytes required\')\n    return [executable,\'-I\',\'-B\',\'-c\',SUPERVISOR_INLINE,\n            base64.b64encode(verified_bootstrap_bytes).decode(\'ascii\'),loader_manifest,loader_sha,entry_path]\n\n\nVALIDATOR_INLINE = r"""import base64,json,os,sys,types\nm=types.ModuleType(\'root_bootstrap\');m.__file__=\'<verified-bootstrap-bytes>\';sys.modules[\'root_bootstrap\']=m\nexec(compile(base64.b64decode(sys.argv[1],validate=True),m.__file__,\'exec\'),m.__dict__)\nfd,raw=m.pinned_validator_file(sys.argv[2],sys.argv[3]);hold=[fd]\ndef unique(pairs):\n d={}\n for k,v in pairs:\n  if k in d:raise ValueError(\'duplicate loader key\')\n  d[k]=v\n return d\nconfig=json.loads(raw,object_pairs_hook=unique)\nif set(config)!={\'modules\',\'extra_files\',\'runtime\'}:raise ValueError(\'validator loader config\')\nnames=(\'ownership_latch\',\'graph_observations\',\'pidfd_compat\',\'pidfd_custody\',\'deferred_fork\',\'runtime_binding\',\'adapter\',\'compositor\',\'validator_consumer\',\'validator_entry\')\nif set(config[\'modules\'])!=set(names):raise ValueError(\'validator module set\')\nlocal=os.path.dirname(config[\'modules\'][\'adapter\'][\'path\'])\nbase=os.path.join(local,\'parser\')\nif local!=os.path.dirname(config[\'modules\'][\'compositor\'][\'path\']):raise ValueError(\'validator source directory\')\nexpected={os.path.join(local,\'custody_protocol_v2.py\'):\'587cebf7b8359a1711f078882a012a701e290902dc4376d1bc6e4c03f7ce8cbb\',\n os.path.join(base,\'candidate_data.py\'):\'74eec517909d92d178d77771dd8ae59e826df50cd17121957a03e320b93d1c96\',\n os.path.join(base,\'contract.json\'):\'d4b38335f7d1af1998b9999a676ae5eee40b2b640021a144d19169328d68e0fd\',\n os.path.join(base,\'repaircontract.json\'):\'d4b38335f7d1af1998b9999a676ae5eee40b2b640021a144d19169328d68e0fd\',\n os.path.join(local,\'GRAPH-CONTRACT.json\'):\'d4b38335f7d1af1998b9999a676ae5eee40b2b640021a144d19169328d68e0fd\'}\nprofile=os.path.join(local,\'PROFILE.V2.SOURCE-ONLY.json\')\nif set(config[\'extra_files\'])!=set(expected)|{profile}:raise ValueError(\'validator source closure\')\nif any(config[\'extra_files\'][path]!=sha for path,sha in expected.items()):raise ValueError(\'validator source closure hash\')\nfor path,sha in config[\'extra_files\'].items():\n fd,_=m.pinned_validator_file(path,sha);hold.append(fd)\nfor name in names:\n spec=config[\'modules\'][name]\n if set(spec)!={\'path\',\'sha256\'}:raise ValueError(\'validator module pin\')\n fd,mod=m.load_verified_validator_module(name,spec[\'path\'],spec[\'sha256\']);hold.append(fd)\nif config[\'modules\'][\'validator_entry\'][\'path\']!=sys.argv[4]:raise ValueError(\'validator entry path\')\nif set(config[\'runtime\'])!={\'path\',\'sha256\'}:raise ValueError(\'validator runtime binding\')\nsys.modules[\'runtime_binding\'].verify_current(config[\'runtime\'][\'path\'],config[\'runtime\'][\'sha256\'])\nresult,operation=sys.modules[\'validator_entry\'].run()\n# Emit one bounded diagnostic DATA record on already captured stdout. Preserve\n# operation/session on a partial or failed write; no authority follows.\ntry:\n sys.modules[\'validator_entry\'].emit_stdout(result,operation,sys.stdout.buffer,os.environ[\'MCKERNEL_PIDFD_CUSTODY_NONCE\'])\nexcept BaseException:\n import signal\n while True:signal.pause()\n"""\n\n\ndef validator_argv(executable,verified_bootstrap_bytes,loader_manifest,loader_sha,entry_path):\n    if type(verified_bootstrap_bytes) is not bytes or not verified_bootstrap_bytes:\n        raise ValueError(\'verified bootstrap bytes required\')\n    return [executable,\'-I\',\'-B\',\'-c\',VALIDATOR_INLINE,\n            base64.b64encode(verified_bootstrap_bytes).decode(\'ascii\'),loader_manifest,loader_sha,entry_path]\n\n\nOWNER_INLINE = r"""import base64,os,sys,types\nm=types.ModuleType(\'root_bootstrap\');m.__file__=\'<verified-bootstrap-bytes>\';sys.modules[\'root_bootstrap\']=m\nexec(compile(base64.b64decode(sys.argv[1],validate=True),m.__file__,\'exec\'),m.__dict__)\nfd,entry=m.load_verified_module(\'root_owner_entry\',sys.argv[2],sys.argv[3])\nentry.run(sys.argv[4],sys.argv[5],int(os.environ[\'MCKERNEL_UNION_CUSTODY_FD\']))\n"""\n\n\ndef owner_argv(executable,verified_bootstrap_bytes,entry_path,entry_sha,config_path,config_sha):\n    if type(verified_bootstrap_bytes) is not bytes or not verified_bootstrap_bytes:\n        raise ValueError(\'verified bootstrap bytes required\')\n    return [executable,\'-I\',\'-B\',\'-c\',OWNER_INLINE,base64.b64encode(verified_bootstrap_bytes).decode(\'ascii\'),\n            entry_path,entry_sha,config_path,config_sha]\n\n\ndef fork_validator(executable,argv,uid,gid,environment,record,guard,journal_fd,nonce):\n    """Root creates socketpair then forks; child cannot retain root custody FDs.\n\n    Caller must have source-bound and admitted the executable, argv, uid/gid,\n    resource limits, identities and operation. The caller retains the socket,\n    process ownership and all operation leases. No call occurs at import.\n    """\n    if os.geteuid()!=0 or type(uid) is not int or uid<=0 or type(gid) is not int or gid<=0:\n        raise ValueError(\'root parent and ordinary child required\')\n    if type(argv) is not list or not argv or argv[0]!=executable or not all(type(x) is str for x in argv):\n        raise ValueError(\'exact validator argv required\')\n    if type(environment) is not dict or any(type(k) is not str or type(v) is not str for k,v in environment.items()):\n        raise ValueError(\'exact validator environment required\')\n    from ownership_latch import ChildRecord\n    from deferred_fork import DeferredFork\n    if type(record) is not ChildRecord or type(guard) is not DeferredFork or not guard.entered:\n        raise ValueError(\'guarded pre-registered child custody required\')\n    if type(nonce) is not str or len(nonce)!=64 or any(x not in \'0123456789abcdef\' for x in nonce):raise ValueError(\'operation nonce required\')\n    if type(journal_fd) is not int or journal_fd<3:raise ValueError(\'owned custody journal required\')\n    journal=os.fstat(journal_fd);mode=fcntl.fcntl(journal_fd,fcntl.F_GETFL)\n    if (not stat.S_ISREG(journal.st_mode) or journal.st_uid!=0 or stat.S_IMODE(journal.st_mode)!=0o600 or\n        journal.st_nlink!=1 or not mode&os.O_APPEND or mode&os.O_ACCMODE==os.O_RDONLY):\n        raise ValueError(\'root-created append-only custody journal required\')\n    parent,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)\n    record.add(parent,child,journal_fd)\n    try:\n        def child_exec():\n            parent.close()\n            channel=child.fileno()\n            if channel==journal_fd:raise ValueError(\'journal and channel alias\')\n            for fd in (channel,journal_fd):os.set_inheritable(fd,True)\n            upper=resource.getrlimit(resource.RLIMIT_NOFILE)[0]\n            if upper==resource.RLIM_INFINITY or upper>1048576:upper=1048576\n            keep=sorted((channel,journal_fd))\n            os.closerange(3,keep[0]);os.closerange(keep[0]+1,keep[1]);os.closerange(keep[1]+1,int(upper))\n            os.setgroups([]);os.setresgid(gid,gid,gid);os.setresuid(uid,uid,uid)\n            env=dict(environment);env[\'MCKERNEL_CUSTODY_FD\']=str(channel)\n            env[\'MCKERNEL_PIDFD_CUSTODY_JOURNAL_FD\']=str(journal_fd)\n            env[\'MCKERNEL_PIDFD_CUSTODY_NONCE\']=nonce\n            os.execve(executable,argv,env)\n        pid,pidfd,birth=guard.fork_and_pin(record,child_exec)\n        child.close()\n        return parent,pid,pidfd,(\'BOUND\',None)\n    except BaseException as error:\n        record.unknown(error);raise\n\n\ndef fork_union_owner(executable,argv,environment,record,guard):\n    """Fork a separately source-bound root union owner on a root-created channel.\n\n    This does not itself authenticate an executable or grant a workload release;\n    the caller must first verify the root-owned immutable executable and exact\n    loaded source bytes, one-shot admission and resource ownership.\n    """\n    if os.geteuid()!=0 or type(argv) is not list or not argv or argv[0]!=executable:\n        raise ValueError(\'root parent and exact owner argv required\')\n    if type(environment) is not dict or any(type(k) is not str or type(v) is not str for k,v in environment.items()):\n        raise ValueError(\'exact owner environment required\')\n    from ownership_latch import ChildRecord\n    from deferred_fork import DeferredFork\n    if type(record) is not ChildRecord or type(guard) is not DeferredFork or not guard.entered:\n        raise ValueError(\'guarded pre-registered child custody required\')\n    parent,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)\n    record.add(parent,child)\n    try:\n        def child_exec():\n            parent.close();channel=child.fileno();os.set_inheritable(channel,True)\n            upper=resource.getrlimit(resource.RLIMIT_NOFILE)[0]\n            if upper==resource.RLIM_INFINITY or upper>1048576:upper=1048576\n            os.closerange(3,channel);os.closerange(channel+1,int(upper))\n            env=dict(environment);env[\'MCKERNEL_UNION_CUSTODY_FD\']=str(channel)\n            os.execve(executable,argv,env)\n        pid,pidfd,birth=guard.fork_and_pin(record,child_exec)\n        child.close()\n        return parent,pid,pidfd,(\'BOUND\',None)\n    except BaseException as error:\n        record.unknown(error);raise\n\n\nif __name__==\'__main__\':\n    raise RuntimeError(\'SOURCE ONLY: no reviewed root bootstrap, owner custody or execution admission\')\n\n\ndef launch_named_native_from_registered_loader(bootstrap_path,bootstrap_sha,loader_path,loader_sha,root_fd,environment,grace_seconds):\n    """Normal Root watchdog frontdoor for the one newly reviewed native domain.\n\n    This function grants nothing at import and is never called by the model or\n    ordinary validator. Root must separately review/admit the actual immutable\n    package, current request/caps/resources/owners and exact operation command.\n    """\n    import json\n    fd,raw=pinned_root_file(loader_path,loader_sha)\n    hold=[fd]\n    config=json.loads(raw,object_pairs_hook=lambda pairs: _unique_loader_pairs(pairs))\n    if set(config)!={\'kind\',\'modules\',\'extra_files\',\'operation_config_path\',\'operation_config_sha\',\'runtime\'} or config[\'kind\']!=\'mckernel-native-signal-loader-v1\':\n        raise ValueError(\'only exact named native loader accepted\')\n    names=(\'ownership_latch\',\'custody_protocol_v2\',\'graph_observations\',\'pidfd_compat\',\'runtime_binding\',\n      \'pidfd_custody\',\'deferred_fork\',\'inplace_custody\',\'immutable_epoch\',\'adapter\',\'materializer\',\'source_freeze\',\n      \'split_inventory\',\'union_server_guarded\',\'graph_producer\',\'graph_server\',\'operation_supervisor\',\'supervisor_entry\',\n      \'native_current_owner\',\'native_diagnostic_container_owner\',\'native_resource_admission\',\'native_source_binding\',\n      \'compositor\',\'operation_watchdog\')\n    if set(config[\'modules\'])!=set(names):raise ValueError(\'complete original18 plus named source modules required\')\n    local=os.path.dirname(config[\'modules\'][\'materializer\'][\'path\'])\n    expected={os.path.join(local,n) for n in (\'verify_scripts_fd.py\',\'verified_owner_loader.py\',\'union_owner.py\',\'root_owner_entry.py\')}\n    if set(config[\'extra_files\'])!=expected:raise ValueError(\'registered parent/checker source closure\')\n    for path,sha in config[\'extra_files\'].items():\n        extra,_=pinned_root_file(path,sha);hold.append(extra)\n    for name in names:\n        spec=config[\'modules\'][name]\n        if type(spec) is not dict or set(spec)!={\'path\',\'sha256\'}:raise ValueError(\'module pin shape\')\n        mf,module=load_verified_module(name,spec[\'path\'],spec[\'sha256\']);hold.append(mf)\n    native=sys.modules[\'native_resource_admission\']\n    request=native.VerifiedNativeRequest.__new__(native.VerifiedNativeRequest)\n    # Retain before initialization or possible compatibility/pinning failure.\n    _NATIVE_FRONTDOOR_HELD.append((hold,request))\n    request.__init__(config[\'operation_config_path\'],config[\'operation_config_sha\'])\n    runtime=config[\'runtime\']\n    if runtime!=request.cfg[\'runtime\']:raise ValueError(\'Root runtime/request disagreement\')\n    bootstrap_fd,bootstrap_raw=pinned_root_file(bootstrap_path,bootstrap_sha)\n    hold.append(bootstrap_fd)\n    entry=config[\'modules\'][\'supervisor_entry\'][\'path\']\n    watchdog=sys.modules[\'operation_watchdog\'].launch_reviewed(root_fd,request.cfg[\'nonce\'],\n      runtime[\'path\'],runtime[\'sha256\'],bootstrap_path,bootstrap_sha,\n      loader_path,loader_sha,entry,environment,request.cfg[\'caps\'][\'boot\'],grace_seconds,\n      runtime[\'path\'],runtime[\'sha256\'],native_request=request)\n    watchdog.source_loader_holds=list(hold)\n    _NATIVE_FRONTDOOR_HELD.append(watchdog)\n    return watchdog\n\n\ndef _unique_loader_pairs(pairs):\n    value={}\n    for key,item in pairs:\n        if key in value:raise ValueError(\'duplicate named loader key\')\n        value[key]=item\n    return value\n\n\n_NATIVE_FRONTDOOR_HELD=[]\n'
BOOTSTRAP_PATH='/var/lib/mckernel-code-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/installed-source-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/root_bootstrap.py'
BOOTSTRAP_SHA='7753d3ee7b05419fa3211afc910e65aec9c0086ae9dc1f2d5ff82ac1fb977328'
MODULES={'ownership_latch': {'path': '/var/lib/mckernel-code-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/installed-source-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/ownership_latch.py', 'sha256': 'fb264b1e6f12852e6a11c44239089a015a02e25019f9094af586422398bfa390'}, 'graph_observations': {'path': '/var/lib/mckernel-code-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/installed-source-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/graph_observations.py', 'sha256': 'df7bb673c206585318a4e41a58486c05548d9981b81074baeb29437f458114ed'}, 'inplace_custody': {'path': '/var/lib/mckernel-code-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/installed-source-468d984b7f1655e9fe3c960589850621396cfe945ad5c27a030876fcefeef4fd/inplace_custody.py', 'sha256': '70307b730512cb56c3f63738fe9fc8c14a1603bb6ec4227e05db3ab36115890e'}}
RUNTIME={'path': '/usr/bin/python3.8', 'device': 66306, 'inode': 1048651, 'uid': 0, 'gid': 0, 'mode': 493, 'nlink': 1, 'bytes': 5490456, 'sha256': '298a9e830ed52f36c299427565485d717d1ce0179c0597cc16560513eb780b06', 'original_flags': 524288}
DRIVER_SHA='0ca054d1b097b16d699dd2ac9be843e6a2a6901ad0aab5c44bb1eb19168dd511'
DRIVER_PATH='/home/holden/mckernel-work/m14-blocker-resolution-20261110/new-native-runtime-binding-publicabi-max-1/native-diagnostic-correction-1/normal_native_once.PROPOSED.py'
CORE_SHA='e9243a348b3d3da681982f17703bd7e1325f4f7097a9c9d69b20b5eaff999838'
OWNED=[]; SECONDARY=[]; ROOT_FD=None; MUTATION_ATTEMPTED=False; STATE='UNSTARTED'; JOURNAL=None; RUNTIME_FD=None

# Raw diagnostic custody is separate from native authority and FD custody.
# Retain exception instances and actual traceback objects before any formatting.
RAW_FAILURES = []
RAW_SEEN = set()
SECONDARY_CAPTURED = 0
DIAGNOSTIC_SEQUENCE = 0


def capture_raw_exception(label, error, traceback_object=None):
    if traceback_object is None:
        traceback_object = BaseException.__dict__['__traceback__'].__get__(error, type(error))
    key = (label, id(error), id(traceback_object))
    if key not in RAW_SEEN:
        RAW_SEEN.add(key)
        RAW_FAILURES.append({'label': label, 'error': error, 'traceback': traceback_object})
    # Explicit exception chains are evidence too. Read builtin descriptors, not
    # a user-defined attribute/formatting hook; cycles remain raw and bounded.
    chain_seen = {id(error)}
    current = error
    for index in range(16):
        cause = BaseException.__dict__['__cause__'].__get__(current, type(current))
        context = BaseException.__dict__['__context__'].__get__(current, type(current))
        child = cause if cause is not None else context
        if child is None or id(child) in chain_seen:
            break
        chain_seen.add(id(child))
        tb = BaseException.__dict__['__traceback__'].__get__(child, type(child))
        chain_label = label + ':chain:' + str(index)
        chain_key = (chain_label, id(child), id(tb))
        if chain_key not in RAW_SEEN:
            RAW_SEEN.add(chain_key)
            RAW_FAILURES.append({'label': chain_label, 'error': child, 'traceback': tb})
        current = child


def capture_secondary_exceptions():
    global SECONDARY_CAPTURED
    while SECONDARY_CAPTURED < len(SECONDARY):
        index = SECONDARY_CAPTURED
        label, error = SECONDARY[index]
        SECONDARY_CAPTURED += 1
        capture_raw_exception('secondary:' + str(index) + ':' + label, error)


def diagnostic_secondary(label, error):
    # The original exception/TB is retained before any attempt to describe it.
    capture_raw_exception(label, error)
    SECONDARY.append((label, error))


def diagnostic_type(value):
    cls = type(value)
    return type.__getattribute__(cls, '__module__') + '.' + type.__getattribute__(cls, '__name__')


def diagnostic_value(value, depth=0):
    cls = type(value)
    if value is None or cls in (bool, int):
        return value
    if cls is float:
        return value if math.isfinite(value) else {'nonfinite_float': True}
    if cls is str:
        return {'text': value[:32768], 'truncated': len(value) > 32768,
                'sha256': hashlib.sha256(value.encode('utf-8', 'backslashreplace')).hexdigest()}
    if cls is bytes:
        return {'bytes_hex': value[:16384].hex(), 'truncated': len(value) > 16384,
                'sha256': hashlib.sha256(value).hexdigest()}
    if depth < 4 and cls in (tuple, list):
        return {'items': [diagnostic_value(item, depth + 1) for item in value[:64]],
                'truncated': len(value) > 64}
    return {'opaque_type': diagnostic_type(value), 'raw_object_retained': True}


def render_raw_failure(record):
    error = record['error']
    raw_args = BaseException.__dict__['args'].__get__(error, type(error))
    value = {'label': record['label'], 'type': diagnostic_type(error),
             'raw_args': diagnostic_value(raw_args), 'errno': None,
             'traceback_frames': [], 'traceback_truncated': False,
             'raw_exception_and_traceback_retained': True}
    if isinstance(error, OSError):
        value['errno'] = diagnostic_value(OSError.__dict__['errno'].__get__(error, type(error)))
    tb = record['traceback']
    while tb is not None and len(value['traceback_frames']) < 128:
        code = tb.tb_frame.f_code
        value['traceback_frames'].append({'file': code.co_filename,
                                           'line': tb.tb_lineno, 'function': code.co_name})
        tb = tb.tb_next
    value['traceback_truncated'] = tb is not None
    # A formatter/report failure must not recursively invoke the same failing
    # hook. Its exact primitive BaseException args and real TB remain evidence.
    if 'diagnostic-' in record['label']:
        value['message'] = json.dumps(value['raw_args'], sort_keys=True)
        value['message_encoding'] = 'exact_bounded_primitive_baseexception_args'
    else:
        try:
            message = str(error)
        except BaseException as formatting_error:
            diagnostic_secondary('diagnostic-message-format:' + record['label'], formatting_error)
            value['message'] = json.dumps(value['raw_args'], sort_keys=True)
            value['message_encoding'] = 'formatter_failed_exact_bounded_args_and_raw_object_retained'
        else:
            value['message'] = message[:65536]
            value['message_truncated'] = len(message) > 65536
            value['message_sha256'] = hashlib.sha256(message.encode('utf-8', 'backslashreplace')).hexdigest()
            value['message_encoding'] = 'actual_exception_str'
    return value


def diagnostic_payload(phase):
    capture_secondary_exceptions()
    records = []
    index = 0
    # Rendering can add a formatting failure; include that real exception too.
    while index < len(RAW_FAILURES):
        records.append(render_raw_failure(RAW_FAILURES[index]))
        index += 1
        capture_secondary_exceptions()
    return {'schema': 'native-root-caller-failure-diagnostics-v1', 'phase': phase,
            'pid': os.getpid(), 'exceptions': records,
            'native_authority_or_release': False, 'raw_objects_retained': True}


def diagnostic_write(fd, raw):
    offset = 0
    while offset < len(raw):
        wrote = os.write(fd, raw[offset:])
        need(wrote > 0, 'short caller diagnostic capture write')
        offset += wrote


def persist_private_diagnostic(phase, payload):
    global DIAGNOSTIC_SEQUENCE
    root_live = any(record['label'] == 'new-current-operation-root' and
                    record['state'] == 'HELD' for record in OWNED)
    if not root_live:
        return False
    DIAGNOSTIC_SEQUENCE += 1
    name = 'CALLER-DIAGNOSTIC-' + str(DIAGNOSTIC_SEQUENCE) + '.json'
    record = None
    stored = False
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW |
                     os.O_CLOEXEC, 0o600, dir_fd=ROOT_FD)
        record = own(fd, 'caller-diagnostic:' + name)
        diagnostic_write(fd, canonical(payload) + b'\n')
        os.fsync(fd); os.fsync(ROOT_FD)
        stored = True
    except BaseException as report_error:
        diagnostic_secondary('diagnostic-private-report:' + phase, report_error)
    finally:
        if record is not None and record['state'] == 'HELD':
            try:
                close_once(record)
            except BaseException:
                # close_once already retained the raw object before raising;
                # never retry its ambiguous numeric descriptor.
                stored = False
    return stored


def emit_failure_diagnostics(phase, primary=None):
    """Finite emitter used before UNKNOWN hold and after all normal drain.

    True means a complete current snapshot reached an fsynced private record or
    an existing captured Root stream. It grants no resource or native outcome.
    If every channel fails, return False with all actual errors/TBs still raw.
    """
    if primary is not None:
        capture_raw_exception('primary', primary)
    capture_secondary_exceptions()
    payload = diagnostic_payload(phase)
    persist_private_diagnostic(phase, payload)
    # Regenerate after private write/close failures, so stream fallback includes
    # those errors, not just the earlier exception snapshot.
    for fd, label in ((2, 'stderr'), (1, 'stdout')):
        payload = diagnostic_payload(phase)
        try:
            diagnostic_write(fd, canonical(payload) + b'\n')
        except BaseException as report_error:
            diagnostic_secondary('diagnostic-' + label + '-report:' + phase, report_error)
        else:
            return True
    # Both captured streams failed. One final fsynced current-private record can
    # preserve all channel failures. Any new failure stays raw; do not recurse.
    payload = diagnostic_payload(phase)
    before = len(SECONDARY)
    stored = persist_private_diagnostic(phase, payload)
    capture_secondary_exceptions()
    return stored and len(SECONDARY) == before


def retain_diagnostic_custody():
    while True:
        try:
            signal.pause()
        except BaseException as interruption:
            diagnostic_secondary('diagnostic-custody-interruption', interruption)
            emit_failure_diagnostics('CUSTODY_INTERRUPTION')

def need(ok,message):
    if not ok:raise ValueError(message)

def own(fd,label):
    row={'fd':fd,'historical_fd':fd,'label':label,'state':'HELD'};OWNED.append(row);return row

def close_once(row):
    if row['state']!='HELD':return
    fd=row.pop('fd');row['state']='CLOSE_ATTEMPTED_UNKNOWN'
    try:os.close(fd)
    except BaseException as error:
        diagnostic_secondary('provider-close:'+row['label'],error);raise
    row['state']='CLOSED'

def close_all(runtime_last=None):
    errors=[]
    for row in list(reversed(OWNED)):
        if row is runtime_last:continue
        try:close_once(row)
        except BaseException:errors.append(sys.exc_info())
    if runtime_last is not None:
        try:close_once(runtime_last)
        except BaseException:errors.append(sys.exc_info())
    return errors

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

def hash_fd(fd):
    os.lseek(fd,0,os.SEEK_SET);h=hashlib.sha256()
    while True:
        raw=os.read(fd,1024*1024)
        if not raw:break
        h.update(raw)
    os.lseek(fd,0,os.SEEK_SET);return h.hexdigest()

def stable_runtime(fd,source):
    st=os.fstat(fd)
    need(stat.S_ISREG(st.st_mode) and (st.st_dev,st.st_ino,st.st_uid,st.st_gid,
         stat.S_IMODE(st.st_mode),st.st_nlink,st.st_size)==
         (RUNTIME['device'],RUNTIME['inode'],0,0,0o755,1,RUNTIME['bytes']), 'same canonical runtime inode/type/owner/mode/size')
    need(hash_fd(fd)==RUNTIME['sha256'],'same runtime bytes required')
    named=own(source.open_exact(RUNTIME['path']),'runtime-path-recheck')
    other=os.fstat(named['fd'])
    need((other.st_dev,other.st_ino,other.st_size)==(st.st_dev,st.st_ino,st.st_size),'runtime pathname changed')
    close_once(named)
    return st

def verify_runtime_lock(fd):
    st=os.fstat(fd);matches=0
    with open('/proc/locks',encoding='ascii') as stream:
        for line in stream:
            fields=line.split()
            if len(fields)<8 or fields[1:4]!=['FLOCK','ADVISORY','WRITE']:continue
            major,minor,inode=fields[5].split(':')
            if (int(fields[4]),int(major,16),int(minor,16),int(inode))==(
                os.getpid(),os.major(st.st_dev),os.minor(st.st_dev),st.st_ino):matches+=1
    need(matches==1,'actual same-process exclusive runtime FLOCK lost')

def record(source,value):
    source.write_all(JOURNAL['fd'],canonical(value)+b'\n');os.fsync(JOURNAL['fd'])

def verify_first_prior_row(source):
    fd=JOURNAL['fd'];before=os.fstat(fd)
    need(stat.S_ISREG(before.st_mode) and before.st_uid==0 and
         stat.S_IMODE(before.st_mode)==0o600 and before.st_nlink==1 and
         0<before.st_size<=4096,'actual prior-flags journal identity/type/bound')
    raw=os.pread(fd,before.st_size+1,0);after=os.fstat(fd)
    need(len(raw)==before.st_size and
         (before.st_dev,before.st_ino,before.st_size,before.st_mode,before.st_mtime_ns,before.st_ctime_ns)==
         (after.st_dev,after.st_ino,after.st_size,after.st_mode,after.st_mtime_ns,after.st_ctime_ns),
         'actual prior-flags journal changed during read')
    rows=[json.loads(line,object_pairs_hook=source.unique) for line in raw.splitlines()]
    expected={'path':RUNTIME['path'],'device':RUNTIME['device'],
              'inode':RUNTIME['inode'],'old_flags':RUNTIME['original_flags']}
    need(len(rows)==1 and rows[0]==expected,'actual first prior-flags row differs; I ownership unproved')
    return rows[0]

def retain_unknown(primary):
    global STATE
    STATE='UNKNOWN_RETAINED'
    capture_raw_exception('runtime-provider-primary',primary[1],primary[2])
    # Reuse the qualified finite whole-function emitter. It preserves raw
    # original type/message/TB and secondaries before guarded private/stream
    # reporting. Every-channel failure still retains actual foreground custody.
    emit_failure_diagnostics('RUNTIME_PROVIDER_UNKNOWN_RETAINED',primary[1])
    retain_diagnostic_custody()


def main():
    global STATE,JOURNAL,RUNTIME_FD,MUTATION_ATTEMPTED,ROOT_FD
    need(os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={6},'actual admitted Root/CPU6 only')
    need(sys.executable==RUNTIME['path'],'no interpreter/path substitution')
    need(resource.getrlimit(resource.RLIMIT_AS)==(536870912,536870912) and
         resource.getrlimit(resource.RLIMIT_FSIZE)==(67108864,67108864) and
         resource.getrlimit(resource.RLIMIT_NOFILE)==(512,512) and resource.getrlimit(resource.RLIMIT_CORE)==(0,0),'unchanged reviewed native Root resource profile')
    need(len(sys.argv)==5 and sys.argv[0]=='-c','literal driver bytes/SHA and actualRoot input path/SHA required')
    driver_literal,driver_sha,input_path,input_sha=sys.argv[1:]
    need(hashlib.sha256(driver_literal.encode()).hexdigest()==driver_sha==DRIVER_SHA,'exact reviewed native driver bytes')
    need(hashlib.sha256(BOOTSTRAP_BYTES).hexdigest()==BOOTSTRAP_SHA,'exact bootstrap bytes')
    bootstrap=types.ModuleType('root_bootstrap');bootstrap.__file__=BOOTSTRAP_PATH;sys.modules['root_bootstrap']=bootstrap
    exec(compile(BOOTSTRAP_BYTES,BOOTSTRAP_PATH,'exec'),bootstrap.__dict__)
    fd,body=bootstrap.pinned_root_file(BOOTSTRAP_PATH,BOOTSTRAP_SHA);own(fd,'registered-bootstrap');need(body==BOOTSTRAP_BYTES,'physical bootstrap differs')
    modules={}
    for name in ('ownership_latch','graph_observations','inplace_custody'):
        spec=MODULES[name];fd,module=bootstrap.load_verified_module(name,spec['path'],spec['sha256']);own(fd,'provider:'+name);modules[name]=module
    source=modules['inplace_custody'];obs=modules['graph_observations']
    input_fd,raw=bootstrap.pinned_root_file(input_path,input_sha);own(input_fd,'actualRoot-native-input')
    inputs=json.loads(raw,object_pairs_hook=source.unique)
    need(type(inputs) is dict and set(inputs)=={'kind','source_contract_sha256','caps','host_admission_ref'} and
         inputs['kind']=='mckernel-native-signal-root-input-v1' and inputs['source_contract_sha256']==CORE_SHA,'unchanged actualRoot input')
    native=types.ModuleType('reviewed_named_native_driver');native.__file__=DRIVER_PATH
    exec(compile(driver_literal,DRIVER_PATH,'exec'),native.__dict__)
    native.check_caps(inputs['caps'],native.CORE['minimum_start_allowance_seconds'])
    admission=inputs['host_admission_ref'];need(type(admission) is dict and set(admission)=={'path','sha256'},'actual external Root admission ref')
    fd,_=bootstrap.pinned_root_file(admission['path'],admission['sha256']);own(fd,'actualRoot-measured-admission')
    # Actual Root has separately reviewed/admitted this SAME-inode preparation
    # plus named operation; these immutable DATA bytes create no permission.
    parent=os.path.dirname(input_path);root=own(source.open_exact(parent),'new-current-operation-root');source.root_private(root['fd']);ROOT_FD=root['fd']
    status=pathlib.Path('/proc/self/status').read_text();effective=int(next(x.split()[1] for x in status.splitlines() if x.startswith('CapEff:')),16)
    need(effective&(1<<9),'actual CAP_LINUX_IMMUTABLE required')
    runtime=own(source.open_exact(RUNTIME['path']),'same-runtime-flag-custody');RUNTIME_FD=runtime
    st=stable_runtime(runtime['fd'],source);exe=os.stat('/proc/self/exe')
    need((exe.st_dev,exe.st_ino)==(st.st_dev,st.st_ino),'actual executing runtime inode differs')
    fcntl.flock(runtime['fd'],fcntl.LOCK_EX|fcntl.LOCK_NB);verify_runtime_lock(runtime['fd'])
    need(source.flags(runtime['fd'])==RUNTIME['original_flags'],'fresh exact prior runtime flags required; no adoption/clear')
    birth=obs.process(os.getpid())[0];name='RUNTIME-FLAGS-'+str(os.getpid())+'-'+birth+'.jsonl'
    JOURNAL=own(os.open(name,os.O_RDWR|os.O_APPEND|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root['fd']),'durable-runtime-prior-flags')
    os.fsync(root['fd']);STATE='PREPARED'
    # The actual provider journals exact device/inode/old_flags and fsyncs
    # before its sole old|IMMUTABLE setter. No flag is removed on acquisition.
    MUTATION_ATTEMPTED=True
    source.walk(runtime['fd'],RUNTIME['path'],'freeze',JOURNAL['fd'])
    owned_prior=verify_first_prior_row(source)
    verify_runtime_lock(runtime['fd']);stable_runtime(runtime['fd'],source)
    need(source.flags(runtime['fd'])==(RUNTIME['original_flags']|source.IMMUTABLE),'exact original flags plus I required')
    STATE='HELD';record(source,{'status':'RUNTIME_HELD','pid':os.getpid(),'birth':birth,'runtime':RUNTIME,
       'native_driver_sha256':DRIVER_SHA,'actualRoot_input_sha256':input_sha,'native_permission_from_provider':False})
    saved_argv=sys.argv;sys.argv=['-c',input_path,input_sha]
    try:code=native.main()
    finally:sys.argv=saved_argv
    # The registered frontdoor reloads module objects. Use the CURRENT actual
    # class, never a preloaded alias or caller-authored completion dictionary.
    actual_module=sys.modules['native_resource_admission'];watchdog=native.WATCHDOG
    need(code in (0,2) and native.NATIVE_ATTEMPTED is True and watchdog is not None and
         watchdog.state=='RETIRED_CURRENT_NATIVE_OPERATION_ONLY' and
         type(watchdog.native_terminal) is actual_module.NativeParentRetirement and
         watchdog.native_terminal.watchdog is watchdog and
         watchdog.native_terminal.state=='CURRENT_NATIVE_AND_SOURCE_RESTORED' and
         not watchdog.close_errors and not native.SECONDARY and
         all(row['state']=='CLOSED' for row in native.OWNED),'genuine positive native/source/own closure required before runtime restore')
    need(not pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split(),'actual owned children remain')
    verify_runtime_lock(runtime['fd']);stable_runtime(runtime['fd'],source)
    need(source.flags(runtime['fd'])==(owned_prior['old_flags']|source.IMMUTABLE),'runtime restoration CAS failed')
    STATE='RESTORING';record(source,{'status':'RESTORE_BEGIN_AFTER_POSITIVE_NATIVE_CLEANUP','pid':os.getpid(),'birth':birth,
       'device':owned_prior['device'],'inode':owned_prior['inode'],'expected_flags':owned_prior['old_flags']|source.IMMUTABLE,'restore_flags':owned_prior['old_flags']})
    # Same exact-inode/prior-flags restoration used by NativeSourceCustody.restore.
    fcntl.ioctl(runtime['fd'],source.SETFLAGS,struct.pack('I',owned_prior['old_flags']))
    need(source.flags(runtime['fd'])==owned_prior['old_flags'],'exact runtime prior flags not restored')
    stable_runtime(runtime['fd'],source);STATE='RESTORED'
    record(source,{'status':'RESTORED_SAME_RUNTIME_ONLY','path':RUNTIME['path'],'device':owned_prior['device'],'inode':owned_prior['inode'],'original_flags':owned_prior['old_flags'],'native_pool_and_historical_outcomes':'UNCHANGED'})
    errors=close_all(runtime_last=runtime)
    if errors:
        for index,item in enumerate(errors):capture_raw_exception('provider-own-close:'+str(index),item[1],item[2])
        raise RuntimeError('runtime provider own closure uncertain')
    STATE='CLOSED_RESTORED'
    print(json.dumps({'status':STATE,'runtime':RUNTIME['path'],'original_flags':RUNTIME['original_flags'],
       'native_functional_exit':code,'native_pool_or_history_release':False},sort_keys=True),flush=True)
    return code

if __name__=='__main__':
    try:
        return_code=main()
    except BaseException:
        # Includes SystemExit/KeyboardInterrupt propagated from actual native
        # main or any provider stage; only the final normal exit is outside try.
        primary=sys.exc_info()
        capture_raw_exception('runtime-provider-primary',primary[1],primary[2])
        if MUTATION_ATTEMPTED:retain_unknown(primary)
        secondary=close_all()
        for index,item in enumerate(secondary):
            capture_raw_exception('provider-premutation-close:'+str(index),item[1],item[2])
        if secondary:retain_unknown(primary)
        if not emit_failure_diagnostics('RUNTIME_PROVIDER_PREMUTATION_FAILURE',primary[1]):
            retain_diagnostic_custody()
        raise BaseException.with_traceback(primary[1],primary[2])
    raise SystemExit(return_code)
