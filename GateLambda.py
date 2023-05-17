import re
import os
import json
import asyncio
import shutil

async def invoke(client, **payload):
    aws_lambda_call = lambda: client.invoke(
            FunctionName = 'gate', Payload = json.dumps(payload))
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, aws_lambda_call)

async def launch(client, instances, **payload):
    """ instances is a list of dict with {'output': ..., 'cmd': ...} """
    async with asyncio.TaskGroup() as tg:
        tsk = [tg.create_task(
            invoke(client, **payload, **inst)) for inst in instances]

    results = [t.result() for t in tsk]
    return [json.loads(r['Payload'].read()) for r in results]

def create_cmd_str(**pars):
    cmd_items = [f'[{k},{v}]' for k,v in pars.items()]
    if len(cmd_items) > 0:
        cmd_items = ''.join(cmd_items)
        return f'-a {cmd_items}'
    else:
        return ''

def upload_gate_dir(s3, dirname, bucket, obj_prefix = '', fmt = 'zip'):
    zipname = os.path.basename(dirname)
    shutil.make_archive(zipname, fmt, root_dir = dirname)

    zipname = f'{zipname}.{fmt}'
    objname = os.path.join(obj_prefix, zipname)

    s3.upload_file(zipname, bucket, objname)
    return objname

def download_gate_dir(s3, bucket, prefix, local_dir = ''):
    objs = s3.list_objects_v2(Bucket = bucket, Prefix = prefix)

    for obj in objs['Contents']:
        objname = obj['Key']
        target = os.path.join(local_dir, objname)

        if not os.path.exists(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target))

        if objname[-1] != '/':
            s3.download_file(bucket, objname, target)

def download_results_dirs(s3, bucket, results):
    for r in results:
        outdir = r['message']
        if re.match(bucket, outdir):
            print(f'Downloading results: {outdir}')
            download_gate_dir(s3, bucket,
                              os.path.relpath(outdir, bucket))
        else:
            print(f'Lambda returned with error: {outdir}')
