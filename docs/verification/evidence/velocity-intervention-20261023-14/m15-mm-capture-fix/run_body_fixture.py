#!/usr/bin/env python3
"""Actual M15 original-C/Rust and gate-object probes; fresh campaign grant required."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

HERE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-13/m15-mm-finish/batch-1')
SUCCESSOR=Path(__file__).resolve().parent
RUSTC=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
OBJTOOL=Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output/build/tools/objtool/objtool')


def gate_metadata(path):
    """Inspect actual ELF64 table relocations; no parser dependency or execution."""
    raw=Path(path).read_bytes()
    if raw[:6] != b'\x7fELF\x02\x01':
        raise ValueError('expected little-endian ELF64')
    header=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    if header[2] != 62:
        raise ValueError('expected EM_X86_64')
    shoff,shsize,shnum,shstr=header[6],header[11],header[12],header[13]
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*shsize) for i in range(shnum)]
    def payload(section):return raw[section[4]:section[4]+section[5]]
    names=payload(sections[shstr])
    def string(data,offset):return data[offset:data.index(0,offset)].decode()
    section_names=[string(names,s[0]) for s in sections]
    table_index=section_names.index('__jump_table')
    table=sections[table_index]
    if table[5] != 48 or table[8] != 8:
        raise ValueError('expected three aligned16-byte jump entries')
    annotation=sections[section_names.index('.discard.annotate_data')]
    if annotation[5] != 24:
        raise ValueError('expected three8-byte special-data annotations')
    reloc=sections[section_names.index('.rela__jump_table')]
    symbols_section=sections[reloc[6]]
    symbol_names=payload(sections[symbols_section[6]])
    symbols=[]
    for offset in range(0,symbols_section[5],symbols_section[9]):
        values=struct.unpack_from('<IBBHQQ',payload(symbols_section),offset)
        symbols.append({'name':string(symbol_names,values[0]),'section':values[3],'value':values[4]})
    entries=[]
    for offset in range(0,reloc[5],reloc[9]):
        at,info,addend=struct.unpack_from('<QQq',payload(reloc),offset)
        symbol=symbols[info>>32]
        entries.append({'offset':at,'type':info & 0xffffffff,'addend':addend,'symbol':symbol})
    expected=['__tracepoint_mmap_lock_start_locking','__tracepoint_mmap_lock_acquire_returned','__tracepoint_mmap_lock_released']
    keys=sorted((e for e in entries if e['offset']%16==8),key=lambda e:e['offset'])
    if [(e['symbol']['name'],e['type'],e['addend']) for e in keys] != [(name,24,10) for name in expected]:
        raise ValueError('key PC64 relocation/symbol/key-offset+HACK mismatch')
    sites=[]
    for entry in range(3):
        code=next(e for e in entries if e['offset']==entry*16)
        target=next(e for e in entries if e['offset']==entry*16+4)
        if code['type']!=2 or target['type']!=2:
            raise ValueError('expected PC32 code and target relocations')
        section=sections[code['symbol']['section']]
        at=code['symbol']['value']+code['addend']
        sites.append({'section':section_names[code['symbol']['section']],
                      'offset':at,'bytes':payload(section)[at:at+5].hex(),
                      'target_offset':target['symbol']['value']+target['addend']})
    return {'table_bytes':table[5],'table_alignment':table[8],
            'annotation_bytes':annotation[5],'keys':keys,'sites':sites}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-after-campaign-grant',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--phase',choices=['body'],required=True)
    parser.add_argument('--cc',type=Path,default=Path('/usr/bin/cc'))
    parser.add_argument('--rustc',type=Path,default=RUSTC)
    parser.add_argument('--objtool',type=Path,default=OBJTOOL)
    args=parser.parse_args()
    output=args.output.resolve()
    if output != SUCCESSOR/'actual-body-attempt-1':
        raise SystemExit('output must be a new private subdirectory')
    output.mkdir(parents=True,exist_ok=False)
    environment={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','TZ':'UTC',
                 'HOME':str(output),'TMPDIR':str(output),'RUST_BACKTRACE':'0',
                 'RUST_MIN_STACK':'2097152'}
    counter=0
    commands=[]
    def run(argv,expected=0):
        nonlocal counter
        argv=[str(v) for v in argv]
        counter+=1
        stdout=output/f'{counter:02d}.stdout'
        stderr=output/f'{counter:02d}.stderr'
        command={'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                 'argv':argv,'cwd':str(HERE),'expected_returncode':expected,
                 'status':'RUNNING','stdout':str(stdout),'stderr':str(stderr)}
        commands.append(command)
        def save_commands():
            (output/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n')
        save_commands()
        try:
            with stdout.open('wb') as out,stderr.open('wb') as err:
                result=subprocess.run(argv,cwd=HERE,env=environment,stdout=out,stderr=err,timeout=30)
        except subprocess.TimeoutExpired:
            command.update(status='TIMEOUT_PRESERVED',timeout_seconds=30)
            save_commands()
            raise
        except OSError as error:
            command.update(status='LAUNCH_FAILURE_PRESERVED',error=str(error))
            save_commands()
            raise
        command.update(status='RETIRED',returncode=result.returncode)
        save_commands()
        if result.returncode != expected:
            raise RuntimeError(f'command{counter} returned{result.returncode}, expected{expected}')
        return stdout.read_text()
    summary={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
             'status':'RUNNING','phase':args.phase,'production_module_or_native_acceptance':False}
    try:
        frozen=json.loads((HERE/'CANDIDATE-INPUTS.json').read_text())
        for relative,expected_hash in frozen['private_source_sha256'].items():
            if hashlib.sha256((HERE/relative).read_bytes()).hexdigest()!=expected_hash:
                raise ValueError('frozen candidate input drift: '+relative)
        python=frozen['python_interpreter']
        actual_python=Path(sys.executable)
        if str(actual_python.resolve())!=python['resolved'] or hashlib.sha256(actual_python.read_bytes()).hexdigest()!=python['sha256']:
            raise ValueError('capture interpreter identity differs from exact profile')
        supplied={'host_fixture_C_compiler':args.cc,'host_fixture_Rust_1_92':args.rustc,
                  'retained_pinned_objtool':args.objtool,'assembly_readback':Path('/usr/bin/objdump')}
        used_roles={'host_fixture_C_compiler','assembly_readback'}
        used_roles.add('host_fixture_Rust_1_92' if args.phase=='body' else 'retained_pinned_objtool')
        for tool in frozen['tools']:
            if tool['role'] not in used_roles:
                continue
            actual=supplied[tool['role']]
            if str(actual)!=tool['invocation'] or str(actual.resolve())!=tool['resolved']:
                raise ValueError('unbound tool invocation: '+tool['role'])
            if hashlib.sha256(actual.read_bytes()).hexdigest()!=tool['sha256']:
                raise ValueError('tool identity drift: '+tool['role'])
        run([args.cc,'--version'])
        if args.phase == 'body':
            rust_identity=run([args.rustc,'--version','--verbose'])
            if not rust_identity.startswith('rustc 1.92.0'):
                raise ValueError('expected pinned Rust1.92.0')
            run([args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(HERE/'generated/include'),
                 '-c',HERE/'generated/original/mcctrl_vm_write_compat.c','-o',output/'reference.o'])
            run([args.rustc,'--crate-name','m15_mm_candidate','--crate-type','staticlib','--edition=2021',
                 '--cfg','m15_fixture','-C','panic=abort','-C','opt-level=2','-C','codegen-units=1',
                 HERE/'fixture_root.rs','-o',output/'candidate.a'])
            run([args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-pie','-no-pie',
                 HERE/'fixture_driver.c',output/'reference.o',output/'candidate.a','-o',output/'fixture'])
            vectors=json.loads((HERE/'FIXTURE-VECTORS.json').read_text())['valid_vectors']
            comparisons=[]
            for vector in vectors:
                initial,trace,expected=vector['initial'],vector['trace'],vector['expected']
                ops=''.join({'lock':'L','unlock':'U','vma0':'0','vma1':'1'}[op] for op in vector['operations'])
                result=json.loads(run([output/'fixture',initial['mm_sequence'],*initial['vma_sequences'],
                                       trace['outer_enabled_mask'],trace['inner_enabled_mask'],ops]))
                for key in ['mm_sequence','vma_sequences','held_mmap','held_vma']:
                    if result[key] != expected[key]:raise ValueError(vector['id']+' independent state '+key)
                primitive=[];calls=[];emitted=[]
                for tag,target,value in result['events']:
                    obj='mmap' if target==0 else 'vma'+str(target-1)
                    if tag==5:primitive.append(obj+'.down')
                    elif tag==6:primitive.append(obj+'.up')
                    elif tag==7:primitive.append('wmb(seq='+str(value)+')')
                    elif tag==8:primitive.append(obj+'.write_once('+str(value)+')')
                    elif tag==2:calls.append(['start','acquire','release'][target])
                    elif tag==4:emitted.append(['start','acquire','release'][target])
                if primitive!=expected['primitive_order']:raise ValueError(vector['id']+' independent primitive order')
                if calls!=expected['trace_helper_calls'] or emitted!=expected['trace_events_emitted']:
                    raise ValueError(vector['id']+' independent trace gate expectation')
                assertion_reads=sum(tag==9 for tag,target,value in result['events'])
                warnings=sum(tag==10 for tag,target,value in result['events'])
                if assertion_reads!=expected['assertion_reads'] or warnings!=expected['warnings']:
                    raise ValueError(vector['id']+' independent active write-lock assertion expectation')
                comparisons.append({'id':vector['id'],'result':result})
            # Also exercise actual repeated-epoch bodies, independent of the22 base vectors.
            epochs=json.loads(run([output/'fixture',0,0,0,0,0,'L0UL01U']))
            if epochs['mm_sequence']!=4 or epochs['vma_sequences']!=[3,3]:
                raise ValueError('successive lock epochs')
            for ops in ['U','0','LL','L']:
                run([output/'fixture',0,0,0,0,0,ops],expected=2)
            (output/'COMPARISONS.json').write_text(json.dumps(comparisons,indent=2)+'\n')
            assertions=[]
            for vector in json.loads((HERE/'FIXTURE-VECTORS.json').read_text())['isolated_assertion_vectors']:
                result=json.loads(run([output/'fixture','--assert-warning',vector['low'],vector['high'],vector['repetitions']]))
                if not result['equal'] or result['warnings']!=vector['expected_warnings'] or result['assertion_reads']!=vector['repetitions']:
                    raise ValueError(vector['id']+' isolated warning expectation')
                assertions.append({'id':vector['id'],'result':result})
            (output/'ASSERTION-COMPARISONS.json').write_text(json.dumps(assertions,indent=2)+'\n')
            (output/'BODY-RESULT.json').write_text(json.dumps({
                'status':'PASS_PRIVATE_BODY_AND_MOCKED_WARNING_FIXTURE',
                'scope':summary['scope'],'compared_base_vectors':len(comparisons),
                'isolated_assertion_vectors':len(assertions),'production_acceptance':False},indent=2)+'\n')
            run(['/usr/bin/objdump','-dr',output/'reference.o'])
            for symbol in ['m15_rust_mmap_write_lock','m15_rust_mmap_write_unlock','m15_rust_vma_start_write']:
                run(['/usr/bin/objdump','-dr','--disassemble='+symbol,output/'candidate.a'])
            summary.update(status='PASS_PRIVATE_BODY_AND_MOCKED_WARNING_FIXTURE',
                           compared_base_vectors=len(comparisons),extra_epoch_cases=1,
                           invalid_schedules_rejected=4,isolated_assertion_vectors=len(assertions),
                           limitations=['MM primitives, trace gates and warning emission are mocked.',
                                        'No actual warning UD2, kernel tracing, LKMM concurrency or production result.'])
        else:
            run([args.cc,'-DM15_USER_GATE_PROBE=1','-c',HERE/'m15_mmap_trace_gates.S','-o',output/'gate-raw.o'])
            raw=gate_metadata(output/'gate-raw.o')
            if any(not site['bytes'].startswith(('eb','e9')) for site in raw['sites']):
                raise ValueError('expected initial jump instructions at all three sites')
            shutil.copyfile(output/'gate-raw.o',output/'gate-nop.o')
            run([args.objtool,'--hacks=jump_label','--werror',output/'gate-nop.o'])
            transformed=gate_metadata(output/'gate-nop.o')
            for original,changed in zip(raw['sites'],transformed['sites']):
                prefix='6690' if original['bytes'].startswith('eb') else '0f1f440000'
                if not changed['bytes'].startswith(prefix):
                    raise ValueError('objtool did not convert site to matching-length x86 NOP')
            for suffix,expected in [('raw',1),('nop',0)]:
                run([args.cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-pie','-no-pie',
                     HERE/'gate_probe.c',output/('gate-'+suffix+'.o'),'-o',output/('gate-'+suffix)])
                run([output/('gate-'+suffix),expected])
            run(['/usr/bin/objdump','-dr',output/'gate-raw.o'])
            run(['/usr/bin/objdump','-dr',output/'gate-nop.o'])
            (output/'GATE-OBJECTS.json').write_text(json.dumps({'raw':raw,'objtool_processed':transformed},indent=2)+'\n')
            summary.update(status='PASS_PRIVATE_STANDALONE_GATE_MICROPROBE',gate_sites=3,
                           limitations=['Mocked MM primitives and trace gates in body fixture.',
                                        'Gate microprobe uses user linkage, not exact SDK ENDBR/RET/module integration.',
                                        'Warning fixture mocks only warning emission; actual warning ASM is not run in user mode.',
                                        'No exactSDK layout/leaf/full module/native result or concurrency proof.'])
    except Exception as error:
        summary.update(status='FAIL_PRESERVED_NO_AUTOMATIC_RETRY',error=str(error))
        (output/'RESULT.json').write_text(json.dumps(summary,indent=2)+'\n')
        raise
    (output/'RESULT.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
