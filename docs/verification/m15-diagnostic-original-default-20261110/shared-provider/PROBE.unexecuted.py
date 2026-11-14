#!/usr/bin/python3
"""Read only two caller-selected provider ELFs; no target program or API call."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

OUT = Path('/output')
report = {'schema':'mckernel.two-diagnostic-provider-passive-result.v1',
          'status':'RUNNING','providers':[], 'original_leaves_accepted':False,
          'runtime_or_API_executed':False}

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def persist():
    temporary = OUT / 'REPORT.json.tmp'
    temporary.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    os.replace(temporary, OUT / 'REPORT.json')

def identity(literal, limit):
    first = Path(literal)
    current = first
    chain = []
    for unused in range(9):
        info = current.lstat()
        if not stat.S_ISLNK(info.st_mode):
            break
        text = os.readlink(current)
        if len(text) > 512:
            raise ValueError('oversize selected symlink')
        chain.append({'path':str(current),'text':text})
        current = Path(os.path.normpath(str(current.parent / text))) if not os.path.isabs(text) else Path(text)
    else:
        raise ValueError('selected symlink chain exceeds eight')
    actual = first.resolve(strict=True)
    if not str(actual).startswith('/usr/lib64/'):
        raise ValueError('selected provider leaves real image library namespace')
    info = actual.stat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
        raise ValueError('selected provider is not bounded regular input')
    blob = actual.read_bytes()
    if len(blob) != info.st_size:
        raise ValueError('selected provider size changed')
    item = {'path':literal,'symlinks':chain,'resolved_path':str(actual),
            'bytes':len(blob),'sha256':digest(blob),'mode':oct(stat.S_IMODE(info.st_mode)),
            'uid':info.st_uid,'gid':info.st_gid}
    if len(blob) >= 64 and blob[:4] == b'\x7fELF':
        if blob[4:6] != bytes([2,1]):
            raise ValueError('selected provider is not ELF64 little endian')
        etype,machine = struct.unpack_from('<HH',blob,16)
        item['ELF'] = {'class':64,'little_endian':True,'type':etype,'machine':machine}
    else:
        item['ELF'] = None
    return item

symbol_row = re.compile(r'^\s*(\d+):\s+([0-9a-fA-F]+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)(?:\s+\((\d+)\))?\s*$')
version_line = re.compile(r'^\s*([0-9a-fA-F]+):\s+(.*)$')
version_item = re.compile(r'([0-9a-fA-F]+)(h?)\s*\(([^)]+)\)')
version_def = re.compile(r'Index:\s*(\d+)\s+Cnt:\s*\d+\s+Name:\s*(\S+)')

def parse_selected(text, expected):
    symbols = []
    versym = {}
    definitions = {}
    in_versions = False
    soname = None
    needed = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('Version symbols section'):
            in_versions = True
        elif stripped.startswith('Version definition section') or stripped.startswith('Version needs section'):
            in_versions = False
        if in_versions:
            match = version_line.match(line)
            if match:
                start = int(match.group(1),16)
                for offset,entry in enumerate(version_item.finditer(match.group(2))):
                    versym[start+offset] = {'index':int(entry.group(1),16),'hidden':bool(entry.group(2)),'name':entry.group(3)}
        match = version_def.search(line)
        if match:
            definitions[int(match.group(1))] = match.group(2)
        match = re.search(r'\(SONAME\).*\[([^]]+)\]',line)
        if match:
            soname = match.group(1)
        match = re.search(r'\(NEEDED\).*\[([^]]+)\]',line)
        if match:
            needed.append(match.group(1))
        match = symbol_row.match(line)
        if match:
            name = match.group(8)
            symbols.append({'index':int(match.group(1)),'value':match.group(2),
                            'bytes':int(match.group(3)),'kind':match.group(4),
                            'binding':match.group(5),'visibility':match.group(6),
                            'section':match.group(7),'name':name,'base_name':name.split('@')[0],
                            'raw':line})
    if soname != expected['required_SONAME']:
        raise ValueError('selected provider SONAME differs')
    selected = []
    for required in expected['required_unique']:
        eligible = []
        for symbol in symbols:
            if symbol['base_name'] != required['name'] or symbol['section'] == 'UND':
                continue
            if symbol['kind'] not in ('FUNC','IFUNC') or symbol['binding'] not in ('GLOBAL','WEAK') or symbol['visibility'] != 'DEFAULT':
                continue
            full = symbol['name']
            version = full.split('@')[-1] if '@' in full else None
            vs = versym.get(symbol['index'])
            if vs is None:
                continue
            if required['required_version'] is None:
                if vs['hidden'] or ('@' in full and '@@' not in full):
                    continue
            elif version != required['required_version']:
                continue
            if version is None:
                if vs['index'] != 1 or vs['name'] != '*global*':
                    continue
            elif vs['name'] != version or definitions.get(vs['index']) != version:
                continue
            eligible.append({'required':required,'definition':symbol,'versym':vs,
                             'verdef':definitions.get(vs['index'])})
        if len(eligible) != 1:
            raise ValueError('selected definition/version closure differs for '+required['name'])
        selected.append(eligible[0])
    return {'SONAME':soname,'DT_NEEDED':needed,'selected_definitions':selected,
            'version_definition_names':definitions,
            'scope':'Exact caller-selected definitions/versions, no target loader/API invocation'}

try:
    spec = json.loads(Path('/input/INPUTS.json').read_text())
    helper = Path('/input/owned_process.py')
    if digest(helper.read_bytes()) != spec['existing_owner_helper']['sha256']:
        raise ValueError('owned child helper binding differs')
    sys.path.insert(0,'/input')
    from owned_process import Owner
    owner = Owner(OUT)
    environment = {'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','TZ':'UTC',
                   'TMPDIR':'/output/tmp','PYTHONDONTWRITEBYTECODE':'1'}
    def run(argv,label):
        completed = owner.run(argv,env=environment,cwd='/output',timeout=15,label=label)
        if len(completed.stdout) > spec['readelf_stdout_limit_bytes'] or len(completed.stderr) > spec['command_stderr_limit_bytes']:
            raise ValueError('passive command capture bound exceeded')
        if completed.returncode != 0 or completed.stderr:
            raise ValueError('passive command failed: '+label)
        return completed.stdout.decode('utf-8','strict')
    qformat = '%{NAME}|%{EPOCHNUM}|%{VERSION}|%{RELEASE}|%{ARCH}|%{SOURCERPM}\n'
    for expected in spec['providers']:
        key = expected['id']
        entry = {'id':key}
        report['providers'].append(entry)
        runtime = identity(expected['runtime_anchor'],spec['file_size_limit_bytes'])
        link = identity(expected['link_input'],spec['file_size_limit_bytes'])
        entry['runtime'] = runtime
        entry['link_input'] = link
        if runtime.get('ELF') != {'class':64,'little_endian':True,'type':3,'machine':62}:
            raise ValueError('runtime provider ELF role differs')
        if runtime['resolved_path'] != link['resolved_path'] or runtime['sha256'] != link['sha256']:
            raise ValueError('selected development and runtime provider files differ')
        entry['runtime_link_same_file'] = True
        rpms = []
        for role,path in [('runtime',expected['runtime_anchor']),('devel',expected['link_input'])]:
            text = run(['/usr/bin/rpm','-qf','--qf',qformat,path],key+'-'+role+'-rpm')
            fields = text.strip().split('|')
            if len(fields) != 6 or '\n' in text.strip() or not fields[5].endswith('.src.rpm'):
                raise ValueError('RPM source/header row shape differs')
            prior = expected['prior_runtime_package'] if role == 'runtime' else expected['prior_devel_package']
            if prior is not None and fields[:5] != prior:
                raise ValueError('actual installed provider package differs from saved consumer profile')
            rpms.append({'role':role,'argv_path':path,'raw':text,'fields':fields})
        entry['package_headers'] = rpms
        if rpms[0]['fields'][1:] != rpms[1]['fields'][1:]:
            raise ValueError('runtime and development EVR/arch/source header relation differs')
        entry['same_runtime_devel_EVR_arch_source'] = True
        text = run(['/usr/bin/readelf','--wide','--file-header','--section-headers','--dynamic','--dyn-syms','--version-info',expected['runtime_anchor']],key+'-ELF')
        entry['ELF_join'] = parse_selected(text,expected)
        after = identity(expected['runtime_anchor'],spec['file_size_limit_bytes'])
        if after != runtime:
            raise ValueError('immutable provider identity changed during passive read')
        entry['identity_stable_after_metadata'] = True
        entry['caller_rows'] = expected['caller_rows']
    report['owned_records'] = owner.records
    if len(owner.records) != 6:
        raise ValueError('exact six passive child commands not recorded')
    for item in owner.records:
        if not (int(item['leader_birth']) > 0 and item['status'] == 0 and item['leader_parent_joined'] and item['whole_descendants_joined'] and item['streams_closed']):
            raise ValueError('positive child ownership/exit/stream facts missing')
        if item.get('adopted_reaps') or item.get('adopted_kills') or item.get('remaining_direct_children') or item.get('error') or item.get('timed_out') or item.get('leader_group_signalled'):
            raise ValueError('unresolved or destructive child cleanup')
    report['status'] = 'PASS_EXACT_TWO_PROVIDER_ELF_VERSION_FILE_PACKAGE_JOINS_PENDING_ORIGINAL_LEAF_REVIEW'
    persist()
    print(report['status'])
except BaseException as primary:
    report['status'] = 'FAIL_PASSIVE_PROVIDER_CAPTURE_OR_JOIN'
    report['error'] = type(primary).__name__+': '+str(primary)
    try:
        persist()
    except BaseException as secondary:
        try:
            sys.stderr.write('secondary receipt write failure: '+type(secondary).__name__+': '+str(secondary)+'\n')
        except BaseException:
            pass
    raise
