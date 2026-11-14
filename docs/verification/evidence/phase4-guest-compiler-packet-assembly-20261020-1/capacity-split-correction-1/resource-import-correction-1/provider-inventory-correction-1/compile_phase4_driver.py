"""Five genuine crate/C compiles; accepted WNOWAIT capture, no image build."""
import hashlib, json, os, resource, signal, struct, sys, time, types
from pathlib import Path
STREAM = 32 * 2 ** 20
WORK = 640 * 2 ** 20
SYMBOLS = {'process_fork_guest_' + s + '_current_v1' for s in ('carrier_create', 'carrier_begin', 'carrier_cancel', 'carrier_retain', 'control_submit')}
RUST_DEFINITIONS=SYMBOLS|{'process_fork_construct_current_v1','process_fork_cancel_constructed_current_v1',
    'process_fork_owned_caller_current_v1','process_fork_owned_caller_current_v2','release_process_checked',
    'release_thread_checked','release_process_vm_checked','release_cpuid'}
BRIDGES={'process_fork_construct_current_v1','process_fork_cancel_constructed_current_v1','process_fork_owned_caller_current_v2'}
PROVIDERS={'clone_thread'}
C_COMPILER_SHA256='2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2'
RULES={'native-mckernel_rust.o':(RUST_DEFINITIONS,PROVIDERS,set()),
       'legacy-mckernel_rust.o':(RUST_DEFINITIONS,PROVIDERS,set()),
       'selected-owned-syscall.o':({'do_fork'},BRIDGES,set()),
       'fallback-owned-syscall.o':({'do_fork'},set(),BRIDGES),
       'constructor-process.o':(PROVIDERS,set(),{'release_cpuid'})}

def metadata(st):
    return {key: getattr(st, key) for key in ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_blocks')}

def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())

def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda : stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()

def object_info(path):
    data=path.read_bytes()
    assert 64<=len(data)<=STREAM and data[:7]==b'\x7fELF\x02\x01\x01'
    header=struct.unpack_from('<16sHHIQQQIHHHHHH',data)
    assert header[1:4]==(1,62,1) and header[8]==64 and header[10]==0
    offset,entry,count,names=header[6],header[11],header[12],header[13]
    assert entry==64 and count>0 and names<count and offset+entry*count<=len(data)
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*entry)for i in range(count)]
    symbols={}
    for section in sections:
        if section[1]!=8:assert section[4]+section[5]<=len(data)
        if section[1]!=2:continue
        assert section[9]==24 and section[5]%24==0 and section[6]<count
        strings=sections[section[6]];assert strings[1]==3
        table=data[strings[4]:strings[4]+strings[5]]
        for pos in range(section[4],section[4]+section[5],24):
            name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',data,pos)
            assert name<len(table);end=table.find(b'\0',name);assert end>=name
            if info>>4 not in (1,2):continue
            symbol=table[name:end].decode('ascii',errors='strict')
            if symbol:symbols.setdefault(symbol,[]).append((index!=0,info&15))
    definitions,undefined,forbidden=RULES[path.name]
    witnesses={}
    for symbol in sorted(definitions|undefined|forbidden):
        rows=symbols.get(symbol,[])
        d=sum(defined and kind==2 for defined,kind in rows);u=sum(not defined for defined,kind in rows)
        if symbol in definitions:assert d==1 and u==0,(path.name,symbol,d,u)
        if symbol in undefined:assert d==0 and u==1,(path.name,symbol,d,u)
        if symbol in forbidden:assert not rows,(path.name,symbol,rows)
        witnesses[symbol]={'defined_functions':d,'undefined':u}
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
        'elf_class':64,'elf_data':'little','machine':62,'type':'ET_REL','section_count':count,
        'exact_boundary_symbols':witnesses,'symbol_presence_is_activation':False,'actual_relocatable_link_proof':False}

def main():
    assert sys.argv == ['/driver.py', '--execute']
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (STREAM, STREAM))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    helpers = types.ModuleType('_accepted_owned_capture')
    helpers.__file__ = '/owned-capture.py'
    exec(compile(Path(helpers.__file__).read_bytes(), helpers.__file__, 'exec'), helpers.__dict__)
    for number in helpers.STOP_SIGNALS:
        signal.signal(number, helpers.stop)
    manifest = json.loads(Path('/inputs.json').read_bytes())
    for row in manifest['rows']:
        path = Path('/src') / row['relative']
        assert path.is_file() and (not path.is_symlink()) and (path.stat().st_size == row['bytes']) and (sha(path) == row['sha256'])
    commands = json.loads(Path('/commands.json').read_bytes())
    assert [row['selection'] for row in commands] == ['native','legacy','caller-selected','caller-fallback','constructor-provider']
    assert all((row['cwd'] == '/work/output/build/kernel' for row in commands))
    assert sha(Path('/usr/bin/cc'))==C_COMPILER_SHA256
    Path('/work/output/build/kernel').mkdir(parents=True, exist_ok=False)
    config=Path('/src/.compiler-generated/config.h').read_bytes()
    Path('/work/output/build/config.h').write_bytes(config)
    out = Path('/work/output/build/current-guest-control-fullcrate-1')
    out.mkdir(parents=True, exist_ok=False)
    actual=Path('/src/kernel/syscall.c').read_text()
    suffix=Path('/prototype-assertions.h').read_text()
    assert 'extern ' not in suffix and '__attribute__((alias' not in suffix
    (out/'actual-owned-syscall.c').write_text('#line 1 \"/src/kernel/syscall.c\"\n'+actual+'\n'+suffix)
    deadline = time.monotonic() + 1750
    capacity_error = []

    def current_capacity():
        allocated = count = 0
        for path in Path('/work').rglob('*'):
            try:
                if path.is_file():
                    allocated += path.stat().st_blocks * 512
                    count += 1
            except FileNotFoundError:
                pass
        if allocated > WORK or count > 4096:
            capacity_error.append('wholework640MiB/4096files cap')
            raise RuntimeError(capacity_error[-1])
    ancestor_wait_terminal = helpers.wait_terminal

    def wait_with_capacity(process, seconds):
        if helpers.stopping:
            return ancestor_wait_terminal(process, seconds)
        until = time.monotonic() + seconds
        while True:
            current_capacity()
            remaining = until - time.monotonic()
            if ancestor_wait_terminal(process, min(0.02, max(0, remaining))):
                return True
            if remaining <= 0:
                return False
    helpers.wait_terminal = wait_with_capacity
    statuses = []
    artifacts = []
    for command in commands:
        stage = out / command['selection']
        stage.mkdir()
        os.chdir(command['cwd'])
        save(stage / 'command.json', {'argv': command['argv'], 'cwd': os.getcwd()})
        child_row = {}

        def started(pid):
            stat = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
            child_row.update(pid=pid, starttime=int(stat[19]), process_group=int(stat[2]), argv=command['argv'], cwd=os.getcwd(), parent_pid=os.getpid())
            assert child_row['process_group'] == pid
            save(stage / 'child.json', child_row)
            return child_row['starttime']

        def limits():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (STREAM, STREAM))
            resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
        joined = helpers.owned_capture(command, stage, max(0.1, deadline - time.monotonic()), limits, started)
        save(stage/'wait-status.json',{key:joined[key] for key in ('returncode','direct_child_joined','group_absent')})
        streams = {}
        for (role, row) in joined['captures'].items():
            stable = {key: value for (key, value) in row.items() if key not in ('path', 'sha256')}
            streams[role] = {'path': row['path'], 'bytes': row['size'], 'sha256': row['sha256'], 'closed': joined['closed_streams'], 'stable_fd': stable, 'stable_fields': list(helpers.FIELDS), 'descriptive_stat': metadata(Path(row['path']).stat())}
        status = {'argv': command['argv'], 'cwd': command['cwd'], 'child': child_row, 'exit_code': joined['returncode'], 'direct_wait': joined['direct_child_joined'], 'owned_process_group_absent': joined['group_absent'], 'streams': streams, 'owned_capture': joined}
        save(stage / 'status.json', status)
        statuses.append(status)
        if capacity_error or joined['returncode'] != 0 or (not joined['direct_child_joined']) or (not joined['group_absent']) or joined['error'] or joined['retirement_error'] or joined['unexpected_group_members']:
            break
        artifacts.append(object_info(Path(command['output'])))
    passed = len(statuses) == len(artifacts) == 5 and (not capacity_error)
    save(out / 'result.json', {'status': 'CRATE_OBJECT_COMPILE_PASS' if passed else 'FAIL', 'commands': statuses, 'artifacts': artifacts, 'source_identity': manifest['source_identity'], 'capacity_errors': capacity_error, 'image_or_guest_acceptance': False,'actual_link_performed':False,'boundary_scope':'candidate cross-object symbol closure only; no linked artifact or activation proof'})
    return 0 if passed else 1
if __name__ == '__main__':
    sys.exit(main())
