#!/usr/bin/python

import boto3
import asyncio
import logging
import datetime

import GateLambda

logging.basicConfig(level = logging.INFO)

sess = boto3.Session(profile_name = 'godinez')
lambda_client = sess.client('lambda')
s3_client = sess.client('s3')

# the s3 bucket for storing inputs and outputs
bucket = 'ucd-godinez-gate'

# the local directory containing all the necessary gate macros
gate_macro_dir = './gate'

# the name of the main macro
gate_main_macro = 'main.mac'

# the folder that the gate macros expect to store results
gate_output_dir = 'output'


# zip and upload the local macro directory to s3
# returns the path to the file with the lambda will download
obj_name = GateLambda.upload_gate_dir(
        s3_client, gate_macro_dir, bucket)

# mandatory parameters for the lambda function, which are
# constant across all invocations
pld = {'bucket':    bucket,
       'main':      gate_main_macro,
       'results':   gate_output_dir,
       'input':     obj_name}

# create the varying parameters passed to each instance of lambda

prefix_dir = datetime.datetime.now().isoformat(timespec = 'seconds')
results_dir_fmt = f'run_{prefix_dir}/output_{{}}'

cmd_str = GateLambda.create_cmd_str(
        activity = 1000,
        duration = 10,
        x = 0.0,
        y = 0.0,
        z = 0.0)

instances = []
for i in range(5):
    output_name_i = results_dir_fmt.format(i)
    cmd_str_i = cmd_str

    instances.append({'output': output_name_i,
                      'cmd': cmd_str_i})

# invoke lambda and download results

results = asyncio.run(
        GateLambda.launch(lambda_client, instances, **pld))

GateLambda.download_results(s3_client, bucket, results)
