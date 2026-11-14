"""Source/mock tests only. Synthetic retained bytes never count as runtime evidence."""
import copy, hashlib, importlib.util, json, os, stat, struct, tempfile, unittest
from pathlib import Path
from unittest import mock
HERE=Path(__file__).resolve().parent/'fixtures/application-collector-v1/linux-sealed-v1/adverse-v1'
def load(name):
    spec=importlib.util.spec_from_file_location('test_adverse_'+name,HERE/(name+'.py')); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
p=load('prepare'); oracle=load('oracle'); build=load('build_owner'); profile=load('root_profile')
def save(path,value): path.write_text(json.dumps(value,sort_keys=True)+'\n')
def fixture(root,case):
    """Explicit synthetic production-shaped records with real retained unit files."""
    for name in ('collection','outer','inputs','cwd'): (root/name).mkdir()
    n,status,failure,error,sig=oracle.EXPECTED[case]; ready=n==384
    exe=b'SYNTHETIC-UNIT-ELF-BYTES'; manifest=b'SYNTHETIC-UNIT-MANIFEST\n'
    wire=p.reviewed('run_collector_tests.py').request_wire(root/'inputs/fixture',root/'cwd',None,
             [b'literal-app',b'stdin-devnull'],[],manifest,exe,b'',b'x'*16)
    for name,raw in [('fixture',exe),('selected-inputs.json',manifest),('request.bin',wire)]: (root/'inputs'/name).write_bytes(raw)
    cwd=(root/'cwd').stat(); words=[0]*48; words[:18]=[0x314c4341,1,1,1,0,102,101,102,102,0,0,0,0,1,0,18,cwd.st_dev,cwd.st_ino]
    words[18:31]=[stat.S_IFCHR|0o666,1,3,stat.S_IFIFO|0o600,2,4,stat.S_IFIFO|0o600,2,5,3,6,15,0]
    words[31:38]=[0,1,1,0,0,0,1]
    events=[{'event':'collector-start','pid':101,'monotonic_ns':100},
            {'event':'child-created','pid':102,'startticks':20,'monotonic_ns':210},
            {'event':'leader-waitable','pid':102,'monotonic_ns':300},
            {'event':'actual-reap','pid':102,'raw_wait_status':0,'monotonic_ns':410},
            {'event':'collector-finish','first_failure':failure,'monotonic_ns':550}]
    data={'request.bin':wire,'selected-inputs.bin':manifest,'argv.nul':b'literal-app\0stdin-devnull\0','env.nul':b'',
          'events.jsonl':b''.join((json.dumps(x)+'\n').encode() for x in events),'executable.verified.bin':exe,
          'stdout.bin':b'DEVNULL\n' if ready else b'','stderr.bin':oracle.WITNESS[case] if not ready else b'',
          'setup.bin':struct.pack('<48Q',*words)[:n]}
    artifacts=[]
    for name in oracle.NAMES:
        if name is None: artifacts.append(None); continue
        raw=data[name]; (root/'collection'/name).write_bytes(raw)
        artifacts.append({'path':name,'attempted_name':name,'created':True,'fd_available':True,'creation_errno':0,'fd_errno':0,
                          'seen_bytes':len(raw),'stored_bytes':len(raw),'limit_bytes':65536,'truncated':False,'io_error':False,'sha256':oracle.digest(raw)})
    desired={'role':1,'request_profile':1,'uid':0,'gid':0,'group':0,'umask':18,'argc':2,'envc':0,'stdin_mode':0,
             'case_id_hex':b'infrastructure.collector'.hex(),'source_selector_hex':os.fsencode(root/'inputs/fixture').hex(),
             'cwd_hex':os.fsencode(root/'cwd').hex(),'stdin_selector_hex':b'/dev/null'.hex(),'attempt_id_hex':(b'x'*16).hex(),'selected_inputs_sha256':oracle.digest(manifest)}
    r={'schema_version':1,'kind':'linux-sealed-infrastructure-collection','status':status,'first_failure':failure,
       'first_failure_errno':error,'collector_interruption_signal':sig,'application_acceptance':False,'transport_acceptance':False,
       'backend_enabled':False,'request_valid':True,'child_created':True,'cleanup_complete':True,'group_identity_pinned':True,
       'owned_records_omitted':0,'owned_children':[],'setup_ready_record':ready,'setup_validated':ready,'setup_error_record':False,
       'post_exec_backing_observed':ready,'streams':{'stdout_eof':True,'stderr_eof':True,'setup_eof':True},'artifacts':artifacts,
       'stdin':{'artifact':None,'verified':False},'collector_pid':101,'linux_child':{'pid':102,'ppid':101,'startticks':20,
       'identity_observed':True,'reaped':True,'raw_wait_status':0,'wait':{'exited':True,'signaled':False,'exit_code':0,'signal':None,'core_dumped':False}},
       'desired':desired,'setup_words':words if ready else [0]*48,'executable':{'sealed_backing':{'device':3,'inode':6},'seals':15},
       'devnull_identity':{'mode':stat.S_IFCHR|0o666,'device':1,'inode':3},'preparation_start_ns':100,'preparation_deadline_ns':120000000100,
       'process_start_ns':200,'process_deadline_ns':10000000200,'completion_observed_ns':290,'cleanup_start_ns':400,
       'cleanup_deadline_ns':15000000400,'cleanup_finished_ns':500,'first_failure_monotonic_ns':350 if sig else 520}
    outer={'status':'COMPLETED','cleanup_complete':True,'raw_wait_status':0 if case=='control' else 256,
           'process':{'pid':101,'starttime_ticks':10},'streams':{}}
    for name in ('stdout','stderr'):
        raw=oracle.WITNESS[case] if sig and name=='stderr' else b''; (root/'outer'/(name+'.bin')).write_bytes(raw)
        outer['streams'][name]={'eof':True,'discarded_observed_bytes':0,'truncated':False,'bytes_retained':len(raw),'bytes_observed':len(raw),'artifact':{'sha256':oracle.digest(raw)}}
    save(root/'collection/report.json',r); save(root/'outer/report.json',outer); return r,outer
def change_artifact(root,r,name,raw):
    (root/'collection'/name).write_bytes(raw)
    row=next(x for x in r['artifacts'] if x is not None and x['path']==name)
    row.update(sha256=oracle.digest(raw),seen_bytes=len(raw),stored_bytes=len(raw)); save(root/'collection/report.json',r)

def build_fixture(root):
    """Synthetic compiler transcript; no executable/compiler is invoked."""
    prefix=Path('/work/build')
    def retained(relative,raw):
        target=root/relative; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
        return {'path':str(prefix/relative),'size':len(raw),'sha256':p.digest(raw)}
    record={'status':'PASS_ADVERSE_BUILD_ONLY','application_acceptance':False,'backend_enabled':False,
            'image':p.reviewed('root_orchestrator.py').IMAGE_ID,
            'selectors':dict(p.CASES),'inputs':[],'tools':[],'loader_dependencies':[],
            'compiler_dependencies':[],'compiled_outputs':[],'commands':[]}
    for name in build.SOURCE_PINS:
        src=p.SOURCE.parent.parent/name if name.startswith('request.') else p.SOURCE.parent/name
        relative='source/'+name if name.startswith('request.') else 'source/linux-sealed-v1/'+name
        data=p.read(src); item=retained(relative,data)
        record['inputs'].append({'original':dict(item,path='/workspace/'+str(src.relative_to(p.REPO))),'retained':item})
    source=p.read(p.SOURCE); generated=p.generate(source)
    for name,raw in [('adverse-collector.c',generated),('source.collector.c',source),('inject.h',p.read(HERE/'inject.h')),
                     ('collector.patch',p.read(HERE/'collector.patch')),('generated.diff',p.generated_diff(source,generated))]:
        record['inputs'].append({'retained':retained('source/linux-sealed-v1/'+name,raw)})
    pins={}
    for group,directory,original,names in [('tools','tools','/usr/bin',('gcc','readelf','objdump')),
                                         ('loader_dependencies','loaders','/usr/lib64',('libc.so.6','ld-linux-x86-64.so.2'))]:
        pins[group]={}
        for name in names:
            data=('SYNTHETIC-UNIT-'+name).encode(); item=retained(directory+'/'+name,data)
            pins[group][name]=(len(data),p.digest(data))
            row={'original':dict(item,path=original+'/'+name),'retained':item}
            if group=='loader_dependencies': row['logical']=dict(item,path='/lib64/'+name)
            record[group].append(row)
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','TZ':'UTC','TMPDIR':'/work/build/tmp'}
    def command(label,argv):
        size,sha=pins['tools'][Path(argv[0]).name]
        report={'status':'COMPLETED','raw_wait_status':0,'cleanup_complete':True,'argv':argv[:],
                'cwd':str(prefix),'env':dict(env),'executable_path':argv[0],
                'executable':{'path':argv[0],'size':size,'sha256':sha},'timeout_seconds':120.0,
                'cleanup_timeout_seconds':15.0,'stdout_limit_bytes':8*1024**2,'stderr_limit_bytes':8*1024**2,
                'payload_monotonic_started':100.0,'payload_monotonic_deadline':220.0,
                'payload_completion_observed_monotonic':101.0,'streams':{}}
        for stream in ('stdout','stderr'):
            report['streams'][stream]={'artifact':retained(label+'-collection/'+stream+'.bin',b''),
                     'eof':True,'truncated':False,'discarded_observed_bytes':0,'bytes_retained':0,'bytes_observed':0}
        record['commands'].append({'label':label,'argv':argv,'environment':dict(env),'collection':report})
    command('compiler-version',['/usr/bin/gcc','--version'])
    for name in ['request','sha256','fixture']+list(p.CASES):
        src='source/request.c' if name=='request' else 'source/linux-sealed-v1/'+('adverse-collector.c' if name in p.CASES else name+'.c')
        flags=['-std=c11','-D_GNU_SOURCE','-O2','-g','-Wall','-Wextra','-Werror','-fno-pie']
        if name in p.CASES: flags+=['-DM02_ADVERSE_TEST_ONLY=1','-DM02_ADVERSE_CASE='+str(p.CASES[name])]
        command('compile-'+name,['/usr/bin/gcc']+flags+['-MD','-MF',str(prefix/(name+'.d')),'-c',str(prefix/src),'-o',str(prefix/(name+'.o'))])
        record['compiled_outputs'] += [retained(name+'.o',b'SYNTHETIC-OBJECT'),retained(name+'.d',(str(prefix/(name+'.o'))+': '+str(prefix/src)+'\n').encode())]
    for name,objects in [('fixture',['fixture'])]+[('linux-collector-adverse-'+case,['request','sha256',case]) for case in p.CASES]:
        command('link-'+name,['/usr/bin/gcc','-no-pie']+[str(prefix/(obj+'.o')) for obj in objects]+['-Wl,-Map='+str(prefix/(name+'.map')),'-o',str(prefix/name)])
        command('elf-'+name,['/usr/bin/readelf','-h','-l','-d',str(prefix/name)])
        command('disassembly-'+name,['/usr/bin/objdump','-d',str(prefix/name)])
        record['compiled_outputs'] += [retained(name,b'SYNTHETIC-ELF'),retained(name+'.map',b'SYNTHETIC-MAP')]
    for relative in ['source/request.c']+['source/linux-sealed-v1/'+name for name in ('sha256.c','fixture.c','adverse-collector.c')]:
        data=(root/relative).read_bytes()
        record['compiler_dependencies'].append({'original':{'path':str(prefix/relative),'size':len(data),'sha256':p.digest(data)},
                    'retained':retained('compiler-inputs/work/build/'+relative,data)})
    return record,pins

class AdversePacketTests(unittest.TestCase):
    def test_fixed_packet_source_header_patch(self):
        packet=p.packet(HERE/'packet.json'); self.assertFalse(packet['application_acceptance']); self.assertEqual(list(p.CASES.values()),[0,1,2,3])
        source=p.read(p.SOURCE); generated=p.generate(source)
        self.assertTrue(p.patch_is_applicable(source,generated,p.read(HERE/'collector.patch')))
        self.assertEqual(generated.count(b'm02_adverse_child_boundary(setup_fd, words);'),1)
        self.assertEqual(generated.count(b'm02_adverse_completed_wait_hook'),1)
        with self.assertRaises(ValueError): p.generate(source+b'\n')
        self.assertFalse(p.patch_is_applicable(source,generated,b'bad patch\n'))
        with mock.patch.object(p,'EXPECTED_PACKET','0'*64):
            with self.assertRaises(ValueError): p.packet(HERE/'packet.json')
        original=p.read
        for name in ('collector.patch','inject.h'):
            def tampered(path,maximum=16*1024**2): return original(path,maximum)+b'\n' if Path(path).name==name else original(path,maximum)
            with mock.patch.object(p,'read',side_effect=tampered):
                with self.assertRaises(ValueError): p.packet(HERE/'packet.json')
    def test_guarded_selector_zero_and_unknown(self):
        header=p.read(HERE/'inject.h').decode()
        for text in ('#ifndef M02_ADVERSE_TEST_ONLY','#ifndef M02_ADVERSE_CASE','#if M02_ADVERSE_CASE < 0 || M02_ADVERSE_CASE > 3','M02_ADVERSE_CASE == 0 || M02_ADVERSE_CASE == 3','M02_ADVERSE_CASE != 3','raise(SIGTERM)'):
            self.assertIn(text,header)
        for selector in range(4): self.assertEqual(build.flags(selector)[-2:],['-DM02_ADVERSE_TEST_ONLY=1','-DM02_ADVERSE_CASE='+str(selector)])
        for selector in (-1,4,True,None,'0'):
            with self.assertRaises(ValueError): build.flags(selector)
    def test_prepare_fresh_output_and_reuse_rejected(self):
        import sys
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'prepared'; argv=['prepare.py','--packet',str(HERE/'packet.json'),'--attempt-root',str(out)]
            with mock.patch.object(sys,'argv',argv): p.main()
            record=json.loads((out/'prepare.json').read_bytes()); self.assertEqual(record['status'],'PREPARED_NOT_EXECUTED')
            self.assertEqual(record['generated']['sha256'],p.digest((out/'adverse-collector.c').read_bytes()))
            with mock.patch.object(sys,'argv',argv):
                with self.assertRaises(ValueError): p.main()
    def test_whole_profile_exact_modes_under_private_umask(self):
        with tempfile.TemporaryDirectory() as d:
            synthetic=Path(d)/'synthetic-build'; synthetic.mkdir()
            names=['fixture']+['linux-collector-adverse-'+case for case in p.CASES]
            for name in names: (synthetic/name).write_bytes(b'SYNTHETIC-UNIT-ELF')
            save(synthetic/'build-record.json',{'synthetic':True})
            for mode in ('build','run'):
                root=Path(d)/mode; previous=os.umask(0o077)
                try:
                    with mock.patch.object(profile,'verify_build',return_value={'synthetic':True}):
                        _,manifest=profile.create(HERE/'packet.json',root,mode,synthetic/'build-record.json','b'*32)
                finally: os.umask(previous)
                expected=set(profile.FILES)|{'inputs.json'}
                if mode=='run': expected.update(names+['build-record.json'])
                self.assertEqual(set(x.name for x in (root/'inputs').iterdir()),expected)
                for name,row in manifest['files'].items():
                    target=root/'inputs'/name
                    self.assertEqual(stat.S_IMODE(target.stat().st_mode),row['mode'])
                    self.assertEqual(p.digest(target.read_bytes()),row['sha256'])
                self.assertEqual(stat.S_IMODE((root/'inputs/inputs.json').stat().st_mode),0o644)
                self.assertEqual(stat.S_IMODE((root/'plan.json').stat().st_mode),0o600)
                for name in ('','work','work/tmp'): self.assertEqual(stat.S_IMODE((root/name).stat().st_mode),0o700)
    def test_build_transcript_exact_matrix_and_mutations(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); record,pins=build_fixture(root); path=root/'build-record.json'
            original_local=profile.local
            def selected(name): return build if name=='build_owner' else original_local(name)
            mutations=[('image identity',lambda r:r.update(image='sha256:'+'0'*64)),
                       ('link args',lambda r:r['commands'][8]['argv'].insert(2,'-static')),
                       ('readelf args',lambda r:r['commands'][9]['argv'].append('-S')),
                       ('objdump args',lambda r:r['commands'][10]['argv'].__setitem__(1,'-D')),
                       ('argv executable',lambda r:r['commands'][0]['argv'].__setitem__(0,'/bin/false')),
                       ('removed input',lambda r:r['inputs'].pop()),
                       ('original input',lambda r:r['inputs'][0]['original'].update(path='/workspace/other.c')),
                       ('cwd',lambda r:r['commands'][0]['collection'].update(cwd='/work')),
                       ('deadline',lambda r:r['commands'][0]['collection'].update(payload_monotonic_deadline=221.0)),
                       ('timeout',lambda r:r['commands'][0]['collection'].update(timeout_seconds=121.0)),
                       ('executable identity',lambda r:r['commands'][0]['collection']['executable'].update(sha256='0'*64)),
                       ('loader identity',lambda r:r['loader_dependencies'][0]['original'].update(sha256='0'*64)),
                       ('loader name',lambda r:r['loader_dependencies'][0]['original'].update(path='/usr/lib64/other.so')),
                       ('loader canonical alias',lambda r:r['loader_dependencies'][0]['original'].update(path='/lib64/libc.so.6')),
                       ('loader logical identity',lambda r:r['loader_dependencies'][0]['logical'].update(sha256='0'*64)),
                       ('loader logical path',lambda r:r['loader_dependencies'][0]['logical'].update(path='/usr/lib64/libc.so.6'))]
            with mock.patch.object(profile,'local',side_effect=selected), mock.patch.object(build,'TOOL_PINS',pins['tools']), mock.patch.object(build,'LOADER_PINS',pins['loader_dependencies']):
                save(path,record); self.assertEqual(profile.verify_build(path),record)
                for label,mutate in mutations:
                    with self.subTest(mutation=label):
                        changed=copy.deepcopy(record); mutate(changed); save(path,changed)
                        with self.assertRaises(ValueError): profile.verify_build(path)
                save(path,record); (root/'source/linux-sealed-v1/generated.diff').write_bytes(b'changed\n')
                with self.assertRaises(ValueError): profile.verify_build(path)
        self.assertIn("('generated.diff',p.generated_diff(source,generated))",p.read(HERE/'build_owner.py').decode())
    def test_loader_real_lib64_symlink_and_wrong_canonical(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); canonical=root/'usr/lib64'; canonical.mkdir(parents=True)
            (root/'lib64').symlink_to('usr/lib64',target_is_directory=True)
            for name in build.LOADER_PINS:
                raw=('SYNTHETIC-UNIT-'+name).encode(); (canonical/name).write_bytes(raw)
                expected=(len(raw),p.digest(raw)); dst=root/'retained'/name
                row=build.retain_loader(root/'lib64'/name,canonical/name,expected,dst)
                self.assertEqual(row,{'logical':{'path':str(root/'lib64'/name),'size':len(raw),'sha256':p.digest(raw)},
                                     'original':{'path':str(canonical/name),'size':len(raw),'sha256':p.digest(raw)},
                                     'retained':{'path':str(dst),'size':len(raw),'sha256':p.digest(raw)}})
                wrong=root/'wrong'/name; wrong.parent.mkdir(exist_ok=True); wrong.write_bytes(raw)
                with self.assertRaisesRegex(ValueError,'canonical path'):
                    build.retain_loader(root/'lib64'/name,wrong,expected,root/'rejected'/name)
                self.assertFalse((root/'rejected'/name).exists())
    def test_four_real_layout_synthetic_positive_records(self):
        for case in p.CASES:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as d:
                root=Path(d); r,_=fixture(root,case); self.assertIsNone(r['artifacts'][6]); self.assertTrue(oracle.validate_retained(root,case))
    def test_required_metadata_negative_matrix(self):
        mutations=[lambda r,o:r.update(status='COMPLETED'),lambda r,o:r.update(first_failure_errno=0),
                   lambda r,o:r.update(cleanup_complete=False),lambda r,o:r.update(group_identity_pinned=False),
                   lambda r,o:r['linux_child'].update(raw_wait_status=256),lambda r,o:o.update(raw_wait_status=0),
                   lambda r,o:r['linux_child'].update(startticks=0),lambda r,o:o['process'].update(pid=999),
                   lambda r,o:r['streams'].update(setup_eof=False),lambda r,o:o['streams']['stderr'].update(eof=False),
                   lambda r,o:r.update(completion_observed_ns=r['process_deadline_ns']),
                   lambda r,o:r.update(cleanup_finished_ns=r['cleanup_deadline_ns']),
                   lambda r,o:r.update(first_failure_monotonic_ns=1),lambda r,o:r['desired'].update(attempt_id_hex='00'*16),
                   lambda r,o:r['artifacts'].__setitem__(6,{}),lambda r,o:r.update(owned_records_omitted=1)]
        for index,mutate in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as d:
                root=Path(d); r,o=fixture(root,'interrupt-completed-wait'); mutate(r,o)
                save(root/'collection/report.json',r); save(root/'outer/report.json',o)
                self.assertFalse(oracle.validate(root,'interrupt-completed-wait'))
    def test_required_retained_byte_negative_matrix(self):
        cases=[('partial-setup','setup.bin',b'x'*382),('partial-setup','setup.bin',b'x'*383),
               ('partial-setup','stderr.bin',b''),('missing-setup','stderr.bin',b''),
               ('interrupt-completed-wait','stdout.bin',b'DEVNULL\\n'),('control','stdout.bin',b''),
               ('control','request.bin',b'bad'),('control','events.jsonl',b'{}\n')]
        for case,name,raw in cases:
            with self.subTest(case=case,name=name), tempfile.TemporaryDirectory() as d:
                root=Path(d); r,_=fixture(root,case); change_artifact(root,r,name,raw); self.assertFalse(oracle.validate(root,case))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); fixture(root,'interrupt-completed-wait'); (root/'outer/stderr.bin').write_bytes(b'')
            self.assertFalse(oracle.validate(root,'interrupt-completed-wait'))
    def test_selector_zero_cannot_pass_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); r,o=fixture(root,'control'); r.update(status='SETUP_ERROR'); o.update(raw_wait_status=256)
            save(root/'collection/report.json',r); save(root/'outer/report.json',o); self.assertFalse(oracle.validate(root,'control'))
    def test_artifact_hash_and_symlink_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); fixture(root,'control'); (root/'collection/stdout.bin').write_bytes(b'DEVNULL!\n'); self.assertFalse(oracle.validate(root,'control'))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); fixture(root,'control'); path=root/'collection/stdout.bin'; path.unlink(); path.symlink_to(root/'inputs/fixture'); self.assertFalse(oracle.validate(root,'control'))
    def test_owner_negative_boundaries_without_execution(self):
        owner=p.reviewed('root_orchestrator.py')
        self.assertFalse(owner.release_lock_allowed({'absence_verified':False},0))
        self.assertFalse(owner.release_lock_allowed({'absence_verified':True},256))
        self.assertTrue(owner.release_lock_allowed({'absence_verified':True},0))
        config={'container_id':'a'*64,'name':'mckernel-collector-'+'b'*32,'nonce':'b'*32}
        with self.assertRaises(ValueError): owner.owned({'Id':'c'*64},config)
        for field in ('Config','HostConfig'):
            with self.assertRaises((ValueError,KeyError,TypeError)): owner.full_inspect({field:{}},config,{})
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'record.json'; save(path,{'status':'PREPARED_NOT_EXECUTED'})
            with self.assertRaises((ValueError,KeyError)): profile.verify_build(path)
    def test_all_executable_modules_import_without_side_effects(self):
        for name in ('run','build_owner','root_profile','root_inside','root_orchestrator'): self.assertIsNotNone(load(name).main if name not in ('root_profile',) else load(name).create)

if __name__=='__main__': unittest.main(failfast=True)
