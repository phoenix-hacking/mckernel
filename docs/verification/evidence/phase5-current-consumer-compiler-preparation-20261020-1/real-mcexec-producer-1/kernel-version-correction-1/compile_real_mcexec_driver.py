"""Actual six real mcexec producers, reused accepted owned capture; no runtime."""
import hashlib,json,os,resource,shlex,signal,stat,struct,sys,time,types
from pathlib import Path
STREAM=32*2**20
WORK=640*2**20
C_COMPILER_SHA256='2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2'
ARTIFACTS=['output/build/executer/user/CMakeFiles/mcexec.dir/mcexec.c.o','output/build/executer/user/rust/mcexec_helpers.o','output/build/executer/user/CMakeFiles/libmcexec.dir/arch/x86_64/archdep.S.o','output/build/executer/user/libmcexec.a','output/build/executer/user/mcexec']
IMAGE_DEPENDENCY_ROOTS=('/usr/include','/usr/lib64','/usr/lib/gcc','/usr/libexec/gcc','/nightly','/out/build')
ASM_SYMBOLS={'switch_ctx','compare_and_swap','compare_and_swap_int'}
RULES={'mcexec.c.o':({'mcexec_clone_fork_bridge'},{'act_clone_start'}),
       'mcexec_helpers.o':({'act_clone_start'},{'mcexec_clone_fork_bridge'}),
       'archdep.S.o':(set(),set()),
       'mcexec':({'act_clone_start','mcexec_clone_fork_bridge'},set())}
def metadata(st):
    return {key:getattr(st,key)for key in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns','st_blocks')}
def save(path,value):
    with path.open('x')as stream:
        json.dump(value,stream,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
def sha(path):
    value=hashlib.sha256()
    with path.open('rb')as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()
def under(path,root):
    return path==Path(root) or Path(root) in path.parents

def dependency_info(depfile,cwd,manifest,source_root='/src',build_root='/work/output/build',image_roots=IMAGE_DEPENDENCY_ROOTS):
    raw=depfile.read_bytes();assert 0<len(raw)<=STREAM
    text=raw.decode('utf-8');assert '$' not in text and '\x00' not in text
    logical=text.replace('\\\n',' ').splitlines();rules=[]
    for line in logical:
        if not line.strip():continue
        assert ':' in line,'dependency rule missing target separator'
        target,body=line.split(':',1);assert target.strip()
        rules.append((shlex.split(target),shlex.split(body)))
    assert rules and rules[0][1] and all(not body for target,body in rules[1:]),'one populated actual dependency rule plus optional phony rules'
    selected={str(Path(source_root)/row['relative']):row for row in manifest['rows']};descriptors=[];seen=set()
    for spelling in rules[0][1]:
        path=Path(spelling);path=(path if path.is_absolute()else cwd/path).resolve(strict=True)
        if path in seen:continue
        seen.add(path)
        assert path.is_file() and 0<=path.stat().st_size<=STREAM
        if under(path,source_root):
            assert str(path)in selected,'actual source dependency outside frozen21: '+str(path)
            pin=selected[str(path)];digest=sha(path);assert path.stat().st_size==pin['bytes'] and digest==pin['sha256'];authority='exact frozen known-input source'
        elif under(path,build_root):
            digest=sha(path);authority='fresh generated compiler/link output'
            if path.name=='config.h':
                pin=selected[str(Path(source_root)/'config.h')];assert path.stat().st_size==pin['bytes'] and digest==pin['sha256']
        else:
            assert any(under(path,root)for root in image_roots),'actual dependency outside approved immutable image/toolchain roots: '+str(path)
            digest=sha(path);authority='exact pinned readonly image or readonly accepted nightly root'
        descriptors.append({'path':str(path),'sha256':digest,'bytes':path.stat().st_size,'authority':authority})
    return {'path':str(depfile),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'target':rules[0][0],'actual_dependency_spellings':rules[0][1],'actual_dependencies':descriptors,'complete_actual_rule_captured':True,'historical_dependency_proof_claimed':False}

def object_info(path):
    data=path.read_bytes();assert 0<len(data)<=STREAM
    if path.name=='libmcexec.a':
        assert data.startswith(b'!<arch>\n');pos=8;members=[];indices=0
        while pos<len(data):
            header=data[pos:pos+60];assert len(header)==60 and header[58:60]==b'`\n';size=int(header[48:58].strip());name=header[:16].decode('ascii').strip();start=pos+60;end=start+size;assert end<=len(data)
            if name=='/':indices+=1
            else:
                assert name=='archdep.S.o/';members.append({'name':'archdep.S.o','sha256':hashlib.sha256(data[start:end]).hexdigest(),'bytes':size})
            pos=end+(size%2)
        assert pos==len(data) and indices==1 and len(members)==1
        expected=path.parent/'CMakeFiles/libmcexec.dir/arch/x86_64/archdep.S.o';assert members[0]['sha256']==sha(expected) and members[0]['bytes']==expected.stat().st_size
        return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'type':'actual ar archive','members':members,'source_or_stub_substitution':False}
    assert data[:7]==b'\x7fELF\x02\x01\x01'
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',data);expected_type=3 if path.name=='mcexec'else 1
    assert h[1:4]==(expected_type,62,1) and h[8]==64
    if expected_type==1:assert h[10]==0
    offset,entry,count,names=h[6],h[11],h[12],h[13];assert entry==64 and count>0 and names<count and offset+entry*count<=len(data)
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*entry)for i in range(count)];symbols={}
    for section in sections:
        if section[1]!=8:assert section[4]+section[5]<=len(data)
        if section[1]!=2:continue
        assert section[9]==24 and section[5]%24==0 and section[6]<count
        strings=sections[section[6]];assert strings[1]==3;table=data[strings[4]:strings[4]+strings[5]]
        for pos in range(section[4],section[4]+section[5],24):
            name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',data,pos);assert name<len(table);end=table.find(b'\0',name);assert end>=name
            if info>>4 not in (1,2):continue
            symbol=table[name:end].decode('ascii');
            if symbol:symbols.setdefault(symbol,[]).append((index!=0,info&15))
    definitions,undefined=RULES[path.name];witnesses={}
    for name in sorted(definitions|undefined):
        rows=symbols.get(name,[]);d=sum(defined and kind==2 for defined,kind in rows);u=sum(not defined for defined,kind in rows)
        if name in definitions:assert d==1 and u==0,(path.name,name,d,u)
        if name in undefined:assert d==0 and u==1,(path.name,name,d,u)
        witnesses[name]={'defined_functions':d,'undefined':u}
    if path.name=='archdep.S.o':
        for name in sorted(ASM_SYMBOLS):
            rows=symbols.get(name,[]);assert len(rows)==1 and rows[0][0] and rows[0][1]in(0,2),(path.name,name,rows)
            witnesses[name]={'defined_global_rows':1,'kind':rows[0][1],'undefined':0}
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'elf_class':64,'elf_data':'little','machine':62,'type':'ET_DYN'if expected_type==3 else 'ET_REL','section_count':count,'exact_boundary_symbols':witnesses,'symbol_presence_is_activation':False,'Linux_mcexec_link_artifact':expected_type==3,'McKernel_kernel_link_proof':False}

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
    assert manifest['count']==len(manifest['rows'])==21
    assert [row['selection'] for row in commands] == ['real-mcexec-C-and-dependencies','real-mcexec-Rust','real-mcexec-ASM','real-mcexec-archive-0','real-mcexec-archive-1','real-mcexec-link']
    assert all(row['cwd']=='/work/output/build/executer/user' for row in commands)
    assert sha(Path('/usr/bin/cc'))==C_COMPILER_SHA256
    cwd=Path('/work/output/build/executer/user');cwd.mkdir(parents=True,exist_ok=False)
    for relative in ('CMakeFiles/mcexec.dir','CMakeFiles/libmcexec.dir/arch/x86_64','rust'):(cwd/relative).mkdir(parents=True)
    Path('/work/output/build/config.h').write_bytes(Path('/src/config.h').read_bytes())
    out=Path('/work/output/build/real-mcexec-1');out.mkdir(parents=True,exist_ok=False)
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
    artifacts = [];dependencies={}
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
        if command['selection']=='real-mcexec-C-and-dependencies':
            dependencies['C']=dependency_info(Path(command['generated_dependency_file']),Path(command['cwd']),manifest)
            save(out/'actual-C-dependencies.json',dependencies['C'])
        if command['selection']=='real-mcexec-link':
            dependencies['link']=dependency_info(Path(command['generated_dependency_file']),Path(command['cwd']),manifest)
            save(out/'actual-link-dependencies.json',dependencies['link'])
    if len(statuses)==6 and all(row['exit_code']==0 and row['direct_wait'] and row['owned_process_group_absent'] for row in statuses) and not capacity_error:
        artifacts=[object_info(Path('/work')/relative) for relative in ARTIFACTS]
    passed = len(statuses)==6 and len(artifacts)==5 and set(dependencies)=={'C','link'} and (not capacity_error)
    save(out / 'result.json', {'status': 'MCEXEC_COMPILE_AND_LINK_PASS' if passed else 'FAIL', 'commands': statuses, 'artifacts': artifacts, 'source_identity': manifest['source_identity'], 'capacity_errors': capacity_error, 'image_or_guest_acceptance': False,'actual_link_performed':passed,'dependencies':dependencies,'boundary_scope':'actual current Linux mcexec compile/archive/link and generated dependencies only; no McKernel kernel link, installation, selector1 runtime or native/default acceptance'})
    return 0 if passed else 1
if __name__ == '__main__':
    sys.exit(main())
