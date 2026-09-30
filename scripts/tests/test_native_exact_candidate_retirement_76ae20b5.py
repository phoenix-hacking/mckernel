#!/usr/bin/env python3
"""Source-only checks for the 76ae20b5 disk-candidate retirement boundary."""
import copy, hashlib, importlib.util, json, os, re, tempfile, unittest
from unittest import mock
from pathlib import Path
ROOT=Path(__file__).parents[2]
PACKET=ROOT/'docs/verification/evidence/native-exact-candidate-retirement-76ae20b5-1.py'
spec=importlib.util.spec_from_file_location('retire_76ae20b5', PACKET)
M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

class RetirementPacketTests(unittest.TestCase):
    def test_draft_is_fail_closed_and_exactly_bound(self):
        self.assertEqual(M.RELEASE_SHA256, 'RELEASE_HASH_REQUIRED')
        with self.assertRaisesRegex(M.Error, 'DRAFT_NOT_RELEASED'):
            M.draft_guard()
        self.assertEqual(M.MAIN, '76ae20b523f57dee8e0fb1fb834caf5443f9f671')
        self.assertEqual(M.IHK, '3114d9e7101ad52030eb3effa849a5c108972a1f')
        self.assertEqual(M.CANDIDATE, '/dev/shm/mckernel-exact-candidate-76ae20b5-1')
        self.assertEqual(M.BACKUP, '/dev/shm/mckernel-exact-metadata-backup-76ae20b5-1')
        self.assertEqual(M.INV_SHA, '585fc0f5a4bca638d9684592fe61e52a3929490260fe0ad0c34d8df1ba3504fd')
        self.assertEqual(M.CAP_SHA, 'fd26f227fef7a850e013494600e32c51108375cb4137119b205136b24b41e3d7')
        self.assertEqual(M.ROUTING_COUNTS, {'main':7864,'ihk':1295})
        self.assertEqual(M.RETENTION_MEMBER_COUNT, 937)
        self.assertEqual(M.RETENTION_CAPSULE_REQUIRED, 922)
        self.assertEqual(M.PREPARATION_COMMIT, 'f5db92dfbdd76c06335177d09a350154c727f08e')
        self.assertEqual(M.PREPARATION_RELEASE_SHA, '0dad43e96598491fe8f7607758a2c9fa52a7b9501c07edfc6a57a15b97cec167')
        self.assertEqual(M.RECEIPT_SHA, 'cfd7b5d54918d59dde074476ef2475a739bfdcc0aabb5c39347242a7e413565b')
        self.assertEqual(M.SUCCESS_SHA, '9a1a4b0c6e98b9b09ef934962dbcd9dac7ed3d23e90104c1561d6a4953cc348c')
        self.assertEqual(M.SOURCE_CANDIDATE_ID, '26:58679')
        self.assertEqual(M.SOURCE_BACKUP_ID, '26:69465')
        self.assertEqual(M.PROTECTED_SEAL_ID, '1831:4849667')
        self.assertEqual(M.PROTECTED_SEAL_SHA256, '192f8fe161ee0e486b0c0532f64bc34bb0684da2b113d01d13dc4f4ba7bb1c2c')
        self.assertEqual(M.COPY_FAILURES.name, 'stability-native-exact-candidate-disk-copy-failures-76ae20b5-20260929-1.json')
        self.assertEqual(M.COPY_FAILURES_SHA256, 'f4ee6d4c458243c566a5c29fcc0023475d16df78170e111dfc110ddae51ca304')
        self.assertEqual(M.PROTECTED_DISK_CANDIDATE_ID, '1831:4194306')
        self.assertEqual(M.PROTECTED_DISK_BACKUP_ID, '1831:4204970')

    def test_sealed_corrupt_archive_is_not_a_retirement_target(self):
        text=PACKET.read_text()
        self.assertIn('stability-native-exact-candidate-retention-76ae20b5-20260929-2.inventory.json', text)
        self.assertIn('stability-native-exact-candidate-retention-76ae20b5-20260929-2.tar', text)
        self.assertNotIn(M.PROTECTED_DISK_CANDIDATE, M.CANDIDATE)
        self.assertNotIn(M.PROTECTED_DISK_BACKUP, M.BACKUP)
        self.assertNotIn(M.PROTECTED_DISK_CANDIDATE, '\n'.join(M.QUARANTINES))
        self.assertNotIn(M.PROTECTED_DISK_BACKUP, '\n'.join(M.QUARANTINES))
        self.assertIn('192f8fe161ee0e486b0c0532f64bc34bb0684da2b113d01d13dc4f4ba7bb1c2c',
                      (ROOT/'docs/verification/evidence/stability-native-exact-candidate-disk-validation-success-76ae20b5-20260929-1.json').read_text())

    def test_all_future_release_placeholders_block_before_root_admission(self):
        old=M.RELEASE_SHA256; old_inv=M.INV_SHA
        try:
            M.RELEASE_SHA256='a'*64
            M.INV_SHA='RETENTION_INVENTORY_REQUIRED'
            with self.assertRaisesRegex(M.Error, 'DRAFT_NOT_RELEASED'):
                M.draft_guard()
        finally: M.RELEASE_SHA256=old; M.INV_SHA=old_inv

    def test_target_and_protected_namespaces_are_disjoint(self):
        self.assertEqual(M.CANDIDATE, '/dev/shm/mckernel-exact-candidate-76ae20b5-1')
        self.assertEqual(M.BACKUP, '/dev/shm/mckernel-exact-metadata-backup-76ae20b5-1')
        self.assertTrue(all(x.startswith('/dev/shm/') for x in M.QUARANTINES))
        self.assertTrue(all(x not in M.QUARANTINES for x in (M.PROTECTED_DISK_CANDIDATE, M.PROTECTED_DISK_BACKUP)))
        self.assertEqual(M.EVIDENCE_PARENT, Path('/dev/shm'))
        self.assertNotEqual(M.EVIDENCE_PARENT, Path('/home/holden/mckernel-work/scratch'))

    def test_routing_counts_are_derived_from_real_manifest(self):
        import json
        d=json.loads((ROOT/'docs/verification/evidence/stability-native-exact-candidate-retention-76ae20b5-20260929-2.inventory.json').read_text())
        counts={'main':0,'ihk':0}
        for row in d['entries']:
            if row['classification']=='reconstructible' and row['type']!='directory':
                counts['ihk' if row['path'].startswith('ihk/') else 'main']+=1
        self.assertEqual(counts, M.ROUTING_COUNTS)

    def test_shared_exclusion_is_exclusive_and_never_steals(self):
        with tempfile.TemporaryDirectory() as d:
            old=(M.COMMON_EXCLUSION,M.LEGACY_EXCLUSIONS)
            try:
                M.COMMON_EXCLUSION=Path(d)/'common'; M.LEGACY_EXCLUSIONS=(Path(d)/'legacy1',Path(d)/'legacy2')
                release=self.release(d)
                with mock.patch.object(M.ExclusionLease,'_make_immutable'), mock.patch.object(M.ExclusionLease,'_flags',return_value=M.FS_IMMUTABLE_FL):
                    with M.SharedExclusions(release) as held:
                        held.assert_held()
                        with self.assertRaises(FileExistsError): M.SharedExclusions(release).__enter__()
                        self.assertTrue(all(x.parent_fd is not None for x in held.records))
                    self.assertTrue(all(x.fd is None and x.parent_fd is None for x in held.records))
                    self.assertTrue(all(p.exists() for p in held.paths))
            finally: M.COMMON_EXCLUSION,M.LEGACY_EXCLUSIONS=old

    def test_current_helper_and_observer_are_bound(self):
        self.assertEqual(M.HELPER.name, 'native_exact_candidate_retire.py')
        self.assertEqual(M.HELPER_SHA256, '704a3f5f8f2ab259af493b3fbc0dd5bf1d461b8a0d67301d2176052b520df54b')
        self.assertEqual(M.OBSERVER_SHA256, 'e81b9a654be747839880585935d3428cbdf084d25eb8a5295682a8371cb2803a')
        self.assertEqual(M.ARCHIVE_SHA256, '6a28184e13e4ddec3a5e2fe6229c618929df29f235901083d55918c8291ac06e')

    def test_packet_has_live_quarantine_observer_and_post_delete_hooks(self):
        text=PACKET.read_text()
        for token in ('observer_callback', 'docker_callback', 'live_gate', 'bind_delete_boundary',
                      'QUARANTINES', 'ExclusionLease', 'finalize', 'remove_root', 'root'):
            self.assertIn(token, text)
        self.assertIn('RENAME_NOREPLACE', text)

    def test_protected_identity_and_failure_archive_are_documented(self):
        success=(ROOT/'docs/verification/evidence/stability-native-exact-candidate-disk-validation-success-76ae20b5-20260929-1.json').read_text()
        self.assertIn('"sealed_identity": "1831:4849667"', success)
        self.assertIn('"sealed_sha256": "192f8fe161ee0e486b0c0532f64bc34bb0684da2b113d01d13dc4f4ba7bb1c2c"', success)
        self.assertTrue((ROOT/'docs/verification/evidence/stability-native-exact-candidate-disk-copy-failures-76ae20b5-20260929-1.json').exists())

    def release(self,d):
        st=os.stat(d)
        return {'boot_id':'test','exclusion_tombstone':{'parent_uid':st.st_uid,'parent_gid':st.st_gid,'parent_mode':st.st_mode&0o7777,'filesystem_device':st.st_dev}}

    def evidence(self):
        return [json.loads(p.read_text()) for p in (M.SUCCESS,M.RETENTION_SUCCESS,M.RECEIPT,M.COPY_FAILURES,M.INVENTORY)]

    def test_real_evidence_and_corrupt_member_are_bound(self):
        M.evidence_bindings(*self.evidence())
        M.verify_corrupt_capsule()

    def test_each_evidence_closure_rejection(self):
        originals=self.evidence()
        mutations=[(0,('status',),'PASS_PREPARATION_EVIDENCE_ONLY'),
                   (1,('source_commit',),'0'*40),(1,('execution','children_absent'),False),
                   (1,('verified_state','tmpfs_inventory_sha256'),'0'*64),
                   (2,('planner','returncode'),1),(2,('archive','descendants_absent'),False),
                   (2,('postflight','error'),'observer failed'),(2,('operational_exclusions_released',),False),
                   (2,('operational_exclusions',),[]),(3,('observed_divergence','tmpfs_sha256'),'0'*64)]
        for index,keys,value in mutations:
            with self.subTest(index=index,keys=keys):
                data=copy.deepcopy(originals);target=data[index]
                for k in keys[:-1]:target=target[k]
                target[keys[-1]]=value
                with self.assertRaises(M.Error):M.evidence_bindings(*data)
        data=copy.deepcopy(originals)
        next(x for x in data[4]['entries'] if x['path']==M.CORRUPT_MEMBER)['classification']='reconstructible'
        with self.assertRaisesRegex(M.Error,'capsule coverage'):M.evidence_bindings(*data)

    def test_output_constructor_closes_parent_on_child_open_failure(self):
        with tempfile.TemporaryDirectory() as d:
            before=set(os.listdir('/proc/self/fd'))
            with self.assertRaises(FileNotFoundError):M.OutputDir(Path(d)/'missing')
            self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def test_output_write_preserves_primary_and_close_failure(self):
        with tempfile.TemporaryDirectory() as d:
            output=M.OutputDir(Path(d));real_close=M.os.close
            def close_and_fail(fd):real_close(fd);raise OSError('close fault')
            try:
                with mock.patch.object(M,'full_write',side_effect=OSError('write fault')),mock.patch.object(M.os,'close',side_effect=close_and_fail):
                    with self.assertRaises(M.CompositeError) as failure:output.write('packet.failure',b'x')
                self.assertIn('write fault',str(failure.exception));self.assertIn('close fault',str(failure.exception))
            finally:output.close()

    def test_partial_exclusion_write_failure_closes_all_descriptors(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(M,'COMMON_EXCLUSION',Path(d)/'common'), mock.patch.object(M,'LEGACY_EXCLUSIONS',(Path(d)/'legacy',)), mock.patch.object(M.ExclusionLease,'_make_immutable'), mock.patch.object(M.ExclusionLease,'_flags',return_value=M.FS_IMMUTABLE_FL):
            original=M.full_write;calls=[]
            def fail_second(fd,data):
                calls.append(fd)
                if len(calls)==2:raise OSError('injected write')
                return original(fd,data)
            held=M.SharedExclusions(self.release(d));before=set(os.listdir('/proc/self/fd'))
            with mock.patch.object(M,'full_write',side_effect=fail_second):
                with self.assertRaisesRegex(OSError,'injected write'):held.__enter__()
            self.assertEqual(before,set(os.listdir('/proc/self/fd')))
            self.assertTrue(all(x.fd is None and x.parent_fd is None for x in held.records))
            self.assertTrue((Path(d)/'common').exists());self.assertTrue((Path(d)/'legacy').exists())

    def test_shared_cleanup_aggregates_and_continues(self):
        held=M.SharedExclusions({});first=mock.Mock();second=mock.Mock()
        first._close.side_effect=OSError('first close');second._close.side_effect=OSError('second close')
        held.records=[first,second]
        with self.assertRaises(M.CompositeError) as failure:held.close()
        first._close.assert_called_once();second._close.assert_called_once()
        self.assertIn('first close',str(failure.exception));self.assertIn('second close',str(failure.exception))

    def test_aggregate_guard_blocks_mutation_on_any_lost_exclusion(self):
        h=mock.Mock();h.remove_root=mock.Mock();h.quarantine=mock.Mock()
        shared=mock.Mock(unsafe=True);lease=mock.Mock(unsafe=True);protected=mock.Mock(unsafe=True);shared.assert_held.side_effect=M.Error('shared lost')
        original=h.remove_root;M.bind_delete_boundary(h,M.AggregateGuard(shared,lease,protected))
        with self.assertRaisesRegex(M.Error,'shared lost'):h.remove_root({},None)
        original.assert_not_called()
        with mock.patch.object(M.os,'unlink') as unlink:
            with self.assertRaisesRegex(M.Error,'shared lost'):h.os.unlink('anything')
            unlink.assert_not_called()

    def test_protected_open_replacement_rejected_without_fd_leak(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'seal';p.write_bytes(b'old');st=p.stat()
            specs=((str(p),st.st_dev,st.st_ino,3,hashlib.sha256(b'old').hexdigest(),False),)
            original=M.os.open;changed=[]
            def replace(path,*args,**kwargs):
                if str(path)=='seal' and not changed:
                    changed.append(True);p.rename(Path(d)/'old');p.write_bytes(b'old')
                return original(path,*args,**kwargs)
            before=set(os.listdir('/proc/self/fd'))
            with mock.patch.object(M,'PROTECTED_SPECS',specs),mock.patch.object(M.os,'open',side_effect=replace):
                with self.assertRaisesRegex(M.Error,'identity changed'):M.ProtectedDescriptors().__enter__()
            self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def test_rename_guard_detects_exclusion_loss_after_quarantine_entry(self):
        h=mock.Mock();syscall=mock.Mock(name='renameat2');h.rename_noreplace=syscall
        guard=mock.Mock(unsafe=True);lost=[]
        def check():
            if lost:raise M.Error('exclusion lost before renameat2')
        guard.assert_held.side_effect=check
        def quarantine_body(*args):
            lost.append(True)
            h.rename_noreplace(12,'original','quarantine')
        h.quarantine=quarantine_body
        M.bind_delete_boundary(h,guard)
        with self.assertRaisesRegex(M.Error,'exclusion lost before renameat2'):h.quarantine({},None)
        syscall.assert_not_called()
        self.assertEqual(guard.assert_held.call_count,2)

    def test_rename_failure_preserves_primary_and_post_guard_failure(self):
        h=mock.Mock();primary=OSError('renameat2 fault');cleanup=M.Error('post-rename exclusion lost')
        h.rename_noreplace=mock.Mock(side_effect=primary)
        guard=mock.Mock(unsafe=True);guard.assert_held.side_effect=[None,cleanup]
        M.bind_delete_boundary(h,guard)
        with self.assertRaises(M.CompositeError) as failure:h.rename_noreplace(12,'original','quarantine')
        self.assertTrue(M.failure_contains(failure.exception,primary))
        self.assertTrue(M.failure_contains(failure.exception,cleanup))

    def test_callback_environment_has_no_inherited_docker_or_python_settings(self):
        with mock.patch.dict(os.environ,{'DOCKER_HOST':'tcp://bad:1234','PYTHONPATH':'/bad','DOCKER_CONTEXT':'bad'}):
            env=M.callback_env()
        self.assertEqual(env['DOCKER_HOST'],'unix:///var/run/docker.sock')
        self.assertNotIn('DOCKER_CONTEXT',env);self.assertNotIn('PYTHONPATH',env)

    def docker_fixture(self,secret):
        ids=['decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9','8943e49772f840ba5da6571c2e2c6fde60b61157f21f873d832669157ef9bc10','a'*64]
        rows=[]
        for identity in ids:
            rows.append({'Id':identity,'Config':{'Image':'image','User':'0','Cmd':['test',secret],'Env':['PASSWORD='+secret],'Labels':{'password':secret}},'State':{'Status':'exited','Running':False,'Paused':False,'Restarting':False,'Dead':False,'Pid':0,'ExitCode':1,'OOMKilled':False,'Error':secret},'HostConfig':{'SecurityOpt':[secret],'Privileged':False,'ReadonlyRootfs':True,'NanoCpus':4,'Memory':1024,'PidsLimit':512,'CpusetCpus':'2-5','RestartPolicy':{'Name':'no','MaximumRetryCount':0},'AutoRemove':False},'Mounts':[{'Source':'/safe/source','Destination':'/safe/destination','Credential':secret}]})
        docker={'terminal_containers':{r['Id']:r for r in rows[:2]},'terminal':{'id':ids[0],'state':rows[0]['State'],'exact_config':{k:rows[0][k] for k in ('Config','HostConfig','Mounts')}}}
        return ids,rows,docker

    def test_docker_secrets_never_enter_captures_or_helper_evidence(self):
        secret='UNRELATED-ENV-CREDENTIAL-TEST';ids,rows,docker=self.docker_fixture(secret)
        ps=('\n'.join(ids)+'\n').encode();raw=json.dumps(rows).encode();captures={}
        def capture(base,name,data):captures[name]=data
        guard=mock.Mock(unsafe=True)
        with mock.patch.object(M,'owned_spawn',return_value=(object(),{})),mock.patch.object(M,'_drain',side_effect=[(ps,b''),(raw,secret.encode()),(ps,b'')]),mock.patch.object(M,'complete_process',return_value=0),mock.patch.object(M,'close_streams',return_value=None),mock.patch.object(M,'restore_spawn_mask',return_value=None),mock.patch.object(M,'capture',side_effect=capture):
            census=M.docker_callback(None,docker,guard)()
        persisted=b'\n'.join(captures.values())+json.dumps(census).encode()
        self.assertNotIn(secret.encode(),persisted);self.assertNotIn(b'"Env"',persisted)
        self.assertIn('docker-census.json',captures)
        self.assertEqual(census['inspect'][2],{'Id':'a'*64,'Mounts':[{'Source':'/safe/source','Destination':'/safe/destination'}]})
        projected=M.sanitized_terminal_release(docker)
        self.assertNotIn(secret,json.dumps(projected))
        spec=importlib.util.spec_from_file_location('retire_helper_secret_test',M.HELPER)
        helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        helper.validate_docker_census(census,projected,[M.CANDIDATE,M.BACKUP,*M.QUARANTINES])
        census['inspect'][2]['Mounts'][0]['Source']=M.CANDIDATE
        with self.assertRaisesRegex(Exception,'unexpected candidate container'):helper.validate_docker_census(census,projected,[M.CANDIDATE,M.BACKUP,*M.QUARANTINES])

    def test_terminal_env_change_still_rejected_without_disclosure(self):
        secret='CHANGED-TERMINAL-ENV-SECRET';ids,rows,docker=self.docker_fixture('original')
        changed=copy.deepcopy(rows);changed[0]['Config']['Env']=['PASSWORD='+secret]
        ps=('\n'.join(ids)+'\n').encode();captures={}
        with mock.patch.object(M,'owned_spawn',return_value=(object(),{})),mock.patch.object(M,'_drain',side_effect=[(ps,b''),(json.dumps(changed).encode(),b''),(ps,b'')]),mock.patch.object(M,'complete_process',return_value=0),mock.patch.object(M,'close_streams',return_value=None),mock.patch.object(M,'restore_spawn_mask',return_value=None),mock.patch.object(M,'capture',side_effect=lambda base,name,data:captures.update({name:data})):
            with self.assertRaisesRegex(M.Error,'terminal config') as failure:M.docker_callback(None,docker,mock.Mock(unsafe=True))()
        self.assertNotIn(secret,str(failure.exception));self.assertNotIn(secret.encode(),b'\n'.join(captures.values()))

    def test_docker_parse_failure_does_not_echo_secret_or_raw_output(self):
        secret='MALFORMED-JSON-SECRET';ids,rows,docker=self.docker_fixture(secret)
        ps=('\n'.join(ids)+'\n').encode();captures={}
        with mock.patch.object(M,'owned_spawn',return_value=(object(),{})),mock.patch.object(M,'_drain',side_effect=[(ps,b''),(('{'+'"'+secret+'":1,"'+secret+'":2}').encode(),secret.encode())]),mock.patch.object(M,'complete_process',return_value=0),mock.patch.object(M,'close_streams',return_value=None),mock.patch.object(M,'restore_spawn_mask',return_value=None),mock.patch.object(M,'capture',side_effect=lambda base,name,data:captures.update({name:data})):
            with self.assertRaisesRegex(M.Error,'Docker JSON rejected') as failure:M.docker_callback(None,docker,mock.Mock(unsafe=True))()
        self.assertNotIn(secret,str(failure.exception));self.assertNotIn(secret.encode(),b'\n'.join(captures.values()))

    def test_private_subprocess_failure_scrubs_exception_and_stderr(self):
        secret='SUBPROCESS-ERROR-SECRET';captures={}
        with mock.patch.object(M,'owned_spawn',side_effect=OSError(secret)),mock.patch.object(M,'cleanup_owned',return_value=((secret.encode(),secret.encode()),OSError(secret))),mock.patch.object(M,'close_streams',return_value=None),mock.patch.object(M,'restore_spawn_mask',return_value=None),mock.patch.object(M,'capture',side_effect=lambda base,name,data:captures.update({name:data})):
            with self.assertRaises(M.Error) as failure:M.call(['docker'],None,'docker-inspect',private=True)
        self.assertNotIn(secret,json.dumps(M.error_record(failure.exception)));self.assertNotIn(secret.encode(),b'\n'.join(captures.values()))

    def test_observer_sentinel_blocks_even_with_release_hash(self):
        with mock.patch.object(M,'RELEASE_SHA256','a'*64),mock.patch.object(M,'OBSERVER_SHA256','OBSERVER_HASH_REQUIRED'),mock.patch.object(M.os,'geteuid',side_effect=AssertionError('root queried')):
            with self.assertRaisesRegex(M.Error,'DRAFT_NOT_RELEASED'):M.admit('anything')

    def closure(self):
        baseline={'roots':[{'tree_member_identities':[[26,5,0,0,16384,448]]}]}
        summary={'schema':'mckernel.post-delete-live-reference-round.v1.summary','status':'PASS','scan_complete':True,'observer_sha256':M.OBSERVER_SHA256,'baseline_sha256':'b'*64,'boot_id':'test','roots':baseline['roots'],'observer_pid':21,'observer_starttime':'34','rounds':[]}
        rows=[]
        for n in range(1,4):
            row={'schema':'mckernel.post-delete-live-reference-round.v1','status':'PASS','round':n,'scan_complete':True,'observer_sha256':M.OBSERVER_SHA256,'baseline_sha256':'b'*64,'boot_id':'test','observer_pid':21,'observer_starttime':'34','retained_inode_count':1,'task_churn':False,'closure_nonconvergent':False,'censuses':[[[21,21,'34']],[[21,21,'34']]],'records':[{'identity':[21,21,'34'],'successful':True,'state':'same','references':[],'denials':[],'incomplete':[],'mount_proof':{'complete':True,'identity':[21,21,'34']}}]}
            row.update({k:[] for k in ('path_failures_before','path_failures_after','target_references','permission_denials','incomplete','identity_replacements','entry_churn','unscanned_final_identities')})
            raw=json.dumps(row).encode();rows.append((raw,row));summary['rounds'].append({'round':n,'status':'PASS','path':str(M.EVIDENCE_DIR/('post-delete-scan-%d.json'%n)),'sha256':M.sha(raw)})
        return summary,baseline,'b'*64,{'boot_id':'test'},rows

    def test_three_retained_closure_rounds_and_failure_vectors(self):
        original=self.closure();M.validate_post_delete(*original)
        for key,value in [('permission_denials',[{}]),('target_references',[{}]),('identity_replacements',[{}]),('entry_churn',[{}]),('path_failures_after',[{}]),('task_churn',True),('closure_nonconvergent',True),('retained_inode_count',2),('records',[]),('censuses',[])]:
            with self.subTest(key=key):
                data=copy.deepcopy(original);data[4][1][1][key]=value
                with self.assertRaises(M.Error):M.validate_post_delete(*data)
        data=copy.deepcopy(original);data[0]['rounds'][2]['sha256']='0'*64
        with self.assertRaisesRegex(M.Error,'digest'):M.validate_post_delete(*data)
        data=copy.deepcopy(original);data[4][2][1]['records'][0]['mount_proof']['complete']=False
        with self.assertRaisesRegex(M.Error,'mount proof'):M.validate_post_delete(*data)
        data=copy.deepcopy(original);data[4].pop()
        with self.assertRaisesRegex(M.Error,'count'):M.validate_post_delete(*data)

    def test_quarantine_validation_checks_each_root(self):
        # Populate only pre-root fields; a bad quarantine must reject before
        # inventory, Git, process, or destructive operations can be reached.
        keys={'schema','status','one_shot','retry','rollback','main_commit','ihk_commit','candidate','metadata_backup','inventory_sha256','capsule_sha256','success_sha256','source_hashes','roots','protected_non_targets','sealed','observer','docker','boot_id','launcher_identities','operational_exclusion','exclusion_tombstone','conflict_basenames','heavy_lease_paths','known_exact_build_leases','object_counts','post_delete_observer_rounds','resource_floors','output_dir','evidence_namespace','template','finalization'}
        r=dict.fromkeys(keys)
        r.update(schema='mckernel.ordinary-retirement-release.v1',status='PASS_ONE_SHOT_RETIRE',one_shot=True,retry=False,rollback=False,main_commit=M.MAIN,ihk_commit=M.IHK,candidate=M.CANDIDATE,metadata_backup=M.BACKUP,inventory_sha256=M.INV_SHA,capsule_sha256=M.CAP_SHA,success_sha256=M.SUCCESS_SHA,source_hashes={'helper':M.HELPER_SHA256,'observer':M.OBSERVER_SHA256,'archive':M.ARCHIVE_SHA256,'helper_test':M.HELPER_TEST_SHA256,'observer_test':M.OBSERVER_TEST_SHA256},roots=[])
        for path,q,ino in zip((M.CANDIDATE,M.BACKUP),M.QUARANTINES,(58679,69465)):
            r['roots'].append({'path':path,'root':M.root(ino,40),'parent':M.root(1,40),'members':[],'quarantine_name':Path(q).name,'quarantine_uid':0,'quarantine_gid':0,'quarantine_mode':0o700})
        for index in range(2):
            changed=copy.deepcopy(r);changed['roots'][index]['quarantine_uid']=1000
            with self.subTest(index=index),self.assertRaisesRegex(M.Error,'quarantine owner distinction'):M.validate_release(changed,'unused',{})

if __name__=='__main__': unittest.main()
