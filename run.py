#!/usr/bin/python
import boto3
import json
import asyncio

async def invoke(client, **kwds):
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, lambda: client.invoke(**kwds))
    #response_pld = json.loads(response['Payload'].read())
    return response

async def launch(client, i, **payload):
    payload['output'] = f'output_{i}'
    return await invoke(client,
                        FunctionName = 'gate',
                        Payload = json.dumps(payload))

async def aggregate(client, **payload):
    results = await asyncio.gather(*[launch(client, i, **payload) for i in range(3)])
    print(results)

sess = boto3.Session(profile_name = 'godinez')
lambda_client = sess.client('lambda')

pld = {'bucket': 'ucd-godinez-gate',
        'main': 'main.mac',
        'results': 'output',
        'input': 'files.zip',
        'output': '',
        'cmd': ''}

asyncio.run(aggregate(lambda_client, **pld))

#response = lambda_client.invoke(
#        FunctionName = 'gate', Payload = json.dumps(pld))
#response_pld = json.loads(response['Payload'].read())
#print(response_pld)
