"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source preparation and static retained ELF/source extraction only; no workload.
"""
import ast,copy,hashlib,json,re,struct
from pathlib import Path
B=Path(__file__).resolve().parent
S=B.parent
R=S/'accepted-inline-machine-binding-correction1-source-1/exact-selected-process-prior-U-correction1-source-1'
E=R/'finite-six-command-envelope-source-1'
X=S.parent.parent/'x86-cpu'
A=X/'new-window-source-17-current285-five-data-owner-union-source-1'
def pin(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def save(n,v):
 p=B/n
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
 return pin(p)
r=json.loads((R/'EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json').read_text())
m=json.loads((R/'EXACT-SOURCE37-SELECTED-C-INPUT-AND-REUSE-MAP.json').read_text())
spec=json.loads((E/'EXACT-SOURCE38-SIX-COMMAND-ENVELOPE.SOURCE-ONLY.json').read_text())
ns=dict(Path=Path,struct=struct)
nodes=[n for n in ast.parse(Path(m['qualified_Elf_source']['path']).read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='Elf' or isinstance(n,ast.FunctionDef) and n.name in {'owning_relocations','object_bytes'}]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<retained-static-ELF-reader>','exec'),ns)
Elf=ns['Elf'];obj=ns['object_bytes'];own=ns['owning_relocations']
oldpath=m['compile_rows'][0]['baseline_selected_C_object']['path'];old=Elf(Path(oldpath));newpath=R/'output-1/process.selected.o';new=Elf(newpath)
assert pin(newpath)['sha256']=='f3953d2131216a32302b4ba8377684b77585447d76c6bada9508ffbb4c505e15'
def D(e):return {s['name'] for s in e.symbols if s['name'] and s['shndx'] and s['bind'] in (1,2)}
def U(e):return {s['name'] for s in e.symbols if s['name'] and not s['shndx']}
names=sorted(D(old)-D(new));assert len(names)==20 and not D(new)-D(old) and U(new)==U(old)
source=A/'source/kernel/process.c'
assert pin(source)['sha256'].startswith('d7646410')
lines=source.read_text().splitlines(keepends=True);append=''.join(lines[7000:7108]);assert all(len(re.findall(r'\b'+re.escape(n)+r'\b',append))==1 for n in names)
fixture=[]
for name in names:
 s=old.sym(name);sec=old.sections[s['shndx']]
 assert s['bind']==1 and s['type']==1 and sec['name']=='.rodata' and sec['flags']==2 and sec['type']==1 and sec['align']==32
 assert not own(old,s)
 fixture.append(dict(name=name,symbol=s,section=sec,bytes_hex=obj(old,s).hex(),outgoing_ALLOC_RELA=[]))
assert next(s for s in old.sections if s['name']=='.text')['size']==0
# Resolve every ALLOC relocation target by name OR section+addend. Conservative
# x86 PC-relative biases also cover the conventional field-end displacement.
def consumers(e,allow_old=False):
 hits=[];count=0
 for s in e.symbols:
  if s['name'] in names and not (allow_old and s['shndx']):hits.append(dict(kind='symbol',symbol=s))
 for sec in e.sections:
  if sec['type'] not in (4,9):continue
  owner=e.sections[sec['info']]
  if not owner['flags']&2:continue
  assert sec['type']==4 and sec['entsize']==24 and sec['size']%24==0 and sec['link']==e.table['index']
  for i in range(sec['size']//24):
   off,info,add=struct.unpack_from('<QQq',e.raw,sec['offset']+24*i);target=e.symbols[info>>32];typ=info&0xffffffff;count+=1
   if target['name'] in names:hits.append(dict(kind='named_RELA',owner=owner['name'],offset=off,target=target,addend=add,type=typ))
   if allow_old:
    for f in fixture:
     s=f['symbol'];addresses={target['value']+add}
     if typ in (2,4):addresses.add(target['value']+add+4)
     incoming=target['shndx']==s['shndx'] and any(s['value']<=a<s['value']+s['size'] for a in addresses)
     outgoing=sec['info']==s['shndx'] and s['value']<=off<s['value']+s['size']
     if incoming or outgoing:hits.append(dict(kind='section_addend_or_outgoing_RELA',fixture=f['name'],owner=owner['name'],offset=off,target=target,addend=add,type=typ))
 assert not hits,hits
 return dict(ALLOC_RELA_count=count,fixture_symbol_or_relocation_consumers=hits,section_addend_resolution=True,PC_relative_biases=[0,4])
consumerpaths=[oldpath,str(newpath)]+r['commands'][4]['argv'][5:]
# argv[5:] is the five-input tail after retained process at index4.
consumerpaths=list(dict.fromkeys(consumerpaths))
proof=[]
for p in consumerpaths:
 if p.endswith('/syscall.selected.o') and not Path(p).exists():continue
 proof.append(dict(input=pin(p),proof=consumers(Elf(Path(p)),p==oldpath)))
# Include baseline syscall selected object; successor checked again by actual observer.
p=m['compile_rows'][1]['baseline_selected_C_object']['path'];proof.append(dict(input=pin(p),proof=consumers(Elf(Path(p)))))
origin=[source,A/'actual-current285-data5-attempt-1/00/command.json',A/'actual-current285-data5-attempt-1/00/WHOLE-JOIN.json',X/'new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/EXACT-UNCHANGED-ARCH-C-REUSE.json']
contract=save('EXACT-CLOSED20-FIXTURE-ROLE-AND-CONSUMER-CONTRACT.json',dict(scope=r['scope'],old_process=pin(oldpath),retained_new_process=pin(newpath),retained_process_dependencies=pin(R/'output-1/process.selected.d'),fixture_names=names,fixture_objects=fixture,source_append=dict(source=pin(source),first_line=7001,last_line=7108,exact_text=append,sha256=hashlib.sha256(append.encode()).hexdigest()),origin_chain=[pin(p) for p in origin],actual_and_baseline_input_proofs=proof,old_process_text_size=0,exact_D_removed=names,exact_D_added=[],U_unchanged=True,future_syscall_and_partial_must_have_no_fixture_consumers=True,no_generic_prefix_allowance=True))
q=B/'quote-root';(q/'kernel').mkdir(parents=True);(q/'executer/include').mkdir(parents=True)
h=Path('/home/holden/mckernel/executer/include/uti.h');assert pin(h)['sha256']=='0787fcf51f5c5f5a702196e891cede5e570bb472e2b0a1a1041566b59e784fb7' and pin(h)['bytes']==1747
assert not re.search(rb'^\s*#\s*include',h.read_bytes(),re.M)
(q/'executer/include/uti.h').write_bytes(h.read_bytes())
syssource=Path(m['compile_rows'][1]['source']['path']);assert re.findall(r'^\s*#\s*include\s*"([^"\n]+)"',syssource.read_text(),re.M)==['../executer/include/uti.h']
# Retain original source path exactly; quote namespace repairs its sole missing include.
commands=copy.deepcopy(r['commands'][2:])
for c in commands:
 c['cwd']=str(B)
 c['argv']=[v.replace(str(R/'output-1/syscall.selected'),str(B/'output-1/syscall.selected')).replace(str(R/'output-1/coherent-selected.partial.o'),str(B/'output-1/coherent-selected.partial.o')).replace(str(R/'observe_selected_coherent_partial.NOT-RUN.py'),str(B/'observe_selected_coherent_partial.NOT-RUN.py')) for v in c['argv']]
 if c['argv'][0]=='/usr/bin/gcc-9':c['argv'][1:1]=['-iquote',str(q/'kernel')]
# New additive observer preserves every accepted gate except explicit closed20 D subtraction.
obs=(R/'observe_selected_coherent_partial.NOT-RUN.py').read_text()
obs=obs.replace("process, syscall = Elf(out / 'process.selected.o'), Elf(out / 'syscall.selected.o')", "process, syscall = Elf(Path(recipe['retained_process']['path'])), Elf(out / 'syscall.selected.o')")
needle="for name, elf in [('process',process),('syscall',syscall)]:\n    need(defined(elf) == set(m['old_' + name + '_D']), 'selected C definitions changed outside declaration selectors: ' + name)"
replacement="""fixture_contract = json.loads(auth(recipe['closed20_fixture_contract']))
need(len(fixture_contract['fixture_names']) == 20 and len(set(fixture_contract['fixture_names'])) == 20,
     'exact closed20 fixture membership differs')
need(fixture_contract['retained_new_process'] == recipe['retained_process'], 'retained process fixture proof differs')
for row in fixture_contract['origin_chain']:
    auth(row)
for proof in fixture_contract['actual_and_baseline_input_proofs']:
    auth(proof['input'])
old_process = Elf(Path(fixture_contract['old_process']['path']))
auth(fixture_contract['old_process'])
need(defined(old_process) == set(m['old_process_D']), 'old process exact D differs')
for f in fixture_contract['fixture_objects']:
    symbol = old_process.sym(f['name'])
    need(symbol == f['symbol'] and old_process.sections[symbol['shndx']] == f['section']
         and object_bytes(old_process,symbol).hex() == f['bytes_hex'] and not owning(old_process,symbol),
         'closed fixture storage/RELA differs')
need(set(fixture_contract['fixture_names']) == set(f['name'] for f in fixture_contract['fixture_objects']), 'closed fixture rows differ')
# This actual suffix observes all five concrete link inputs and partial again.
# An undefined name, definition, named relocation, or resolved SECTION+addend
# to any closed fixture object is a stop; no selected runtime consumer allowed.
def no_fixture_consumers(elf, old_owner=False):
    names = set(fixture_contract['fixture_names'])
    need(all(s['name'] not in names or old_owner and s['shndx'] for s in elf.symbols), 'selected input consumes/defines fixture')
    for sec in elf.sections:
        if sec['type'] not in (4,9) or not elf.sections[sec['info']]['flags'] & 2:
            continue
        need(sec['type'] == 4 and sec['entsize'] == 24 and sec['size'] % 24 == 0 and sec['link'] == elf.table['index'], 'ALLOC RELA format differs')
        for index in range(sec['size']//24):
            offset, info, addend = struct.unpack_from('<QQq',elf.raw,sec['offset']+24*index)
            target = elf.symbols[info >> 32]
            need(target['name'] not in names, 'named ALLOC fixture consumer')
            if old_owner:
                addresses = {target['value'] + addend}
                if info & 0xffffffff in (2,4):
                    addresses.add(target['value'] + addend + 4)
                for f in fixture_contract['fixture_objects']:
                    s = f['symbol']
                    need(not (target['shndx'] == s['shndx'] and any(s['value'] <= a < s['value']+s['size'] for a in addresses)), 'SECTION+addend fixture consumer')
                    need(not (sec['info'] == s['shndx'] and s['value'] <= offset < s['value']+s['size']), 'outgoing fixture RELA')
no_fixture_consumers(old_process,True)
for path in recipe['commands'][2]['argv'][4:]:
    no_fixture_consumers(Elf(Path(path)))
no_fixture_consumers(partial)
for name, elf in [('process',process),('syscall',syscall)]:
    expected_D = set(m['old_' + name + '_D'])
    if name == 'process':
        expected_D -= set(fixture_contract['fixture_names'])
    need(defined(elf) == expected_D, 'selected C definitions changed outside closed20 fixture-only removal: ' + name)"""
assert needle in obs;obs=obs.replace(needle,replacement)
obs=obs.replace("str(out/'process.selected.o')","recipe['retained_process']['path']")
obs=obs.replace("text = (out / (unit + '.selected.d')).read_text()", "text = (Path(recipe['retained_process_dependencies']['path']) if unit == 'process' else out / (unit + '.selected.d')).read_text()")
obs=obs.replace("result = dict(scope=recipe['scope'],", "result = dict(closed20_fixture_role=recipe['closed20_fixture_contract'],closed20_fixture_consumer_check='all five actual partial inputs and partial checked',retained_process=recipe['retained_process'],scope=recipe['scope'],")
(B/'observe_selected_coherent_partial.NOT-RUN.py').write_text(obs)
# Freeze same accepted map verbatim, with pointer preserved (no map rewriting).
r['predecessor_recipe']=pin(R/'EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json');r['commands']=commands;r['fresh_output_root']=str(B/'output-1');r['changed_C_compiler_jobs']=1;r['syntax_only_jobs']=1;r['retained_process']=pin(newpath);r['retained_process_dependencies']=pin(R/'output-1/process.selected.d');r['closed20_fixture_contract']=contract;r['root_grant']=None;r['status']='SOURCE_ONLY_EXACT_FOUR_COMMAND_SUFFIX_NOT_GRANTED'
# Original observer is removed from direct inputs, successor/contract/proofs added.
pins={x['path']:x for x in r['pinned_inputs'] if x['path']!=str(R/'observe_selected_coherent_partial.NOT-RUN.py')}
for p in [B/'observe_selected_coherent_partial.NOT-RUN.py',B/'EXACT-CLOSED20-FIXTURE-ROLE-AND-CONSUMER-CONTRACT.json',newpath,R/'output-1/process.selected.d',q/'executer/include/uti.h',h,*origin,E/'ACTUAL-SOURCE38-SIX-COMMAND-FIRST-RESULT.json']:
 pins[str(p)]=pin(p)
for p in consumerpaths:
 if Path(p).exists():pins[p]=pin(p)
r['pinned_inputs']=list(pins.values())
r['quote_namespace']=dict(search_root=str(q/'kernel'),materialized_header=pin(q/'executer/include/uti.h'),canonical_header=pin(h),source_quoted_includes=['../executer/include/uti.h'],transitive_includes=[])
recipe=save('EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json',r)
ready=save('READY-SOURCE38-FOUR-COMMAND-SUFFIX.NOT-GRANTED.json',dict(scope=r['scope'],status='SOURCE_ONLY_NOT_GRANTED',recipe=recipe,closed20_fixture_contract=contract,execution=False,actual_compiler=False,actual_observer=False,retained_process=pin(newpath),retained_dependency=pin(R/'output-1/process.selected.d'),no_prefix_replay=True,commands=commands,CPU0_grant=None))
manifest=save('FINITE-SOURCE38-FOUR-COMMAND-SUFFIX.FILES.json',dict(scope=r['scope'],files=[pin(p) for p in [B/'freeze_suffix_source.py',B/'observe_selected_coherent_partial.NOT-RUN.py',B/'EXACT-CLOSED20-FIXTURE-ROLE-AND-CONSUMER-CONTRACT.json',q/'executer/include/uti.h',B/'EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json',B/'READY-SOURCE38-FOUR-COMMAND-SUFFIX.NOT-GRANTED.json']]))
critical={x['path'] for x in spec['critical_recipe_inputs']};critical.discard(str(R/'observe_selected_coherent_partial.NOT-RUN.py'))
header={x['path'] for x in spec['batched_header_inputs']}
for p in pins:
 if p not in header:critical.add(p)
spec.update(recipe=recipe,source_READY=ready,source_manifest=manifest,critical_recipe_inputs=[pins[p] for p in sorted(critical)],critical_recipe_count=len(critical),batched_header_inputs=[pins[p] for p in sorted(header) if p in pins],batched_header_count=len(header),retained_process=pin(newpath),closed20_fixture_contract=contract,execution=False,actual_PID=None,actual_root_grant=None)
specpin=save('EXACT-SOURCE38-FOUR-COMMAND-ENVELOPE.SOURCE-ONLY.json',spec)
runner=(E/'run_source38_six_commands_once.NOT-GRANTED.py').read_text()
runner=re.sub(r'^SPEC = .*$', 'SPEC = '+repr(specpin),runner,flags=re.M);runner=re.sub(r'^RECIPE = .*$', 'RECIPE = '+repr(recipe),runner,flags=re.M)
runner=runner.replace('SIX-COMMAND','FOUR-COMMAND').replace('six-command','four-command').replace('six positive','four positive').replace("len(recipe['commands'])==6","len(recipe['commands'])==4")
runner=runner.replace("('process.selected.o','process.selected.d','syscall.selected.o','syscall.selected.d','coherent-selected.partial.o')","('syscall.selected.o','syscall.selected.d','coherent-selected.partial.o')")
runner=runner.replace('SIX_COMMAND','FOUR_COMMAND')
(B/'run_source38_four_commands_once.NOT-GRANTED.py').write_text(runner)
print(json.dumps(dict(recipe=recipe,spec=specpin,runner=pin(B/'run_source38_four_commands_once.NOT-GRANTED.py'),critical=len(critical),headers=len(header),fixture_names=names,consumer_inputs=len(proof)),indent=2))
