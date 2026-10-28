"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One additive recipe coherence correction; original sources/recipes remain immutable.
"""
from pathlib import Path
import ast
import copy
import hashlib
import json

HERE=Path(__file__).resolve().parent
PINS=json.loads((HERE/'INPUTS.json').read_bytes())


def require(ok,why):
    if not ok:raise ValueError(why)


def ref(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def read(row):
    require(ref(row['path'])==row,'exact BYTE input: '+row['path'])
    return Path(row['path']).read_bytes()


def checked(row):return json.loads(read(row))


def actual_encoder():
    # Extract only the existing pure encoder; never import/run the source module.
    tree=ast.parse(read(PINS['canonical_encoder_source']))
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='canonical_bytes']
    require(len(nodes)==1,'one actual canonical_bytes implementation')
    namespace={'json':json}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),PINS['canonical_encoder_source']['path'],'exec'),namespace)
    encoder=namespace['canonical_bytes']
    # Actual accepted115 command metadata provides four independently retained
    # encoding vectors. This is the actual field encoding, not a new format.
    accepted=checked(PINS['actual115_profile'])
    for command in accepted['exact_commands']:
        require(hashlib.sha256(encoder(command['argv'])).hexdigest()==command['argv_sha256'],
                'accepted115 exact command hash encoding')
    require(len(accepted['exact_commands'])==4,'four accepted encoding vectors')
    return encoder


def validate_recipe(recipe,encoder):
    commands=recipe['ordered_commands']
    require(len(commands)==4,'four-command recipe')
    for command in commands:
        argv=command['argv']
        require(type(argv) is list and all(type(arg) is str and arg for arg in argv),'literal argv')
        require(hashlib.sha256(encoder(argv)).hexdigest()==command['argv_sha256'],'current argv/hash mismatch')
    environment='MCKERNEL_F06_CLONE_CPUID_METADATA_RS='
    paths=[word[len(environment):] for word in commands[0]['argv'] if word.startswith(environment)]
    require(len(paths)==1,'one actual Rust metadata path')
    output=str(Path(paths[0]).parent)
    require(output=='/work/output/build/kernel/rust/f06-origin','actual generated metadata output directory')
    require(recipe['prerequisite_origin']['output']==output,'origin output matches Rust metadata')
    require('-I'+output in commands[2]['argv'],'origin output matches arch include')
    return output


def corrected():
    original=checked(PINS['original117_recipe']);old116=checked(PINS['historical116_recipe'])
    encoder=actual_encoder();recipe=copy.deepcopy(original)
    history=[]
    for index,(command,old) in enumerate(zip(recipe['ordered_commands'],old116['ordered_commands'])):
        before=command['argv_sha256'];fresh=hashlib.sha256(encoder(command['argv'])).hexdigest()
        historical_actual=hashlib.sha256(encoder(old['argv'])).hexdigest()
        history.append(dict(index=index,historical116_recorded_argv_sha256=old['argv_sha256'],
                            historical116_recomputed_argv_sha256=historical_actual,
                            historical116_recorded_hash_matches_its_argv=old['argv_sha256']==historical_actual,
                            original117_copied_argv_sha256=before,current117_argv_sha256=fresh,
                            argv_changed_from116=command['argv']!=old['argv']))
        command['argv_sha256']=fresh
    require([r['index'] for r in history if r['argv_changed_from116']]==[0,2], 'only intended two argv changes')
    require(all(r['current117_argv_sha256']!=r['historical116_recorded_argv_sha256'] for r in history if r['index'] in (0,2)),
            'both current117 changed command hashes must be new')
    recipe['prerequisite_origin']['output']='/work/output/build/kernel/rust/f06-origin'
    recipe['command_hash_history']=history
    recipe['recipe_correction']=dict(original117_recipe=PINS['original117_recipe'],historical116_recipe=PINS['historical116_recipe'],
                                    encoding_source=PINS['canonical_encoder_source'],accepted_encoding_vectors=PINS['actual115_profile'],
                                    scope='Fresh argv_sha256 fields plus exact origin-output path only; source postimages and argv unchanged',
                                    actual_build_consumer=PINS['actual116_runner'],
                                    runtime_hash_consumption='Runner commands_for_plan consumes exact argv/cwd/new_output; argv_sha256 remains recipe consistency metadata, verified here.',
                                    candidate_origin_profile_argv_sha256='Historical copied metadata only; exact derive producer authenticates complete profile BYTE hash and argv, never reads this ancillary field. Seven reviewed source postimages stay unchanged.')
    validate_recipe(recipe,encoder)
    # Reverse precisely the two metadata/path corrections and additive history
    # fields to prove no command or unrelated recipe field changed.
    reverse=copy.deepcopy(recipe)
    for now,old in zip(reverse['ordered_commands'],original['ordered_commands']):now['argv_sha256']=old['argv_sha256']
    reverse['prerequisite_origin']['output']=original['prerequisite_origin']['output']
    reverse.pop('command_hash_history');reverse.pop('recipe_correction')
    require(reverse==original,'bounded metadata/path correction only')
    source_map=checked(PINS['seven_source_map'])
    for row in source_map['writes']:read(row['postimage'])
    require(len(source_map['writes'])==7,'seven reviewed source postimages unchanged')
    return recipe,history


if __name__=='__main__':
    recipe,history=corrected()
    (HERE/'MINIMAL-FOUR-COMMAND-CONTINUATION.CORRECTED.NOT-GRANTED.json').write_text(json.dumps(recipe,indent=2)+'\n')
    print(json.dumps(history,indent=2))
