# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Seven ordinary wrapper artifacts, fourteen serial compile/link calls and one passive ELF call only.
# The rejected worker01a1c48d / turn01a1ce01 signal/frame/xstate request is excluded.
import ast, errno, hashlib, importlib.util, json, os, pathlib, re, shlex, shutil
import stat, struct, sys, time, traceback

OUT = pathlib.Path('/output')
CAP = OUT/'capture'
PLAN = pathlib.Path('/input/COMMAND-PLAN.json')
OWNER = pathlib.Path('/input/owned_process.py')
attempts = []
owner = None
held_inputs = {}
primary_raw = None
primary_tb = None
OWNER_CALL_PENDING = None
OWNER_CALL_COMPLETED = []
OWNER_CUSTODY_ERRORS = []

def current_Owner_call_closed(context, result):
    # A missing current row is UNKNOWN, even when older rows are all closed.
    try:
        rows=context['owner'].records
        if len(rows)!=context['record_index']+1:return False
        row=rows[context['record_index']]
        return (row['label']==context['label'] and type(row['leader']) is int and row['leader']>0 and
            str(row['leader_birth']).isdigit() and int(row['leader_birth'])>0 and
            row['leader_parent_joined'] is True and row['whole_descendants_joined'] is True and
            row['streams_closed'] is True and type(row['status']) is int and
            row['status']==result.returncode and row['remaining_direct_children']==[] and
            row['error'] is None and row['timed_out'] is False and
            row['leader_group_signalled'] is False and row['adopted_reaps']==[] and row['adopted_kills']==[])
    except BaseException:
        return False

def retain_current_Owner_context_nonescaping():
    # Same original call context and raw TB stay reachable. No new call, signal,
    # kill, numeric wait, substituted handle, re-execution or persistence guard.
    while True:
        try:
            if OWNER_CALL_PENDING is None:return
            try:time.sleep(30)
            except BaseException as error:
                try:OWNER_CUSTODY_ERRORS.append((error,BaseException.__dict__['__traceback__'].__get__(error,type(error))))
                except BaseException:pass
        except BaseException:
            pass

def digest(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def identity(st):
    return [st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_uid, st.st_gid,
            st.st_size, st.st_mtime_ns, st.st_ctime_ns]

def save(path, value):
    path = pathlib.Path(path)
    temporary = path.with_name(path.name+'.pending')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(str(temporary),str(path))
    # Same qualified durable-capture body, scoped to this capture directory.
    for leaf in path.parent.iterdir():
        if leaf.is_file():
            fd=os.open(str(leaf),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
            try:os.fsync(fd)
            finally:os.close(fd)
    fd = os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(fd)
    finally:os.close(fd)

def observe_input(path, category, expected=None):
    p = pathlib.Path(path)
    real = p.resolve(strict=True)
    st = real.stat()
    assert stat.S_ISREG(st.st_mode) and 0 < st.st_size <= 64*2**20, str(p)
    record = dict(path=str(p),resolved=str(real),identity=identity(st),
                  bytes=st.st_size,sha256=digest(real),categories=[category])
    assert identity(real.stat())==record['identity'], 'input changed during hash'
    if expected is not None:
        for key in ('resolved','bytes','sha256'):
            if key in expected:assert record[key]==expected[key], (str(p),key)
    if str(p) in held_inputs:
        old = held_inputs[str(p)]
        assert all(old[k]==record[k] for k in ('resolved','identity','bytes','sha256')), 'selected input changed'
        if category not in old['categories']:old['categories'].append(category)
    else:held_inputs[str(p)]=record
    return record

def bookend_inputs():
    for path, old in list(held_inputs.items()):
        observe_input(path,'terminal-bookend',old)

def owned_command(item):
    global OWNER_CALL_PENDING
    attempt = dict(index=len(attempts),label=item['id'],argv=item['argv'],
                   creation_attempted=True,lifecycle_UNKNOWN=True)
    attempts.append(attempt)
    # This durable receipt precedes the qualified Owner's Popen.
    save(CAP/'ATTEMPTS.json',attempts)
    # Mark the possibly-created invocation BEFORE Owner.run. If Popen or any
    # stream/record persistence raises before append, this context remains held.
    context=dict(owner=owner,label=item['id'],argv=item['argv'],record_index=len(owner.records),
        original_raw_error=None,original_raw_tb=None,returned_result=None,positive_closed_record=None)
    OWNER_CALL_PENDING=context
    try:
        result=owner.run(item['argv'],env=plan['environment'],cwd='/output',
            timeout=item['wall_seconds'],label=item['id'])
    except BaseException as error:
        context['original_raw_error']=error
        context['original_raw_tb']=BaseException.__dict__['__traceback__'].__get__(error,type(error))
        raise
    context['returned_result']=result
    assert current_Owner_call_closed(context,result),'current original Owner closure UNKNOWN'
    context['positive_closed_record']=owner.records[context['record_index']]
    OWNER_CALL_COMPLETED.append(context)
    OWNER_CALL_PENDING=None
    row = owner.records[-1]
    assert int(row['leader'])>0 and int(row['leader_birth'])>0
    assert row['leader_parent_joined'] and row['whole_descendants_joined'] and row['streams_closed']
    assert not row['timed_out'] and not row['leader_group_signalled']
    assert not row['adopted_reaps'] and not row['adopted_kills'] and not row['remaining_direct_children']
    assert row['error'] is None and row['status']==result.returncode
    assert len(result.stdout)<=plan['command_stream_limit_bytes'] and len(result.stderr)<=plan['command_stream_limit_bytes']
    attempt.update(exit=result.returncode,ownership=row,lifecycle_UNKNOWN=False)
    save(CAP/'ATTEMPTS.json',attempts)
    assert result.returncode==0, (item['id'],result.returncode)
    if item['id']=='wrappers-passive-ELF':
        assert not result.stderr, 'passive ELF/disassembly diagnostic retained'
    return result

def dynsyms(text):
    rows=[]
    for line in text.splitlines():
        fields=line.split()
        if (len(fields)>=8 and re.fullmatch('[0-9]+:',fields[0]) and
                re.fullmatch('[0-9a-fA-F]+',fields[1]) and fields[2].isdigit() and
                fields[3] in ('NOTYPE','OBJECT','FUNC','SECTION','FILE','COMMON','TLS','IFUNC')):
            rows.append(dict(value=fields[1],bytes=int(fields[2]),type=fields[3],
                             binding=fields[4],visibility=fields[5],section=fields[6],name=fields[7]))
    return rows

def elf_header(text):
    assert re.search(r'Class:\s+ELF64\b',text) and re.search(r'Data:\s+2.s complement, little endian',text)
    assert re.search(r'Machine:\s+Advanced Micro Devices X86-64',text)

def qualify_wrappers_and_providers(text):
    parts=re.split(r'^File: (.+)\n',text,flags=re.M)
    assert not parts[0].strip() and len(parts)==2*len(plan['readelf_provider_inputs'])+1, 'exact nine readelf inputs required'
    sections={parts[i]:parts[i+1] for i in range(1,len(parts),2)}
    assert len(sections)==9 and set(sections)==set(plan['readelf_provider_inputs'])
    provider_defs={}
    for path in plan['readelf_provider_inputs'][-2:]:
        provider=sections[path];elf_header(provider)
        assert re.search(r'Type:\s+DYN\b',provider)
        for row in dynsyms(provider):
            if row['section']!='UND' and row['binding'] in ('GLOBAL','WEAK') and row['visibility'] in ('DEFAULT','PROTECTED'):
                normalized=row['name'].replace('@@','@')
                provider_defs.setdefault(normalized,[]).append(dict(provider=path,definition=row))
                if '@@' in row['name']:
                    provider_defs.setdefault(row['name'].split('@@',1)[0],[]).append(dict(provider=path,definition=row))
    qualification={}
    for case_id in plan['case_ids']:
        executable=sections['/output/'+case_id];elf_header(executable)
        assert re.search(r'Type:\s+EXEC\b',executable), 'ordinary wrapper executable must be ET_EXEC'
        assert re.findall(r'Requesting program interpreter: ([^\]]+)',executable)==['/lib64/ld-linux-x86-64.so.2']
        needed=re.findall(r'\(NEEDED\).*Shared library: \[([^\]]+)\]',executable)
        assert needed==['libc.so.6'], ('unexpected wrapper DT_NEEDED',case_id,needed)
        resolutions=[];weak=[]
        for row in dynsyms(executable):
            if row['section']!='UND' or not row['name']:continue
            if row['binding']=='WEAK':weak.append(row);continue
            assert row['binding']=='GLOBAL' and row['name'] in provider_defs, ('unresolved strong dynamic import',case_id,row)
            resolutions.append(dict(required=row,definitions=provider_defs[row['name']]))
        assert resolutions, 'no strong dynamic imports observed'
        qualification[case_id]=dict(interpreter='/lib64/ld-linux-x86-64.so.2',needed=needed,strong_import_resolutions=resolutions,legitimate_weak_undefined=weak,same_image_provider_bytes_required_and_bookended=True)
    return qualification

def selected_compiler_inputs():
    for name in plan['depfile_names']:
        raw=(OUT/name).read_text()
        logical=raw.replace('\\\n',' ')
        target,sep,rest=logical.partition(':')
        assert sep and target.strip().startswith('/output/'), 'bounded compiler depfile target'
        paths=shlex.split(rest)
        assert paths and all(pathlib.Path(x).is_absolute() for x in paths)
        for path in paths:observe_input(path,'actual-depfile:'+name)
    for name in plan['map_names']:
        text=(OUT/name).read_text()
        paths=re.findall(r'^LOAD (/.+)$',text,re.M)
        assert paths and any(pathlib.Path(x).name=='crti.o' for x in paths), 'actual startup LOAD inputs missing'
        assert any(pathlib.Path(x).name in ('crt1.o','Scrt1.o','rcrt1.o') for x in paths), 'actual entry startup object missing'
        for path in paths:
            if not path.startswith('/output/'):observe_input(path,'actual-link-map:'+name)
    observed_tools=set()
    for item in plan['commands'][:-1]:
        for line in (CAP/(item['id']+'.stderr')).read_text().splitlines():
            if not line.startswith(' '):continue
            try:tokens=shlex.split(line)
            except ValueError:continue
            if not tokens:continue
            head=tokens[0]
            if pathlib.Path(head).name in ('cc1','as','collect2','ld'):
                path=head if pathlib.Path(head).is_absolute() else shutil.which(head,path=plan['environment']['PATH'])
                assert path, 'verbose compiler tool unavailable'
                observe_input(path,'actual-compiler-verbose:'+item['id'])
                observed_tools.add(pathlib.Path(head).name)
            for token in tokens[1:]:
                if token.startswith('/') and pathlib.Path(token).is_file() and not token.startswith('/output/'):
                    observe_input(token,'actual-compiler-verbose-argument:'+item['id'])
    assert {'cc1','as','collect2'}<=observed_tools, ('missing actual compiler verbose tools',observed_tools)
    return sorted(observed_tools)

def main():
    global plan,owner,primary_raw,primary_tb
    assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1])
    assert digest(PLAN)==sys.argv[1] and not list(OUT.iterdir()), 'fresh output and exact plan required'
    plan=json.loads(PLAN.read_bytes())
    assert len(plan['commands'])==15 and len(plan['case_ids'])==7 and os.sched_getaffinity(0)=={7}
    assert os.getuid()==1000 and os.getgid()==1000 and pathlib.Path.cwd()==OUT
    os.umask(0o077);CAP.mkdir(mode=0o700)
    observe_input(PLAN,'command-plan')
    for item in plan['readonly_inputs']:observe_input(item['container_path'],'readonly-bind',item)
    for item in plan['expected_image_inputs']:observe_input(item['path'],'immutable-image-matching-input',item)
    for path in plan['additional_image_tools']:observe_input(path,'immutable-image-passive-compiler-tool')
    spec=importlib.util.spec_from_file_location('qualified_wrappers_owned_process',OWNER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    owner=module.Owner(CAP)
    outputs={}
    try:
        for item in plan['commands']:
            result=owned_command(item)
            outputs[item['id']]=result.stdout.decode('utf-8') if item['id']=='wrappers-passive-ELF' else None
        providers=qualify_wrappers_and_providers(outputs['wrappers-passive-ELF'])
        compiler_tools=selected_compiler_inputs()
        bookend_inputs()
        assert not pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
        assert sorted(p.name for p in OUT.iterdir())==sorted(plan['artifact_names']+['capture'])
        artifacts=[]
        for name in plan['artifact_names']:
            path=OUT/name;st=path.stat()
            assert stat.S_ISREG(st.st_mode) and st.st_size>0 and st.st_uid==1000 and st.st_gid==1000
            artifacts.append(dict(name=name,bytes=st.st_size,sha256=digest(path),identity=identity(st)))
        save(CAP/'SELECTED-COMPILER-INPUTS.json',list(held_inputs.values()))
        result=dict(status='PASS_F06_WRAPPERS_FIFTEEN_SERIAL_COMPILER_PASSIVE_COMMANDS_ONLY',
            command_plan_sha256=sys.argv[1],commands=attempts,ownership=owner.records,
            compiler_tools_observed=compiler_tools,artifacts=artifacts,
            provider_qualification=providers,case_ids=plan['case_ids'],
            compiler_diagnostics_retained=True,payload_or_collector_executed=False,
            selected_source_or_kernel_modified=False,staging_or_native_executed=False,
            actual_compiler_ELF_map_provider_independent_qualification_required=True,original_acceptance=False)
        save(CAP/'RESULT.json',result)
        print(json.dumps(dict(status=result['status'],commands=15,artifacts=len(artifacts),
            capture_result_sha256=digest(CAP/'RESULT.json'),payload_or_collector_executed=False,
            original_acceptance=False),sort_keys=True))
        return 0
    except BaseException as exc:
        primary_raw=exc;primary_tb=BaseException.__dict__['__traceback__'].__get__(exc,type(exc))
        try:
            save(CAP/'RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_RETRY',
                error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),
                attempts=attempts,ownership=owner.records if owner else [],
                current_Owner_call_pending=OWNER_CALL_PENDING is not None,
                container_or_resource_release=False,payload_or_collector_executed=False,original_acceptance=False))
        except BaseException as report_error:
            try:OWNER_CUSTODY_ERRORS.append((report_error,BaseException.__dict__['__traceback__'].__get__(report_error,type(report_error))))
            except BaseException:pass
        raise

def entry_once_with_current_Owner_custody():
    global primary_raw,primary_tb
    result=None;error=None;tb=None
    try:
        result=main()  # One invocation, never retry a compiler/passive command.
    except BaseException as caught:
        error=caught;tb=BaseException.__dict__['__traceback__'].__get__(caught,type(caught))
        if primary_raw is None:primary_raw=caught;primary_tb=tb
    finally:
        # The WHOLE diagnostic/retention condition is under the nonescaping guard.
        while True:
            try:
                if OWNER_CALL_PENDING is None:break
                retain_current_Owner_context_nonescaping()
            except BaseException as custody_error:
                try:OWNER_CUSTODY_ERRORS.append((custody_error,BaseException.__dict__['__traceback__'].__get__(custody_error,type(custody_error))))
                except BaseException:pass
    if error is not None:raise BaseException.with_traceback(error,tb)
    return result

if __name__=='__main__':
    sys.exit(entry_once_with_current_Owner_custody())
