#!/usr/bin/env python3
"""Private normal RPM query/extraction only; no install or recovered code runs."""
import base64,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path,PurePosixPath

PACKAGES=Path('/packages')
OUTPUT=Path('/output')
MANIFEST=Path('/producer/PACKAGES.json')
MAX_RPM_BYTES=67108864
MAX_CPIO_BYTES=268435456

def identity(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            data=stream.read(1048576)
            if not data:break
            h.update(data)
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':h.hexdigest()}

def persist():
    (OUTPUT/'EXTRACTION.json').write_text(json.dumps(report,indent=2)+'\n')

def used_disk_bytes():
    # Retained exact RPMS plus fixed allowance for existing HTTP/raw/JSON capture.
    total=spec['retained_download_bytes']+spec['fixed_disk_and_capture_reserve_bytes']
    for directory,dirs,files in os.walk(OUTPUT,followlinks=False):
        total+=8192
        for name in files:
            metadata=os.lstat(Path(directory)/name)
            total+=max(metadata.st_size,getattr(metadata,'st_blocks',0)*512)
        for name in dirs:
            entry=Path(directory)/name
            if entry.is_symlink():total+=max(entry.lstat().st_size,4096)
    return total

def command(label,argv,cwd=None,stdin=None,stdout_file=None,timeout=20,extra_growth=0):
    stderr_path=OUTPUT/(label+'.stderr')
    stdout_path=OUTPUT/(label+'.stdout') if stdout_file is None else stdout_file
    # Both stdout/stderr inherit the frozen256MiB FSIZE hard limit. Extraction
    # additionally reserves bounded payload data plus per-entry metadata below.
    growth=2*MAX_CPIO_BYTES+extra_growth
    used=used_disk_bytes()
    row={'label':label,'argv':argv,'cwd':None if cwd is None else str(cwd),
         'stdout_path':str(stdout_path),'stderr_path':str(stderr_path),
         'state':'PREPARED_NOT_LAUNCHED','pid':None,'returncode':None,
         'wait_joined':None,'started_at':time.time(),'timeout_seconds':timeout,
         'disk_used_before':used,'disk_reserved_growth':growth,
         'global_disk_budget_bytes':spec['global_disk_budget_bytes']}
    report['commands'].append(row)
    persist()  # The exact command exists in evidence before Popen/file creation.
    proc=None;primary=None
    try:
        if used+growth>spec['global_disk_budget_bytes']:
            raise RuntimeError('global2GiB package/extraction/capture budget would be exceeded')
        with stdout_path.open('xb') as stream_out,stderr_path.open('xb') as stream_err:
            proc=subprocess.Popen(argv,cwd=cwd,
                stdin=stdin if stdin is not None else subprocess.DEVNULL,
                stdout=stream_out,stderr=stream_err)
            row.update(state='RUNNING',pid=proc.pid,wait_joined=False)
            try:
                text=Path('/proc')/str(proc.pid)/'stat'
                row['birth']=text.read_text().rsplit(')',1)[1].split()[19]
            except OSError as error:
                row['birth_observation']='UNKNOWN: '+str(error)
            persist()
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired as error:
                row.update(state='TIMEOUT',primary_error=type(error).__name__+': '+str(error))
                # This Popen owns its direct unreaped child; its PID cannot be
                # reused before wait. Only this exact child is retired here.
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception as retire_error:
                    row['retirement_error']=type(retire_error).__name__+': '+str(retire_error)
                raise
            row.update(returncode=proc.returncode,wait_joined=True,
                       state='PASS' if proc.returncode==0 else 'FAILED_RETURN')
            if proc.returncode:raise RuntimeError(label+' returned nonzero; retain raw diagnostics')
    except Exception as error:
        primary=error
        row.setdefault('primary_error',type(error).__name__+': '+str(error))
        if proc is None:
            row.update(state='NOT_LAUNCHED_FAILURE',returncode=None,wait_joined=None,
                       launch_outcome='NO_CHILD_CREATED')
        elif proc.returncode is not None:
            row.update(returncode=proc.returncode,wait_joined=True)
        else:
            row.update(returncode=None,wait_joined=False,outcome='UNKNOWN_DIRECT_CHILD_UNJOINED')
        raise
    finally:
        row['finished_at']=time.time()
        for key,path in [('stdout',stdout_path),('stderr',stderr_path)]:
            try:
                if path.is_file():row[key]=identity(path)
            except Exception as evidence_error:
                row[key+'_capture_error']=type(evidence_error).__name__+': '+str(evidence_error)
        try:row['disk_used_after']=used_disk_bytes()
        except Exception as evidence_error:
            row['disk_capture_error']=type(evidence_error).__name__+': '+str(evidence_error)
            if primary is None:raise
        try:persist()
        except Exception as evidence_error:
            if primary is None:raise
            print('Secondary receipt-write failure while preserving primary '+repr(primary)+': '+repr(evidence_error),file=sys.stderr)
    return stdout_path.read_bytes() if stdout_file is None else b''

def armored_key_packets(value):
    text=value.decode('ascii')
    begin='-----BEGIN PGP PUBLIC KEY BLOCK-----';end='-----END PGP PUBLIC KEY BLOCK-----'
    assert text.count(begin)==1 and text.count(end)==1,'expected one existing release key'
    body=text.split(begin,1)[1].split(end,1)[0]
    # Ignore armor transport headers/CRC only; compare the complete existing
    # OpenPGP packet bytes. No signature or fingerprint algorithm is recreated.
    payload=''.join(line.strip() for line in body.splitlines()
                    if line.strip() and ':' not in line and not line.strip().startswith('='))
    return base64.b64decode(payload,validate=True)

def bind_existing_trusted_key():
    bindings={'be8c4f070b696e64d8ce40e59a95a57e8b5c776f0015c2fd64e14b896622bdb4':
              'FC226859C0860BF0DDB95B085B106C736FEDFC85'}
    key=Path(spec['trusted_release_key_path'])
    actual=identity(key)
    assert actual['sha256']==spec['release_key_sha256'],'actual image release-key bytes differ'
    assert bindings[actual['sha256']]==spec['release_key_fingerprint'],'source full-fingerprint binding differs'
    key_id=spec['release_key_fingerprint'][-8:].lower()
    trusted=command('already-trusted-key-material',['/usr/bin/rpm','-q','--qf',
        '%{NAME}|%{VERSION}|%{RELEASE}|%{DESCRIPTION}\n','gpg-pubkey-'+key_id])
    fields=trusted.split(b'|',3)
    assert len(fields)==4 and fields[0]==b'gpg-pubkey' and fields[1].decode('ascii')==key_id,'trusted RPM key record differs'
    source_packets=armored_key_packets(key.read_bytes())
    trusted_packets=armored_key_packets(fields[3])
    assert source_packets==trusted_packets,'already-trusted RPM key material differs from source-pinned key'
    report['trusted_release_key']={'source_pinned_file':actual,
        'full_primary_fingerprint':spec['release_key_fingerprint'],
        'full_fingerprint_basis':'existing source lock exactkeySHA/fullfingerprint binding; actual existing RPMdb packets equal source-pinned bytes, no new crypto implementation',
        'existing_rpm_key_record':'|'.join(x.decode('ascii') for x in fields[:3]),
        'key_packet_sha256':hashlib.sha256(source_packets).hexdigest(),
        'already_trusted_material_equal':True,'import_or_trust_mutation':False}
    persist()

assert OUTPUT.is_dir() and not list(OUTPUT.iterdir()),'output must be new empty private bind'
report={'status':'IN_PROGRESS','scope':'Exact ordinary RPM metadata/signature/query/passive extraction only; no install, script, CMake/compiler/project/test/native execution','commands':[],'packages':[],'original_acceptance':False}
try:
    spec=json.loads(MANIFEST.read_text())
    # Same immutable native46d image, RO root and no key/RPMdb mounts/mutations.
    # Reuse the actual full-key proof; only this new RPM signature is queried.
    assert spec['reused_key_proof_image_id']=='sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94','key proof image differs'
    trusted=spec['reused_trusted_release_key']
    assert trusted['source_pinned_file']['sha256']==spec['release_key_sha256'],'reused exact key SHA differs'
    assert trusted['full_primary_fingerprint']==spec['release_key_fingerprint'],'reused full fingerprint differs'
    assert trusted['already_trusted_material_equal'] is True and trusted['import_or_trust_mutation'] is False,'reused actual key proof scope differs'
    report['trusted_release_key']=trusted
    report['trusted_release_key_reuse']=spec['reused_key_proof']
    # Inspect every exact download before any payload is extracted.
    for item in spec['packages']:
        archive=PACKAGES/item['filename']
        assert archive.is_file() and not archive.is_symlink(),'exact regular RPM absent'
        record=identity(archive)
        assert 0<record['bytes']<=MAX_RPM_BYTES,'RPM exceeds bounded packet'
        if item['expected_bytes'] is not None:assert record['bytes']==item['expected_bytes'],'pinned RPM length differs'
        if item['expected_sha256'] is not None:assert record['sha256']==item['expected_sha256'],'pinned RPM SHA differs'
        key=item['id']
        fields=command(key+'-nevra',['/usr/bin/rpm','-qp','--qf','%{NAME}|%{EPOCHNUM}|%{VERSION}|%{RELEASE}|%{ARCH}\n',str(archive)]).decode('ascii').strip().split('|')
        assert fields==item['expected_rpm_fields'],'exact requested RPM NEVRA differs'
        signature=command(key+'-signature',['/usr/bin/rpmkeys','--checksig','--verbose',str(archive)])
        assert b'6fedfc85' in signature.lower() and b'nokey' not in signature.lower(),'signature did not bind pinned Rocky10 key; no extraction'
        command(key+'-requires',['/usr/bin/rpm','-qp','--requires',str(archive)])
        if key=='libuv':
            provides=command(key+'-provides',['/usr/bin/rpm','-qp','--provides',str(archive)]).decode('utf-8').splitlines()
            assert item['required_capability'] in provides,'exact actual RPM header does not provide missing capability'
        if key=='crash':
            command(key+'-provides',['/usr/bin/rpm','-qp','--provides',str(archive)])
            source_rpm=command(key+'-sourcerpm',['/usr/bin/rpm','-qp','--qf','%{SOURCERPM}\n',str(archive)]).decode('utf-8').strip()
            assert source_rpm==item['expected_source_rpm'],'actual RPM header source filename differs from exact binary metadata'
            report['crash_declared_source_RPM']=source_rpm
        command(key+'-payload-manifest',['/usr/bin/rpm','-qp','--dump',str(archive)])
        report['packages'].append({'id':key,'archive':record,'rpm_fields':fields,'trusted_signature_exit0':True,'trusted_full_fingerprint':report['trusted_release_key']['full_primary_fingerprint']})
    for item in spec['packages']:
        key=item['id'];archive=PACKAGES/item['filename'];target=OUTPUT/key;target.mkdir()
        payload=OUTPUT/(key+'.payload.cpio')
        command(key+'-rpm2cpio',['/usr/bin/rpm2cpio',str(archive)],stdout_file=payload,timeout=30)
        assert 0<payload.stat().st_size<=MAX_CPIO_BYTES,'expanded CPIO exceeds packet'
        with payload.open('rb') as stream:
            names=command(key+'-cpio-names',['/usr/bin/cpio','--list','--quiet'],stdin=stream,timeout=15).decode('utf-8').splitlines()
        for name in names:
            parts=PurePosixPath(name).parts
            assert not name.startswith('/') and '..' not in parts and '\\' not in name,'payload path escapes private extraction'
        with payload.open('rb') as stream:
            command(key+'-cpio-extract',['/usr/bin/cpio','--extract','--make-directories','--quiet','--no-absolute-filenames','--no-preserve-owner'],cwd=target,stdin=stream,timeout=30,extra_growth=payload.stat().st_size+len(names)*8192)
        # Recovered executable file bytes are data in this phase, never invoked.
        if key=='binutils-devel':
            found={}
            for relative,expected in spec['selected_BFD_outputs'].items():
                q=target/relative;record=identity(q);assert record['sha256']==expected,'selected BFD payload pin differs';found[relative]=record
            report['selected_BFD_outputs']=found
        elif key=='cmake':
            executable=target/'usr/bin/cmake';report['cmake_binary']=identity(executable)
            command('cmake-ELF-metadata',['/usr/bin/readelf','--wide','--file-header','--dynamic',str(executable)],timeout=10)
        elif key=='cmake-data':
            roots=[q for q in (target/'usr/share').glob('cmake*') if (q/'Modules/CMakeDetermineSystem.cmake').is_file()]
            assert len(roots)==1,'exact CMake module root unbound'
            report['cmake_module_root']=str(roots[0])
        elif key=='libuv':
            runtime=target/'usr/lib64/libuv.so.1'
            assert runtime.exists(),'exact runtime SONAME path absent from actual trusted payload'
            resolved=runtime.resolve(strict=True)
            relative=resolved.relative_to(target.resolve())
            assert resolved.is_file(),'resolved runtime implementation is not regular data'
            metadata=command('libuv-ELF-metadata',['/usr/bin/readelf','--wide','--file-header','--dynamic','--version-info',str(resolved)],timeout=10).decode('utf-8')
            assert re.search(r'\(SONAME\).*\[libuv\.so\.1\]',metadata),'actual runtime ELF SONAME differs'
            assert 'ELF64' in metadata and 'Advanced Micro Devices X86-64' in metadata,'actual runtime ELF architecture differs'
            report['libuv_runtime']={'soname_path':str(runtime),'is_symlink':runtime.is_symlink(),
                'symlink_text':os.readlink(runtime) if runtime.is_symlink() else None,
                'resolved_implementation_relative':str(relative),
                'implementation':identity(resolved),'required_SONAME':'libuv.so.1',
                'actual_SONAME_verified':True,'header_provides_exact_capability':True,
                'runtime_library_function_or_CMake_main_executed':False}
        elif key=='crash':
            executable=target/'usr/bin/crash'
            resolved=executable.resolve(strict=True)
            relative=resolved.relative_to(target.resolve())
            assert resolved.is_file(),'selected literal payload must resolve to a regular artifact'
            assert 0<resolved.stat().st_size<=134217728,'selected crash artifact exceeds retained128MiB passive envelope'
            metadata_path=OUTPUT/'crash-ELF-metadata.stdout'
            command('crash-ELF-metadata',['/usr/bin/readelf','--wide','--file-header','--program-headers','--dynamic','--dyn-syms','--version-info',str(resolved)],stdout_file=metadata_path,timeout=20)
            elf64=False;amd64=False
            selected={name:[] for name in spec['crash_selected18_names']}
            needed=[];dynamic_flags=[];search_paths=[];interpreter=[]
            with metadata_path.open('r') as metadata_stream:
                for line in metadata_stream:
                    if 'ELF64' in line:elf64=True
                    if 'Advanced Micro Devices X86-64' in line:amd64=True
                    found=re.search(r'\(NEEDED\).*?\[([^]]+)\]',line)
                    if found:needed.append(found[1])
                    if '(FLAGS' in line:dynamic_flags.append(line.rstrip())
                    if '(RPATH)' in line or '(RUNPATH)' in line:search_paths.append(line.rstrip())
                    if 'Requesting program interpreter:' in line:interpreter.append(line.strip())
                    found=re.match(r'^\s*(\d+):\s+([0-9a-fA-F]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)',line)
                    if found and found[8].split('@',1)[0] in selected:
                        name=found[8].split('@',1)[0]
                        selected[name].append({'index':int(found[1]),'value_hex':found[2],'size_text':found[3],'kind':found[4],'binding':found[5],'visibility':found[6],'section':found[7],'versioned_name':found[8],'raw':line.rstrip()})
            assert elf64 and amd64,'actual selected crash ELF architecture differs'
            def exported(row):
                return row['section'] not in ['UND','ABS'] and row['binding'] in ['GLOBAL','WEAK'] and row['visibility'] in ['DEFAULT','PROTECTED']
            missing=[name for name,rows in selected.items() if not any(exported(row) for row in rows)]
            data_comparisons={name:{'expected_bytes':width,'actual_exported_OBJECT_rows':[row for row in selected[name] if exported(row) and row['kind']=='OBJECT'],'matches_expected_width':any(exported(row) and row['kind']=='OBJECT' and int(row['size_text'],16 if row['size_text'].lower().startswith('0x') else 10)==width for row in selected[name])} for name,width in spec['expected_crash_data_widths'].items()}
            report['crash_provider']={'selected_literal':'/usr/bin/crash','private_payload_literal':str(executable),'literal_is_symlink':executable.is_symlink(),'literal_readlink':os.readlink(executable) if executable.is_symlink() else None,'resolved_implementation_relative':str(relative),'implementation':identity(resolved),'mode':oct(resolved.stat().st_mode&0o7777),'actual_DT_NEEDED':needed,'actual_interpreter':interpreter,'actual_dynamic_flags':dynamic_flags,'actual_RPATH_RUNPATH':search_paths,'selected18_dynamic_rows':selected,'selected18_names_without_recorded_defined_export':missing,'actual_data_width_comparisons':data_comparisons,'private_payload_NOT_installed_RPMdb':True,'crash_main_or_version_or_extension_or_API_executed':False,'provider_header_BFD_ABI_accepted':False,'ABI_limit':'This genuine trusted binary provides only observed dynamic definition/type/size/version and dependency facts. Exact producer source/header and consumed machdep prefix/command entry/BFD section fields plus all function prototypes remain unqualified. Names and known2.41 archive/header do not substitute for the actual crash/BFD implementation/provider; actual DT_NEEDED closure is not inferred from RPMRequires.'}
        report['packages'][next(i for i,x in enumerate(report['packages']) if x['id']==key)]['payload_cpio']=identity(payload)
    report['status']='PASS_ACQUISITION_AND_PASSIVE_EXTRACTION_ONLY'
except Exception as error:
    report['status']='FAIL';report['error']=type(error).__name__+': '+str(error)
    try:persist()
    except Exception as evidence_error:print('Secondary final receipt-write failure: '+repr(evidence_error),file=sys.stderr)
    raise
(OUTPUT/'EXTRACTION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,sort_keys=True))
