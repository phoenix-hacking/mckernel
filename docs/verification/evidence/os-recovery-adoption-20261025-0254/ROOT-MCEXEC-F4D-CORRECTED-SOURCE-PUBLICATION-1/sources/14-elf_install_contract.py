"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only default-graph/installed-library checker. No compiler, subprocess or API call.
The only permitted installed-byte change is the exact CMake RPATH replacement.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct

PROVIDER_SHA='89639e9d56c390968a86a95bb734128ec61bd0f6de28f7c7992cfb9e00b9ef96'
PROVIDER_BYTES=12095032
DATA={'__argc','__argv','loglevel','namespace_files','reserve_mem_conf','ihklib_os_query_mem_type_str'}
NATIVE=['-lgcc_s','-lutil','-lrt','-lpthread','-lm','-ldl','-lc']

def need(ok,why):
    if not ok:raise ValueError(why)
def cstring(raw,offset):
    end=raw.find(b'\0',offset);need(0<=offset<end<len(raw),'bounded nonempty ELF string');return raw[offset:end]
def sections(raw):
    need(raw[:7]==b'\x7fELF\x02\x01\x01' and struct.unpack_from('<H',raw,18)[0]==62,'selected x86_64 ELF64LE')
    offset=struct.unpack_from('<Q',raw,40)[0];size,count,names=struct.unpack_from('<HHH',raw,58)
    need(size==64 and count>0 and names<count and offset+size*count<=len(raw),'bounded section table')
    result=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*size) for i in range(count)]
    for s in result:
        if s[1]!=8:need(s[4]+s[5]<=len(raw),'bounded section bytes')
    return result

def installed_bytes(source,prefix):
    table=sections(source);dynamic=[s for s in table if s[1]==6];need(len(dynamic)==1,'one dynamic table')
    dynamic=dynamic[0];need(dynamic[9]==16 and dynamic[6]<len(table),'selected dynamic layout')
    strings=table[dynamic[6]];need(strings[1]==3,'dynamic string table')
    entries=[struct.unpack_from('<qQ',source,i) for i in range(dynamic[4],dynamic[4]+dynamic[5],16)]
    paths=[value for tag,value in entries if tag in (15,29)];need(len(paths)==1,'one library RPATH/RUNPATH')
    start=strings[4]+paths[0];old=cstring(source,start);replacement=(prefix.rstrip('/')+'/lib64').encode()
    need(old==b':'*16 and replacement==b'/usr/local/lib64','exact retained CMake padding and install prefix')
    expected=bytearray(source);expected[start:start+len(old)]=replacement
    return bytes(expected),dict(offset=start,old=old.decode(),new=replacement.decode())

def exports(raw):
    table=sections(raw);dynamic=[s for s in table if s[1]==11];need(len(dynamic)==1,'one dynamic symbol table')
    symbols=dynamic[0];need(symbols[9]==24 and symbols[6]<len(table),'selected dynamic symbol layout')
    strings=table[symbols[6]];names=raw[strings[4]:strings[4]+strings[5]];result={}
    for offset in range(symbols[4],symbols[4]+symbols[5],24):
        name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,offset)
        if not name or not index:continue
        text=cstring(names,name).decode();result.setdefault(text,[]).append(dict(kind=info&15,binding=info>>4,visibility=other&3,size=size))
    return result

def cache(path):
    result={}
    for line in path.read_text().splitlines():
        if line.startswith(('#','//')) or '=' not in line or ':' not in line.split('=',1)[0]:continue
        key,value=line.split('=',1);result[key.split(':',1)[0]]=value
    return result

def validate(build,stage,roots,source_root,source_tuple,prefix='/usr/local'):
    for relative,row in source_tuple['accepted_library_inputs'].items():
        raw=(source_root/relative).read_bytes()
        need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'accepted library source/ABI input '+relative)
    values=cache(build/'CMakeCache.txt')
    expected=dict(IHK_ENABLE_RUST_WHOLE_LIBRARY='ON',IHKLIB_USE_QUALIFIED_EXTERNAL_ARCHIVE='OFF',IHK_ALLOW_CLI_C_FALLBACK='OFF',IHK_USER_RUSTC='/nightly/bin/rustc',CMAKE_C_COMPILER='/usr/bin/cc',CMAKE_INSTALL_PREFIX=prefix)
    need(all(values.get(k)==v for k,v in expected.items()),'unchanged default source-produced supported cache')
    need(values.get('WITH_KRM') in (None,'OFF') and values.get('ENABLE_KRM_WORKAROUND')=='OFF','retained KRM-free ABI')
    user=build/'ihk/linux/user';source=(user/'libihk.so').read_bytes()
    need(len(source)==PROVIDER_BYTES and hashlib.sha256(source).hexdigest()==PROVIDER_SHA,'exact accepted canonical-source SDK provider')
    recipe=user/'rust/whole70';receipt=json.loads((recipe/'producer-receipt.json').read_bytes())
    need(receipt['status']=='PASS_REAL_HEADERS_AND_ONE_RUST_STATICLIB_BUILD_ONLY' and receipt['C_runtime_TU'] is False
         and len(receipt['commands'])==10 and all(row['returncode']==0 for row in receipt['commands'])
         and receipt['stat_cfg']=='ihklib_stat_abi_stat' and receipt['native_static_libs']==NATIVE,'retained actual producer/header tuple')
    link=shlex.split((user/'CMakeFiles/ihklib.dir/link.txt').read_text())
    archive=[x for x in link if x.endswith('libihklib_whole70.a')]
    need(len(archive)==1 and '/retained/' not in archive[0] and 'rust/whole70' in archive[0]
         and not any(x.endswith('.o') for x in link),'Rust archive only; no C runtime object')
    need('-Wl,-z,defs' in link and '-Wl,--gc-sections' in link
         and set(x.split('=',1)[1] for x in link if x.startswith('-Wl,--undefined='))==set(roots['functions'])|set(roots['data']), 'strict full76 provider roots')
    buildmake=(user/'CMakeFiles/ihklib.dir/build.make').read_text()
    need('ihklib.c' not in buildmake,'selected library graph contains no project C body')
    install=(user/'cmake_install.cmake').read_text()
    need('CMAKE_INSTALL_COMPONENT STREQUAL "ihklib_runtime"' in install,'library runtime component generated')
    installed=stage/prefix.lstrip('/')/'lib64/libihk.so';need(installed.is_file() and not installed.is_symlink(),'installed library file')
    wanted,rpath=installed_bytes(source,prefix);actual=installed.read_bytes();need(actual==wanted,'only exact CMake RPATH mutation permitted')
    symbols=exports(actual)
    need(len(roots['functions'])==70 and len(roots['data'])==6 and set(roots['data'])==DATA,'exact ABI provider manifest')
    for name in roots['functions']+roots['data']:
        need(name in symbols and len(symbols[name])==1,'unique public provider '+name)
        symbol=symbols[name][0];need(symbol['binding']==1 and symbol['visibility']==0 and symbol['kind']==(1 if name in DATA else 2),'public symbol ABI kind '+name)
    return dict(status='PASS_DEFAULT_GRAPH_AND_LIBRARY_COMPONENT_INSTALL_ONLY',source_sha256=PROVIDER_SHA,installed_sha256=hashlib.sha256(actual).hexdigest(),allowed_RPATH_change=rpath,function_providers=70,data_providers=6,compiler_commands_executed=0,library_API_calls=0,native=False,whole_M15=False,full_install=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--roots',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--source-tuple',type=Path,required=True);a=p.parse_args()
    print(json.dumps(validate(a.build,a.stage,json.loads(a.roots.read_bytes()),a.source,json.loads(a.source_tuple.read_bytes())),sort_keys=True,indent=2))
if __name__=='__main__':main()
