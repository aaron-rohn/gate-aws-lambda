#!/usr/bin/python
import boto3
import json
import asyncio

async def invoke(client, i, **payload):
    print(i)
    loop = asyncio.get_running_loop()
    payload['output'] = f'output_{i}'

    aws_lambda_call = lambda: client.invoke(
            FunctionName = 'gate', Payload = json.dumps(payload))

    return await loop.run_in_executor(None, aws_lambda_call)

async def launch(client, **payload):
    results = await asyncio.gather(*[invoke(client, i, **payload) for i in range(3)])

    for r in results:
        print(json.loads(r['Payload'].read()))

sess = boto3.Session(profile_name = 'godinez')
lambda_client = sess.client('lambda')

pld = {'bucket': 'ucd-godinez-gate',
        'main': 'main.mac',
        'results': 'output',
        'input': 'files.zip',
        'output': '',
        'cmd': ''}

asyncio.run(launch(lambda_client, **pld))
