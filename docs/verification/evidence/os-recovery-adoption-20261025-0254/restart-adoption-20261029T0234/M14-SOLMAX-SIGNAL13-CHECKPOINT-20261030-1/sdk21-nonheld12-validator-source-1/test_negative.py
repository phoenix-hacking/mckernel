#!/usr/bin/env python3
"""Pure synthetic negative fixtures; functional McKernel OS only, no security testing.
No compiler, external commands, kernel objects, SDK claim, or actual acceptance.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import traceback
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('adapter',HERE/'validate_artifacts.py')
a=importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
PROFILE=json.loads(a.PROFILE.read_bytes())

class FakeElf:
    def __init__(self, path):
        self.sections=[{'name':'.fixture_abi_witness'}]
        self.symbols=[]

class RejectionFixtures(unittest.TestCase):
    def fixture(self, tmp, profile):
        root=Path(tmp); build=root/'work/output/build/kernel'; build.mkdir(parents=True)
        worker={'commands':[]}
        for command in profile['commands']:
            worker['commands'].append({'argv':command['argv'], 'cwd':command['cwd'], 'returncode':0,
                'output':{'path':command['output'],'bytes':1,'sha256':'1'*64}})
        workerpath=root/'worker.json'; workerpath.write_text(json.dumps(worker))
        orders=profile['link']['order']
        (build/'mckernel.img.map').write_text(''.join('LOAD '+name+'\n' for name in orders))
        linkdep=build/'CMakeFiles/mckernel.img.dir/link.d'; linkdep.parent.mkdir(parents=True)
        linkdep.write_text('mckernel.img: '+' '.join(orders)+'\n')
        deps={}
        for kind, path, token in [('rust','rust/mckernel_rust.d','/src/kernel/rust/lib.rs'),
                                  ('generic',a.GENERIC+'.d','/src/kernel/syscall.c'),
                                  ('arch',a.ARCH+'.d','/src/arch/x86_64/kernel/syscall.c')]:
            dest=build/path; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text('fixture.o: '+token+'\n')
            sha=profile['source_bindings']['overlay_hashes']['arch/x86_64/kernel/syscall.c']['sha256'] if kind=='arch' else '2'*64
            deps[kind]=[{'token':token,'actual_file':{'path':'/fixture/'+kind,'bytes':1,'sha256':sha}}]
        src={'path':'/fixture/arch','bytes':1,'sha256':deps['arch'][0]['actual_file']['sha256']}
        receipt=root/'receipt.json'; receipt.write_text(json.dumps({'profile_sha256':a.PROFILE_SHA,'staged_source':src,'logical_path':deps['arch'][0]['token']}))
        origin={'source_sha256':src['sha256'],'source_logical_path':deps['arch'][0]['token'],
                'staged_source':src,'receipt':{'path':str(receipt),'bytes':1,'sha256':'3'*64},
                'independent_review':{'path':'/fixture/review','bytes':1,'sha256':'4'*64}}
        binding={'profile_sha256':a.PROFILE_SHA,
                 'old_objects':{'generic':[{'path':'/fixture/oldgen','bytes':1,'sha256':'5'*64}],
                                'arch':[{'path':'/fixture/oldarch','bytes':1,'sha256':'6'*64}]},
                 'dependencies':deps,'arch_full_source_origin':origin}
        bindpath=root/'binding.json'; bindpath.write_text(json.dumps(binding))
        profilepath=root/'profile.json'; profilepath.write_text(json.dumps(profile))
        retained={str(build/r['token']):r for r in profile['link']['retained_8']}
        def fake_digest(path):
            p=str(path)
            if p==str(profilepath): return {'path':p,'bytes':1,'sha256':a.PROFILE_SHA}
            if p in retained: return {'path':p,'bytes':retained[p]['bytes'],'sha256':retained[p]['sha256']}
            return {'path':p,'bytes':1,'sha256':'1'*64}
        return root/'work',workerpath,bindpath,profilepath,binding,fake_digest

    def run_fixture(self, expected_line, profile=None, mutate=None):
        profile=copy.deepcopy(PROFILE if profile is None else profile)
        with tempfile.TemporaryDirectory(prefix='m14-validator-fixture-') as tmp:
            work,worker,bindpath,profilepath,binding,digest=self.fixture(tmp,profile)
            if mutate:
                mutate(binding)
                bindpath.write_text(json.dumps(binding))
            with mock.patch.object(a,'PROFILE',profilepath), mock.patch.object(a,'digest',side_effect=digest), \
                 mock.patch.object(a,'authenticate',side_effect=lambda ref:Path(ref['path'])), \
                 mock.patch.object(a,'load_nodes',return_value={'_ReuseElf':FakeElf,'Final':FakeElf}):
                try:
                    a.inspect(work,worker,bindpath)
                except AssertionError as error:
                    self.assertIn(expected_line, traceback.extract_tb(error.__traceback__)[-1].line)
                else:
                    self.fail('fixture unexpectedly passed')

    def test_authenticated_source_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory(prefix='m14-node-fixture-') as tmp:
            p=Path(tmp)/'node.py'; p.write_text('def source():\n    return 1\n')
            ref={'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            a.authenticate(ref); p.write_text('def source():\n    return 2\n')
            with self.assertRaises(AssertionError): a.authenticate(ref)

    def test_frozen_node_rejects_changed_ast_binding(self):
        p=copy.deepcopy(PROFILE); p['original_oracle_and_validation']['frozen_nodes'][0]['AST_sha256']='0'*64
        with self.assertRaises(AssertionError): a.load_nodes(p)

    def test_two_rebuilds_rejected(self):
        p=copy.deepcopy(PROFILE); p['link']['rebuild'].remove(a.ARCH)
        self.run_fixture('set(rebuilt)',profile=p)

    def test_original_389_tuple_change_rejected(self):
        nodes=a.load_nodes(PROFILE)
        ref=PROFILE['original_oracle_and_validation']['original389']; a.authenticate(ref)
        oracle=json.loads(Path(ref['path']).read_bytes())
        expected=a.expected_records(oracle['records']); changed=list(expected)
        row=list(changed[0]); row[-1] ^= 1; changed[0]=tuple(row)
        nodes['compare'](expected,expected)
        with self.assertRaises(AssertionError): nodes['compare'](expected,changed)

    def test_old_object_reuse_rejected(self):
        def mutate(binding): binding['old_objects']['generic'][0]['sha256']='1'*64
        self.run_fixture("not in {r['sha256']",mutate=mutate)

    def test_null_arch_origin_rejected(self):
        self.run_fixture("origin is not None",mutate=lambda binding:binding.update(arch_full_source_origin=None))

    def test_witness_section_rejected(self):
        # Reaches ELF loading with otherwise complete synthetic bookkeeping;
        # no synthetic ELF image is ever accepted.
        self.run_fixture("s['name'].lower() for s in e.sections")

if __name__=='__main__': unittest.main(verbosity=2)
