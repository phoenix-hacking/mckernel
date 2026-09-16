#!/usr/bin/env python3
"""Build four distinct guarded collectors in the bounded root container profile.

The host entry delegates all lifetime ownership to root_orchestrator.execute.
compile_inside is reached only after the actual root profile checks.
"""
import argparse, importlib.util, json, os, shlex, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
def local(name):
    s = importlib.util.spec_from_file_location('stopped-rescue_'+name,HERE/(name+'.py')); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
FLAGS = ['-std=c11','-D_GNU_SOURCE','-O2','-g','-Wall','-Wextra','-Werror','-fno-pie']
TOOL_PINS = {
 'gcc': (1375456, '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2'),
 'readelf': (815448, 'c5e0de5f419ed907fdc0b7b0a6087ff5c54a8c68db4da01097bdf84a296349b7'),
 'objdump': (444544, '6515c0504cdef7aae684a33101fafbdb656695a2c49cd6611449132ebcfe2a7a')}
LOADER_PINS = {
 'libc.so.6': (2339896, 'b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4'),
 'ld-linux-x86-64.so.2': (930600, '0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b')}
def flags(selector):
    if type(selector) is not int or selector not in range(4): raise ValueError('selector must be 0..3')
    return FLAGS + ['-DM02_STOPPED_RESCUE_TEST_ONLY=1','-DM02_STOPPED_RESCUE_CASE='+str(selector)]
SOURCE_PINS = {'request.c':'c072005948e479e6f50d3f647bf649301741365d7c034c72d3047df3f85cc3ab',
 'request.h':'e767e217104d3b89b0b6d0f74e37f8150600c0b078d40799e75d14f3ede8d00e',
 'sha256.c':'8a8a93d4e7f7d1562f044671a673b48e96dc152ad65bd294f082b7b20b4a39e1',
 'sha256.h':'52cfafeecb6c411f7df956e6d444068185e17177bd8f21ed1270a2d06ce50e97',
 'fixture.c':'d2c33206cb1dc938b31ef83c5827f3aae2ca4e78740178d0df2f221015bdfc6d'}
def identity(path):
    p = local('prepare'); raw = p.read(path); return {'path':str(path),'size':len(raw),'sha256':p.digest(raw)}
def retain_loader(logical,canonical,expected,dst):
    p=local('prepare'); path=logical.resolve(strict=True); size,sha=expected
    p.require(path==canonical,'immutable image loader canonical path')
    data=p.read(path); p.require(len(data)==size and p.digest(data)==sha,'immutable image loader')
    p.atomic_new(dst,data)
    return {'logical':{'path':str(logical),'size':size,'sha256':sha},
            'original':identity(path),'retained':identity(dst)}
def compile_inside(out,supervisor):
    p = local('prepare'); p.packet(HERE/'packet.json'); p.require(not out.exists(),'fresh compile tree')
    out.mkdir(mode=0o700); (out/'tmp').mkdir(); (out/'source/linux-sealed-v1').mkdir(parents=True)
    env = {'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','TZ':'UTC','TMPDIR':str(out/'tmp')}
    record = {'status':'FAIL','application_acceptance':False,'backend_enabled':False,'commands':[],
              'image':p.reviewed('root_orchestrator.py').IMAGE_ID,
              'inputs':[],'compiler_dependencies':[],'compiled_outputs':[],'selectors':dict(p.CASES),'tools':[],'loader_dependencies':[]}
    def execute(label,argv):
        argv = list(argv); argv[0] = shutil.which(argv[0],path=env['PATH']) if not Path(argv[0]).is_absolute() else argv[0]
        p.require(argv[0] is not None,'compiler executable lookup')
        report = supervisor.run_supervised(argv,cwd=str(out),env=env,attempt_dir=out/(label+'-collection'),
                  timeout_seconds=120,cleanup_timeout_seconds=15,stdout_limit_bytes=8*1024**2,stderr_limit_bytes=8*1024**2)
        row = {'label':label,'argv':argv,'environment':env,'collection':report}; record['commands'].append(row)
        p.atomic_new(out/(label+'.json'),(json.dumps(row,sort_keys=True)+'\n').encode())
        p.require(report['status'] == 'COMPLETED' and report['raw_wait_status'] == 0 and report['cleanup_complete'] is True,'bounded compiler result '+label)
        for name in ('stdout','stderr'):
            s = report['streams'][name]; raw = p.read(out/(label+'-collection')/(name+'.bin'))
            p.require(s['eof'] is True and s['discarded_observed_bytes'] == 0 and s['truncated'] is False and
                      s['bytes_retained'] == s['bytes_observed'] == len(raw) and s['artifact']['sha256'] == p.digest(raw),'compiler stream '+label)
        return p.read(out/(label+'-collection')/'stdout.bin')
    try:
        source = p.read(p.SOURCE); generated = p.generate(source); patch = p.read(HERE/'collector.patch')
        p.require(p.patch_is_applicable(source,generated,patch),'exact applicable generated source')
        for name,expected in SOURCE_PINS.items():
            src = p.SOURCE.parent.parent/name if name.startswith('request.') else p.SOURCE.parent/name
            raw = p.read(src); p.require(p.digest(raw) == expected,'released compiler source '+name)
            dst = out/'source'/name if name.startswith('request.') else out/'source/linux-sealed-v1'/name
            p.atomic_new(dst,raw,0o644); record['inputs'].append({'original':identity(src),'retained':identity(dst)})
        for name,raw in [('stopped-rescue-collector.c',generated),('inject.h',p.read(HERE/'inject.h')),('collector.patch',patch),('source.collector.c',source),('generated.diff',p.generated_diff(source,generated))]:
            dst = out/'source/linux-sealed-v1'/name; p.atomic_new(dst,raw,0o644); record['inputs'].append({'retained':identity(dst)})
        compiler = execute('compiler-version',['gcc','--version']); record['compiler_version_sha256'] = p.digest(compiler)
        for name,(size,sha) in TOOL_PINS.items():
            path=Path(shutil.which(name,path=env['PATH'])).resolve(); dst=out/'tools'/name
            data=p.read(path); p.require(str(path)=='/usr/bin/'+name and len(data)==size and p.digest(data)==sha,'immutable image tool')
            p.atomic_new(dst,data); record['tools'].append({'original':identity(path),'retained':identity(dst)})
        for name,(size,sha) in LOADER_PINS.items():
            record['loader_dependencies'].append(retain_loader(Path('/lib64')/name,Path('/usr/lib64')/name,
                                                                (size,sha),out/'loaders'/name))
        units = {'request':out/'source/request.c','sha256':out/'source/linux-sealed-v1/sha256.c','fixture':out/'source/linux-sealed-v1/fixture.c'}
        units.update({case:out/'source/linux-sealed-v1/stopped-rescue-collector.c' for case in p.CASES})
        for name,src in units.items():
            compile_flags = flags(p.CASES[name]) if name in p.CASES else FLAGS
            execute('compile-'+name,['gcc']+compile_flags+['-MD','-MF',str(out/(name+'.d')),'-c',str(src),'-o',str(out/(name+'.o'))])
        executables = {'fixture':['fixture']}; executables.update({'linux-collector-stopped-rescue-'+case:['request','sha256',case] for case in p.CASES})
        for name,objects in executables.items():
            execute('link-'+name,['gcc','-no-pie']+[str(out/(obj+'.o')) for obj in objects]+['-Wl,-Map='+str(out/(name+'.map')),'-o',str(out/name)])
            execute('elf-'+name,['readelf','-h','-l','-d',str(out/name)])
            execute('disassembly-'+name,['objdump','-d',str(out/name)])
            raw = p.read(out/name); p.require(raw[:6] == b'\x7fELF\x02\x01','actual ELF64 little endian')
        deps = {}
        for name in units:
            raw = p.read(out/(name+'.d')).decode(); target,body = raw.split(':',1)
            p.require(shlex.split(target) == [str(out/(name+'.o'))],'exact compiler dependency target')
            for item in shlex.split(body.replace('\\\n',' ')):
                dep = Path(item); dep = (out/dep).resolve() if not dep.is_absolute() else dep.resolve()
                deps[str(dep)] = identity(dep)
        for path,original in sorted(deps.items()):
            dst = out/'compiler-inputs'/path.lstrip('/'); p.atomic_new(dst,p.read(Path(path)))
            record['compiler_dependencies'].append({'original':original,'retained':identity(dst)})
        outputs = [out/(name+suffix) for name in units for suffix in ('.o','.d')]
        outputs += [out/(name+suffix) for name in executables for suffix in ('','.map')]
        record['compiled_outputs'] = [identity(path) for path in outputs]
        record['status'] = 'PASS_STOPPED_RESCUE_BUILD_ONLY'
    except BaseException as error:
        record['first_failure'] = {'type':type(error).__name__,'message':str(error)}; raise
    finally: p.atomic_new(out/'build-record.json',(json.dumps(record,indent=2,sort_keys=True)+'\n').encode())
    return record
def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--packet',type=Path,required=True); parser.add_argument('--attempt-root',type=Path,required=True)
    a = parser.parse_args(); return local('root_orchestrator').execute(a.packet,a.attempt_root,'build',None)
if __name__ == '__main__': raise SystemExit(main())
