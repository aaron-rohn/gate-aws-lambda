#!/usr/bin/python3.11

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

# unique s3 prefix for files during computation
s3_prefix_dir = datetime.datetime.now().isoformat(timespec = 'seconds')

# zip and upload the local macro directory to s3
# returns the path to the file with the lambda will download
obj_name = GateLambda.upload_gate_dir(
        s3_client, gate_macro_dir, bucket, s3_prefix_dir)

# mandatory parameters for the lambda function, which are
# constant across all invocations
pld = {'bucket':    bucket,
       'main':      gate_main_macro,
       'results':   gate_output_dir,
       'input':     obj_name}

# create the varying parameters passed to each instance of lambda
instances = GateLambda.create_cmd_str(
        output_prefix = s3_prefix_dir,
        runs = 2,
        activity = 1000,
        duration = 1,
        x = range(2),
        y = range(2),
        z = range(2))

# invoke lambda for each instance
results = asyncio.run(
        GateLambda.launch(lambda_client, instances, **pld))

# download results and remove from s3
GateLambda.download_results(s3_client, bucket, results, cleanup = True)
GateLambda.cleanup_objects(s3_client, bucket, obj_name)
