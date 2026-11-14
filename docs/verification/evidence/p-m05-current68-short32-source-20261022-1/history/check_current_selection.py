"""Three affected production-consumer checks; no archive transformation."""
from pathlib import Path
import copy, importlib.util, json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('actual_current_m05_consumer', HERE / 'stage_m05_two_generation.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
b = s.load_binding()
old = s.authorities(b)
final = s.validate_selection(b['replacements'], old, b)
assert len(final) == 62 and len([k for k in old if old[k] == final[k]]) == 57
assert final['apps/app'] == old['apps/app'] and final['init'] == old['init']
assert final['bin/native-boot'] == old['bin/native-boot']
assert final['bin/native-boot-second'] == old['bin/native-boot-second']
print('PASS real authority/source guards + exact current tuple + preserved M05 workload/helpers/62-member projected map')
wrong = copy.deepcopy(b['replacements'])
wrong['images/mckernel.img']['sha256'] = '053d59b533665eef9d56fe1b348e699d97159e954fbc1fbff973bbe46113f485'
try:
    s.validate_selection(wrong, old, b)
except ValueError as error:
    assert str(error) == 'exact current image/launcher/three-module tuple'
else:
    raise AssertionError('old image tuple accepted')
print('PASS wrong old-image tuple refused by actual selection consumer')
mixed = copy.deepcopy(final)
mixed['modules/mcctrl.ko'] = old['modules/mcctrl.ko']
try:
    s.verify_delta(old, mixed, b)
except ValueError as error:
    assert str(error) == 'exact five final member changes'
else:
    raise AssertionError('mixed old/new module map accepted')
print('PASS mixed old/new replacement map refused by actual final-map consumer')
print(json.dumps(dict(status='PASS_THREE_AFFECTED_SELECTION_AND_MAP_CHECKS',
    cpio_transformations=0, stages=0, compiler=0, native_apps=0, runtime_release=False)))
