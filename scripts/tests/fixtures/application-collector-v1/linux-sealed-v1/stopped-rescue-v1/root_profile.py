#!/usr/bin/env python3
"""Prepare the dedicated read-only inputs and root container command."""
import importlib.util, json, math, os, shlex
from pathlib import Path
HERE = Path(__file__).resolve().parent
FILES = ('packet.json','tests.md','prepare.py','collector.patch','inject.h','oracle.py','run.py',
         'build_owner.py','root_profile.py','root_inside.py','root_orchestrator.py')
def local(name):
    s=importlib.util.spec_from_file_location('stopped-rescue_'+name,HERE/(name+'.py')); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def verify_build(path):
    p=local('prepare'); raw=p.read(path); record=json.loads(raw); root=path.parent
    p.require(record['status']=='PASS_STOPPED_RESCUE_BUILD_ONLY' and record['application_acceptance'] is False and
              record['backend_enabled'] is False and record['selectors']==p.CASES,'build acceptance boundary')
    p.require(record['image']==p.reviewed('root_orchestrator.py').IMAGE_ID,'pinned build image')
    outputs=record['compiled_outputs']; expected={name+suffix for name in ['request','sha256','fixture']+list(p.CASES) for suffix in ('.o','.d')}
    expected.update(name+suffix for name in ['fixture']+['linux-collector-stopped-rescue-'+case for case in p.CASES] for suffix in ('','.map'))
    p.require({Path(row['path']).name for row in outputs}==expected and len(outputs)==len(expected),'exact compiled outputs')
    for row in outputs:
        member=root/Path(row['path']).name; data=p.read(member)
        p.require(len(data)==row['size'] and p.digest(data)==row['sha256'],'compiled output binding')
    p.require(record['compiler_dependencies'] and record['commands'],'actual build provenance')
    prefix=Path('/work/build')
    def mapped(value):
        selected=Path(value); p.require(selected.is_absolute() and '..' not in selected.parts and str(selected).startswith(str(prefix)+'/'),'container build path')
        return root/selected.relative_to(prefix)
    def bind(row):
        data=p.read(mapped(row['path'])); p.require(len(data)==row['size'] and p.digest(data)==row['sha256'],'retained build binding'); return data
    deps={}
    for name in ['request','sha256','fixture']+list(p.CASES):
        target,body=p.read(root/(name+'.d')).decode().split(':',1)
        p.require(shlex.split(target)==[str(prefix/(name+'.o'))],'dependency target')
        for value in shlex.split(body.replace('\\\n',' ')): deps[os.path.normpath(value)]=True
    seen=set()
    for row in record['compiler_dependencies']:
        original=row['original']; retained=row['retained']; bind(retained)
        p.require(original['path'] not in seen and original['sha256']==retained['sha256'] and original['size']==retained['size'],'compiler dependency membership')
        seen.add(original['path'])
    p.require(seen==set(deps),'exact compiler dependencies from .d files')
    build=local('build_owner')
    source=p.read(p.SOURCE); generated=p.generate(source)
    expected_inputs={}
    for name,sha in build.SOURCE_PINS.items():
        src=p.SOURCE.parent.parent/name if name.startswith('request.') else p.SOURCE.parent/name
        data=p.read(src); p.require(p.digest(data)==sha,'released input identity')
        relative='source/'+name if name.startswith('request.') else 'source/linux-sealed-v1/'+name
        original='/workspace/'+str(src.relative_to(p.REPO))
        expected_inputs[str(prefix/relative)]=(data,original)
    for name,data in [('stopped-rescue-collector.c',generated),('inject.h',p.read(HERE/'inject.h')),
                      ('collector.patch',p.read(HERE/'collector.patch')),('source.collector.c',source),
                      ('generated.diff',p.generated_diff(source,generated))]:
        expected_inputs[str(prefix/'source/linux-sealed-v1'/name)]=(data,None)
    p.require(len(record['inputs'])==len(expected_inputs) and
              {row['retained']['path'] for row in record['inputs']}==set(expected_inputs),'exact source input membership')
    for row in record['inputs']:
        data,original=expected_inputs[row['retained']['path']]
        p.require(bind(row['retained'])==data,'exact retained source bytes')
        if original is None: p.require(set(row)=={'retained'},'generated input schema')
        else: p.require(set(row)=={'original','retained'} and row['original']=={'path':original,'size':len(data),'sha256':p.digest(data)},'exact original source input')
    for group,pins,directory,original_directory in [('tools',build.TOOL_PINS,'tools','/usr/bin'),
                         ('loader_dependencies',build.LOADER_PINS,'loaders','/usr/lib64')]:
        p.require(len(record[group])==len(pins) and
                  {row['retained']['path'] for row in record[group]}=={str(prefix/directory/name) for name in pins},'exact tool/loader membership')
        for row in record[group]:
            name=Path(row['retained']['path']).name; size,sha=pins[name]
            bind(row['retained'])
            p.require(row['original']=={'path':str(Path(original_directory)/name),'size':size,'sha256':sha} and
                      row['retained']['size']==size and row['retained']['sha256']==sha,'pinned tool/loader identity')
            if group=='loader_dependencies':
                p.require(set(row)=={'logical','original','retained'} and
                          row['logical']=={'path':'/lib64/'+name,'size':size,'sha256':sha},'pinned logical loader identity')
    units=['request','sha256','fixture']+list(p.CASES)
    executables=['fixture']+['linux-collector-stopped-rescue-'+case for case in p.CASES]
    labels=['compiler-version']+['compile-'+name for name in units]+[kind+'-'+name for name in executables for kind in ('link','elf','disassembly')]
    p.require([row['label'] for row in record['commands']]==labels,'exact ordered compiler commands')
    matrix=[['/usr/bin/gcc','--version']]
    for name in units:
        src=prefix/'source/request.c' if name=='request' else prefix/'source/linux-sealed-v1'/('stopped-rescue-collector.c' if name in p.CASES else name+'.c')
        flags=build.flags(p.CASES[name]) if name in p.CASES else build.FLAGS
        matrix.append(['/usr/bin/gcc']+flags+['-MD','-MF',str(prefix/(name+'.d')),'-c',str(src),'-o',str(prefix/(name+'.o'))])
    for name in executables:
        objects=['fixture'] if name=='fixture' else ['request','sha256',name[len('linux-collector-stopped-rescue-'):]]
        matrix.extend([['/usr/bin/gcc','-no-pie']+[str(prefix/(obj+'.o')) for obj in objects]+['-Wl,-Map='+str(prefix/(name+'.map')),'-o',str(prefix/name)],
                       ['/usr/bin/readelf','-h','-l','-d',str(prefix/name)],['/usr/bin/objdump','-d',str(prefix/name)]])
    p.require([row['argv'] for row in record['commands']]==matrix,'exact complete compiler command matrix')
    for row in record['commands']:
        report=row['collection']; label=row['label']; argv=row['argv']
        p.require(report['status']=='COMPLETED' and type(report['raw_wait_status']) is int and report['raw_wait_status']==0 and report['cleanup_complete'] is True,'compiler completion')
        p.require(row['environment']=={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','TZ':'UTC','TMPDIR':'/work/build/tmp'},'exact compiler environment')
        p.require(report['argv']==argv and report['cwd']==str(prefix) and report['env']==row['environment'] and
                  report['executable_path']==argv[0],'exact collected command context')
        size,sha=build.TOOL_PINS[Path(argv[0]).name]
        p.require(report['executable']=={'path':argv[0],'size':size,'sha256':sha},'exact executed tool identity')
        p.require(report['timeout_seconds']==120 and report['cleanup_timeout_seconds']==15 and
                  report['stdout_limit_bytes']==report['stderr_limit_bytes']==8*1024**2,'exact compiler bounds')
        for clock in ('payload_monotonic_started','payload_monotonic_deadline','payload_completion_observed_monotonic'):
            p.require(type(report[clock]) in (int,float) and math.isfinite(report[clock]),'finite compiler clock')
        p.require(report['payload_monotonic_deadline']==report['payload_monotonic_started']+120 and
                  report['payload_monotonic_started']<=report['payload_completion_observed_monotonic']<report['payload_monotonic_deadline'],'compiler deadline')
        for stream in ('stdout','stderr'):
            entry=report['streams'][stream]; raw=bind(entry['artifact'])
            p.require(entry['artifact']['path']==str(prefix/(label+'-collection')/(stream+'.bin')),'exact compiler stream path')
            p.require(entry['eof'] is True and entry['truncated'] is False and entry['discarded_observed_bytes']==0 and entry['bytes_retained']==entry['bytes_observed']==len(raw),'complete compiler stream')
    p.require(p.read(root/'source/linux-sealed-v1/stopped-rescue-collector.c')==generated,'generated compiler source')
    p.require(p.read(root/'source/linux-sealed-v1/inject.h')==p.read(HERE/'inject.h'),'compiled injection header')
    return record
def create(packet,profile,mode,build_record,nonce):
    p=local('prepare'); p.packet(packet); owner=p.reviewed('root_orchestrator.py'); primitive=p.reviewed('root_profile.py')
    p.require(mode in ('build','run') and not profile.exists(),'fresh mode/profile')
    profile.mkdir(mode=0o700)
    for name,modebits in [('inputs',0o755),('work',0o700)]: (profile/name).mkdir(mode=modebits)
    (profile/'work/tmp').mkdir(mode=0o700)
    manifest={'schema_version':1,'kind':'linux-sealed-stopped-rescue-root-inputs','mode':mode,'profile_nonce':nonce,
              'image':owner.IMAGE_ID,'application_acceptance':False,'backend_enabled':False,'files':{},
              'work_directory':primitive.directory_identity(profile/'work'),'inputs_directory':primitive.directory_identity(profile/'inputs')}
    sources={name:HERE/name for name in FILES}
    if mode=='run':
        verify_build(build_record); sources['build-record.json']=build_record
        for name in ['fixture']+['linux-collector-stopped-rescue-'+case for case in p.CASES]: sources[name]=build_record.parent/name
    for name,source in sources.items():
        raw=p.read(source); bits=0o755 if name=='fixture' or name.startswith('linux-collector-stopped-rescue-') else 0o644
        p.atomic_new(profile/'inputs'/name,raw,bits)
        manifest['files'][name]={'source':str(source),'size_bytes':len(raw),'sha256':p.digest(raw),'mode':bits}
    p.atomic_new(profile/'inputs/inputs.json',(json.dumps(manifest,sort_keys=True)+'\n').encode(),0o644)
    plan={'create':owner.expected_create(profile,nonce),'mode':mode,'profile_nonce':nonce,'application_acceptance':False}
    p.atomic_new(profile/'plan.json',(json.dumps(plan,sort_keys=True)+'\n').encode()); return plan,manifest
