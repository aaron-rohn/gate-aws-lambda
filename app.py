import os
import json
import shutil
import subprocess
import boto3
import tempfile
import logging

s3 = boto3.client('s3')
logging.getLogger().setLevel(logging.INFO)

def handler(event, context):
    try:
        if 'body' in event:
            event = json.loads(event['body'])

        main    = event['main']
        args    = event['cmd']
        results = event['results']

        bucket  = event['bucket']
        obj_in  = event['input']
        obj_out = event['output']

    except Exception as e:
        logging.exception('Error decoding request body')
        return {'message': f'Invalid request body {e} {event}'}

    gate_cmd = f'Gate {args} {main}'
    cmd = ['/bin/bash', '-c', f'source /etc/mybashrc && {gate_cmd} &> {results}/output.log']

    logging.info(f'Input:  {bucket}/{obj_in}')
    logging.info(f'Output: {bucket}/{obj_out}')
    logging.info(f'Run \'{gate_cmd}\' and store results to \'{results}\'')

    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        os.makedirs(results)

        try:
            s3.download_file(bucket, obj_in, 'files.zip')
            shutil.unpack_archive('files.zip')
        except Exception as e:
            logging.exception('Failed to download or unpack specified archive')
            return {'message': f'Error retrieving files ({e})'}

        logging.info(f'Archive contents: {os.listdir()}')

        timeout = context.get_remaining_time_in_millis() / 1000
        timeout = None if timeout <= 1 else timeout - 1

        try:
            subprocess.run(cmd, timeout = timeout)
        except subprocess.TimeoutExpired:
            logging.exception('Simulation process timed out')
            return {'message': 'Timeout expired, process killed'}
        except subprocess.CalledProcessError as e:
            logging.exception('Simulation returned non-zero exit code')
            return {'message': f'Command returned with non-zero exit ({e})'}

        logging.info(f'Files generated: {os.listdir(results)}')

        for root, dirs, files in os.walk(results):
            for name in files:
                s3.upload_file(
                        os.path.join(root, name),
                        bucket, os.path.join(obj_out, name))

    return {'message': f'{bucket}/{obj_out}'}
