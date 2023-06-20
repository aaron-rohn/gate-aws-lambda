#!/usr/bin/python3.11

import botocore
import boto3
import asyncio
import logging
import datetime
import numpy as np

import GateLambda

"""
A note on lambda configuration cost:

Storage is $3.7e-8 per GB-second ->
$0.22 for 10GB x 10min x 1000instances

RAM is $1.67e-5 per GB-second -> 
$10.0 for 10min x 1000instances

370kBq -> 10uCi
10uCi x 1s -> 44.2s runtime

4GB memory is good for about 1e6 simulated events
and requires about 120s to run ($0.008 each)
this figures to about $3.5k to simulate a 20 minute 10mCi scan?
"""

logging.basicConfig(level = logging.INFO)

cfg = botocore.config.Config(
        max_pool_connections = 100,
        read_timeout = 900)
sess = boto3.Session(profile_name = 'godinez')
lambda_client = sess.client('lambda', config = cfg)
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
logging.info(f'Using s3 prefix directory: {s3_prefix_dir}')

# zip and upload the local macro directory to s3
# returns the path to the file with the lambda will download
gate_s3_zip = GateLambda.upload_gate_dir(
        s3_client, gate_macro_dir, bucket, s3_prefix_dir)

max_parallel_runs = 1000
max_counts_per_run = int(10e6)
min_counts_per_run = int(10e3)

fd = open('results.txt', 'w')

for ncounts_total in np.logspace(5, 10, 11):

    if ncounts_total > (max_counts_per_run * max_parallel_runs):
        # we need more than 1000 runs, each with max counts
        nruns = ncounts_total / max_counts_per_run
        ncounts = max_counts_per_run

    elif ncounts_total < (min_counts_per_run*max_parallel_runs):
        # it will be more efficient to use fewer runs with more counts
        nruns = ncounts_total / min_counts_per_run
        ncounts = min_counts_per_run

    else:
        # our run can be broken down well into 1000 jobs
        nruns = max_parallel_runs
        ncounts = ncounts_total / max_parallel_runs

    print(f'\n\nSimulate {nruns*ncounts} counts in {nruns} runs with {ncounts} counts each')

    # create the varying parameters passed to each instance of lambda
    # each 'instance' is a dict with {output: ..., cmd: ...}
    instances = GateLambda.create_cmd_str(
            output_prefix = s3_prefix_dir,
            runs = int(nruns),
            activity = int(ncounts),
            duration = 1,
            x = 1,
            y = 1,
            z = 1)

    # mandatory parameters for the lambda function, which are
    # constant across all invocations
    pld = {'bucket':    bucket,
           'main':      gate_main_macro,
           'results':   gate_output_dir,
           'input':     gate_s3_zip}

    # invoke lambda for each instance
    elapsed, results = asyncio.run(
            GateLambda.launch(lambda_client, instances, **pld))

    print(f'\n\n{ncounts_total}: {elapsed}\n\n')
    fd.write(f'{ncounts_total},{elapsed.total_seconds()}\n')
    fd.flush()

    # download results and remove from s3
    #GateLambda.download_results(s3_client, bucket, results, cleanup = True)
    #GateLambda.cleanup_objects(s3_client, bucket, gate_s3_zip)
