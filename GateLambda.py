import re
import os
import json
import asyncio
import shutil
import queue
import logging
import itertools

from collections.abc import Iterable

async def invoke(client, function = 'gate', **payload):
    aws_lambda_call = lambda: client.invoke(
            FunctionName = function, Payload = json.dumps(payload))

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, aws_lambda_call)

async def launch(client, instances, max_concurrent = 1000, **payload):
    """ instances is a list of dict with {'output': ..., 'cmd': ...} """

    # AWS default max concurrency for lambda is 1000 instances (per account)
    # additional concurrent requests will fail
    tasks = queue.Queue(maxsize = max_concurrent)
    results = []

    logging.info(f'Launch {len(instances)} instances with max concurrency of {max_concurrent}')

    async with asyncio.TaskGroup() as tg:
        for inst in instances:
            if tasks.full():
                # wait for the oldest task to complete
                results.append(await tasks.get())

            logging.info(f'Launch instance: {inst}')
            tsk = tg.create_task(invoke(client, **payload, **inst))
            tasks.put(tsk)

    while not tasks.empty():
        results.append(await tasks.get())

    return [json.loads(r['Payload'].read()) for r in results]

def create_cmd_str(output_prefix = None, runs = 1, **pars):
    range_items = {'run': range(runs)}
    const_items = {}

    # split inputs into scalars and iterables
    for k, v in pars.items():
        if isinstance(v, Iterable):
            range_items[k] = v
        else:
            const_items[k] = v

    # get the outer product of all iterables
    # each combination of range pars will become a lambda instance
    outer_prod = itertools.product(*range_items.values())

    instances = []
    for comb in outer_prod:
        inst = dict(zip(range_items.keys(), comb)) | const_items

        out = [f'{k}{v}' for k,v in inst.items()]
        out = '_'.join(out)
        if output_prefix is not None:
            out = os.path.join(output_prefix, out)

        cmd = [f'[{k},{v}]' for k,v in inst.items() if k != 'run']
        if len(cmd) > 0:
            cmd = ''.join(cmd)
            instances.append(
                {'output': out, 'cmd': f'-a {cmd}'})
        else:
            instances.append({'output': out, 'cmd': ''})

    return instances

def upload_gate_dir(s3, dirname, bucket, obj_prefix = '', fmt = 'zip'):
    zipname = os.path.basename(dirname)
    shutil.make_archive(zipname, fmt, root_dir = dirname)

    zipname = f'{zipname}.{fmt}'
    objname = os.path.join(obj_prefix, zipname)

    logging.info(f'Upload {dirname} to {bucket}/{obj_prefix} as {zipname}')
    s3.upload_file(zipname, bucket, objname)
    return objname

def download_gate_dir(s3, bucket, prefix, local_dir = '', cleanup = False):
    logging.info(f'Download {bucket}/{prefix} to {local_dir or "."}')
    objs = s3.list_objects_v2(Bucket = bucket, Prefix = prefix)

    # each result dir should contain the gate output log and one or more data files
    for obj in objs['Contents']:
        objname = obj['Key']
        target = os.path.join(local_dir, objname)

        if not os.path.exists(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target))

        if objname[-1] != '/':
            try:
                s3.download_file(bucket, objname, target)
                if cleanup:
                    s3.delete_object(Bucket = bucket, Key = objname)
            except Exception as e:
                logging.exception(e)

def download_results(s3, bucket, results, cleanup = False):
    logging.info(f'Download results from {len(results)} instances')

    for r in results:
        # return value should be {message: bucket/prefix} if no error
        outdir = r['message']

        if re.match(bucket, outdir):
            download_gate_dir(s3,
                              bucket,
                              os.path.relpath(outdir, bucket),
                              cleanup = cleanup)
        else:
            # lambda will indicate what error occurred
            logging.error(f'Lambda returned with error: {outdir}')

def cleanup_objects(s3, bucket, *keys):
    for key in keys:
        try:
            s3.delete_object(Bucket = bucket, Key = key)
        except Exception as e:
            logging.exception(e)
