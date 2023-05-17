#!/usr/bin/python

import boto3
import asyncio

import GateLambda

if __name__ == "__main__":
    sess = boto3.Session(profile_name = 'godinez')
    lambda_client = sess.client('lambda')
    s3_client = sess.client('s3')

    bucket = 'ucd-godinez-gate'
    gate_macro_dir = './gate'
    gate_main_macro = 'main.mac'
    gate_output_dir = 'output'

    obj_name = GateLambda.upload_gate_dir(
            s3_client, gate_macro_dir, bucket)

    pld = {'bucket':    bucket,
           'main':      gate_main_macro,
           'results':   gate_output_dir,
           'input':     obj_name}

    results_dir_fmt = 'output_{}'

    cmd_str = GateLambda.create_cmd_str(
            activity = 1000,
            duration = 1,
            x = 0.0,
            y = 0.0,
            z = 0.0)

    instances = []
    for i in range(2):
        instances.append({'output': results_dir_fmt.format(i),
                          'cmd': cmd_str})

    results = asyncio.run(GateLambda.launch(lambda_client, instances, **pld))
    GateLambda.download_results_dirs(s3_client, bucket, results)
