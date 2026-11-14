from pathlib import Path
import json,pprint
p=Path(__file__).parent;b=p.parent
v=(b/'m14-configure-source-closure-1/validator.closure.py').read_text();profile=json.loads((b/'m14-configure-input-matrix-1/PROFILE-OUT-ROOT.NOT-RELEASED.json').read_text());items=profile['configure_argv_items'];fixed=[i['value'] for i in items if 'flag' not in i];names=[i['flag'][2:] for i in items if 'flag' in i];assert len(names)==6
start=v.index('    a=commands[0][\'argv\']\n',v.index('def _selectors('));end=v.index('    v=commands[1][\'argv\']\n',start)
replacement='''    a=commands[0]['argv']
    # Full argv comparison rejects typed definitions, -U, -C and all extra options.
    fixed = '''+pprint.pformat(fixed,width=110)+'''
    names = '''+repr(names)+'''
    values=profile.get('required_actual_values')
    _require(isinstance(values,dict), 'required values missing')
    _require(all(isinstance(values.get(n),str) and '\\0' not in values[n] for n in names), 'unbound configure values')
    _require(all(values[n] for n in names[:4]), 'empty required identity')
    _require(re.fullmatch(r'[0-9a-f]{64}',values['MCKERNEL_M14_EXPECTED_MAKE_SHA256']) is not None, 'make hash malformed')
    _require(values['UNAME_R']==values['MCKERNEL_M14_EXPECTED_UNAME_R'], 'uname mismatch')
    _require(values['KBUILD_MAKE_FLAGS']==values['MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS'], 'flags mismatch')
    _require(a==fixed+['-D'+n+'='+values[n] for n in names], 'exact configure argv differs')
'''
v=v[:start]+replacement+v[end:];(p/'validator.corrected.py').write_text(v)
d=(b/'m14-configure-source-closure-1/driver.closure.py').read_text();key="    write_new(EVIDENCE / 'result.json', {'status': 'COMMANDS_EXITED_ZERO',";assert d.count(key)==1
needle="            return 1\n    write_new(EVIDENCE / 'result.json', {'status': 'COMMANDS_EXITED_ZERO',"
insert="""            return 1
        if i == 1:
            # Direct wait alone cannot establish that configure's descendants stopped.
            # No reviewed observer is yet bound, so this successor always defers.
            write_new(EVIDENCE / 'result.json', {'status':'DEFERRED_DESCENDANT_QUIESCENCE_UNKNOWN',
                                                  'last_stage':i, 'container_retirement':'OWNER_REQUIRED'})
            return 1
    write_new(EVIDENCE / 'result.json', {'status': 'COMMANDS_EXITED_ZERO',"""
assert d.count(needle)==1;d=d.replace(needle,insert);(p/'driver.corrected.py').write_text(d)
o=(b/'m14-configure-sdk-v8-source-1/owner.successor.py').read_text();needle="def _sdk13_driver_result(bound,request,manifest):\n";assert o.count(needle)==1;o=o.replace(needle,needle+"    raise OwnerError('SOURCE_ONLY: positive descendant quiescence and acceptance are unbound')\n");(p/'owner.corrected.py').write_text(o)
