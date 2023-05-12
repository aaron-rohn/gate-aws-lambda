#!/usr/bin/python

import os
import boto3
import json
import asyncio
import shutil

def split(data, pred):
    yes, no = [], []
    for d in data:
        if pred(d):
            yes.append(d)
        else:
            no.append(d)
    return yes, no

async def invoke(client, i, **payload):
    payload['output'] = payload['output'].format(i)
    print(payload['output'])

    aws_lambda_call = lambda: client.invoke(
            FunctionName = 'gate', Payload = json.dumps(payload))

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, aws_lambda_call)

async def launch(client, instances, **payload):
    results = await asyncio.gather(
            *[invoke(client, i, **payload) for i in range(instances)],
            return_exceptions = True)

    exceptions, results = split(results, lambda r: isinstance(r, Exception))

    if len(exceptions) > 0:
        print(exceptions)

    for r in results:
        print(json.loads(r['Payload'].read()))

def create_cmd_str(**pars):
    cmd_items = [f'[{k},{v}]' for k,v in pars.items()]
    if len(cmd_items) > 0:
        cmd_items = ''.join(cmd_items)
        return f'-a {cmd_items}'
    else:
        return ''

def upload_gate_dir(dirname, bucket, obj_prefix = '', fmt = 'zip'):
    zipname = os.path.basename(dirname)
    shutil.make_archive(zipname, fmt, root_dir = dirname)

    zipname = f'{zipname}.{fmt}'
    objname = os.path.join(obj_prefix, zipname)

    s3_client.upload_file(zipname, bucket, objname)
    return objname

if __name__ == "__main__":
    sess = boto3.Session(profile_name = 'godinez')
    lambda_client = sess.client('lambda')
    s3_client = sess.client('s3')

    bucket = 'ucd-godinez-gate'
    gate_macro_dir = './gate'
    gate_main_macro = 'main.mac'
    gate_output_dir = 'output'
    results_dir_fmt = 'output_{}'
    instances = 5

    cmd_str = create_cmd_str(
            activity = 1000, duration = 1,
            x = 0.0, y = 0.0, z = 0.0)

    obj_name = upload_gate_dir(gate_macro_dir, bucket)

    pld = {'bucket':    bucket,
           'main':      gate_main_macro,
           'results':   gate_output_dir,
           'input':     obj_name,
           'output':    results_dir_fmt,
           'cmd':       cmd_str}

    asyncio.run(launch(lambda_client, instances, **pld))
