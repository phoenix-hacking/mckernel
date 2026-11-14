from pathlib import Path
b=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1'); p=Path(__file__).parent
owner=(b/'sdk21-nonheld13-owner-source-1/sdk13_compile_image_owner.v8.py').read_text()
driver=(b/'sdk21-nonheld13-owner-source-1/sdk13_four_command_driver.v4.py').read_text()
validator=(b/'sdk21-nonheld13-input-validation-source-1/sdk13_data32_input_validation.py').read_text()
def once(s,old,new):
    if s.count(old)!=1: raise ValueError('unexpected predecessor: '+old[:80])
    return s.replace(old,new,1)
driver=once(driver,"PROFILE_SHA256 = 'e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3'","PROFILE_SHA256 = None  # SOURCE ONLY: must be replaced by independently reviewed profile hash")
driver=once(driver,"STAGES = ('Rust object plus depinfo', 'GCC14 generic C object plus depfile',\n          'GCC14 architecture C object plus depfile', 'GNU ld 2.41 raw eleven-input image')","STAGES = ('Configure ON composite', 'Post-generation verification')")
driver=once(driver,"if len(commands) != 4 or tuple(x['stage'] for x in commands) != STAGES:","if PROFILE_SHA256 is None or len(commands) != 2 or tuple(x['stage'] for x in commands) != STAGES:")
driver=once(driver,"if any(x['cwd'] != CWD or not isinstance(x['argv'], list) or not x['argv'] or","if any(x['cwd'] != '/work' or not isinstance(x['argv'], list) or not x['argv'] or")
driver=once(driver,"'cwd': CWD,\n                                                            'start_utc': stamp}","'cwd': command['cwd'],\n                                                            'start_utc': stamp}")
driver=once(driver,"child = subprocess.Popen(command['argv'], cwd=CWD, stdin=subprocess.DEVNULL,","child = subprocess.Popen(command['argv'], cwd=command['cwd'], stdin=subprocess.DEVNULL,")
driver=once(driver,"'artifact_validation': 'NOT_PERFORMED',","'artifact_validation': 'POST_GENERATION_STAGE_EXITED_ZERO_ONLY',")
# Preserve old mount/source verification; it cannot accept successor until explicitly adapted.
driver=once(driver,'def main():\n',"def main():\n    raise RuntimeError('SOURCE_ONLY: successor profile, mount validation and owner admission are unbound')\n")
(p/'driver.successor.py').write_text(driver)
# v8 owner custody remains byte-identical except disabled entry and result acceptance.
owner=once(owner,'    def run(self):\n        r=self.request\n        _fail(\'physical_acceptance\' not in r,\'SDK13 launch request must not contain future physical acceptance\')',"    def run(self):\n        raise OwnerError('SOURCE_ONLY: configure successor has no release or live bindings')\n        r=self.request\n        _fail('physical_acceptance' not in r,'SDK13 launch request must not contain future physical acceptance')")
start=owner.index('def _sdk13_driver_result(bound,request,manifest):');end=owner.index('\n\nSDK13_EFFECT_STOP_SIGNALS=',start)
replacement='''def _sdk13_driver_result(bound,request,manifest):
    evidence=Path(bound['work'])/'sdk13-driver-evidence'
    proof=_load_json(_safe_regular(evidence/'precompiler-view.json','configure mounted view proof'),'configure mounted view proof')
    _fail(proof.get('status')=='PASS_EFFECTIVE_MOUNTS_SOURCE_ENV' and
          proof.get('profile_sha256')==SDK13_PROFILE_SHA and proof.get('driver_sha256')==SDK13_DRIVER_SHA and
          proof.get('source_map_sha256')==request['source_map_sha256'] and
          proof.get('mount_manifest_sha256')==manifest['sha256'], 'configure mounted view differs')
    result=_load_json(_safe_regular(evidence/'result.json','configure driver result'),'configure driver result')
    _fail(result.get('status')=='COMMANDS_EXITED_ZERO' and
          result.get('artifact_validation')=='POST_GENERATION_STAGE_EXITED_ZERO_ONLY', 'configure stages incomplete')
    _fail(len(bound['commands'])==2, 'configure stage count differs')
    for i,command in enumerate(bound['commands'],1):
        intent=_load_json(_safe_regular(evidence/('stage-%d-intent.json'%i),'configure intent'),'configure intent')
        row=_load_json(_safe_regular(evidence/('stage-%d-result.json'%i),'configure stage'),'configure stage')
        _fail(intent.get('argv')==command['argv'] and intent.get('cwd')==command['cwd'] and
              row.get('stage')==command['stage'] and row.get('returncode')==0 and
              row.get('direct_wait_completed') is True and row.get('timed_out') is False and
              not row.get('error'), 'configure stage result differs')
        for suffix in ('stdout','stderr'):
            _safe_regular(evidence/('stage-%d.%s'%(i,suffix)),'configure capture')
    outputs=[]
    for raw in ('/work/output/build/tmp.resolve_MODULES_END/driver.ko',
                '/work/output/build/CMakeCache.txt','/work/output/build/compile_commands.json'):
        path=_safe_regular(Path(bound['work'])/Path(raw).relative_to('/work'),'configure output')
        _fail(path.stat().st_size>0,'configure output empty')
        outputs.append({'path':str(path),'bytes':path.stat().st_size,'sha256':_sha256(path)})
    return outputs
'''
owner=owner[:start]+replacement+owner[end:];(p/'owner.successor.py').write_text(owner)
# Replace only proposed selector/mount gates; full source collection is deliberately disabled.
start=validator.index('def _mount_graph(mounts):');end=validator.index('\ndef _collect(',start)
replacement='''def _mount_graph(mounts):
    _require(isinstance(mounts,list) and len(mounts)>=4, 'mount count')
    targets=[]
    for i,row in enumerate(mounts):
        _require(isinstance(row,(tuple,list)) and len(row)==3, 'mount shape')
        host,target,readonly=row
        _require(isinstance(host,str) and isinstance(target,str) and type(readonly) is bool, 'mount row shape')
        p=PurePosixPath(target)
        _require(p.is_absolute() and str(p)==target and '..' not in p.parts, 'mount target invalid')
        _require(target not in targets, 'duplicate mount target')
        _require((i==0 and target=='/work' and not readonly) or (i>0 and readonly), 'unexpected writable mount')
        for prior in targets:
            _require(not (PurePosixPath(prior) in p.parents and prior not in ('/src','/work')), 'unsupported overlap')
            _require(not (p in PurePosixPath(prior).parents), 'mount parent masks child')
        targets.append(target)
    _require({'/work','/src','/src/kernel/rust','/nightly','/out'}<=set(targets), 'required mount absent')

def _selectors(profile, proposal):
    commands=profile['commands']
    _require(commands==proposal['commands'] and len(commands)==2, 'command proposal differs')
    _require([c['stage'] for c in commands]==['Configure ON composite','Post-generation verification'], 'stage order differs')
    _require(all(c.get('cwd')=='/work' and isinstance(c.get('argv'),list) and c['argv'] and
                 all(isinstance(x,str) and x and '\\0' not in x for x in c['argv']) for c in commands), 'bad command schema')
    a=commands[0]['argv']
    _require(a[:7]==['/usr/bin/cmake','-S','/src','-B','/work/output/build','-G','Unix Makefiles'], 'configure argv differs')
    _require(a.count('-DMCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL=ON')==1 and a.count('-DKERNEL_DIR=/out/build')==1, 'ON or kernel selector differs')
    for flag in ('UNAME_R','MCKERNEL_M14_EXPECTED_UNAME_R','MCKERNEL_M14_EXPECTED_MAP_KERNEL_START',
                 'MCKERNEL_M14_EXPECTED_MAKE_SHA256','KBUILD_MAKE_FLAGS','MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS'):
        _require(sum(x.startswith('-D'+flag+'=') and len(x)>len('-D'+flag+'=') for x in a)==1, 'missing or duplicate '+flag)
    _require(commands[1]['argv'][:4]==['/usr/bin/python3','-I','-B','/src/scripts/verify_m14_elf.py'], 'separate verifier differs')
    _require(not any(any(x in arg for x in ('FULL28','WITNESS','EXECVE_TRANSFER','TERMINATE_HOST','DIRECT_TID')) for c in commands for arg in c['argv']), 'held selector')
'''
validator=validator[:start]+replacement+validator[end:];validator=once(validator,'def _collect(request, profile_path, request_path, source_map_path):\n',"def _collect(request, profile_path, request_path, source_map_path):\n    raise ValueError('SOURCE_ONLY: configure source closure and live bindings are unbound')\n")
(p/'validator.successor.py').write_text(validator)
