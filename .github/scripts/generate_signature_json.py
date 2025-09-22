import json
import sys

import boto3
import re
from datetime import datetime

client = boto3.client('s3')

environment = sys.argv[1]

bucket_name = f'{environment}-pronom-website'


def list_keys(prefix):
    return [obj['Key'].split('/')[-1] for obj in client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)['Contents']]


def signature_key_to_name(key):
    version = key.split('_')[2].split('.')[0]
    return f'DROID Signature File {version}'


def container_key_to_name(key):
    date_str = key.split('-')[2].split('.')[0]
    date_obj = datetime.strptime(date_str, "%Y%m%d")
    return date_obj.strftime("%d %B %Y")


signatures = sorted(list_keys('signatures/'), key=lambda k: int(re.search(r'(\d+)', k).group(1)))
container_signatures = list_keys('container-signatures/')
latest_signature_file_name = signatures[-1]
latest_container_signature_file_name = container_signatures[-1]
signature_names = [{"name": signature_key_to_name(sig), "location": f"/signatures/{sig}"} for sig in signatures]
container_signature_names = [
    {"name": container_key_to_name(sig), "location": f"/container-signatures/{sig}"} for sig in container_signatures
]
signature_json = {
    "latest_signature": signature_names[-1],
    "latest_container_signature": container_signature_names[-1],
    "signatures": signature_names,
    "container_signatures": container_signature_names,
}
signature_json_bytes = json.dumps(signature_json).encode()

client.put_object(Bucket=bucket_name, Key='signatures.json', Body=signature_json_bytes, ContentType='application/json')
