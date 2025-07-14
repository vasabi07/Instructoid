import boto3
from botocore.client import Config
import httpx
import os
import uuid
async def get_file(file_key: str,expires_in: int = 60):
    os.makedirs("./content", exist_ok=True)
    session = boto3.session.Session()
    r2 = session.client(
        service_name='s3',
        region_name='auto',
        endpoint_url=os.environ['R2_ENDPOINT'],
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4'),
    )
    signed_url = r2.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': os.environ['R2_BUCKET'],
            'Key': file_key,
        },
        ExpiresIn=expires_in
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(signed_url)
        filename = f"{file_key}.pdf"
        output_path = f"./content/{filename}"
    if response.status_code == 200:
        with open(output_path,"wb") as f:
            f.write(response.content)
        return filename
    else:
        raise Exception(f"Failed to download file: {response.status_code} - {response.text}")

async def get_video(file_key: str, expires_in: int = 60):
    session = boto3.session.Session()
    r2 = session.client(
        service_name='s3',
        region_name='auto',
        endpoint_url=os.environ['R2_ENDPOINT'],
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4'),
    )
    signed_url = r2.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': os.environ['R2_BUCKET'],
            'Key': file_key,
        },
        ExpiresIn=expires_in
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(signed_url)
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Failed to download video: {response.status_code} - {response.text}")

def create_file_key(filename: str) -> str:
    base_name = os.path.basename(filename)
    unique_id = uuid.uuid4().hex
    return f"{unique_id}_{base_name}"

async def upload_video(filename: str, video_data: bytes, expires_in: int = 3600):
    session = boto3.session.Session()
    r2 = session.client(
        service_name='s3',
        region_name='auto',
        endpoint_url=os.environ['R2_ENDPOINT'],
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4'),
    )
    file_key = create_file_key(filename)
    signed_url = r2.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': os.environ['R2_BUCKET'],
            'Key': file_key,
        },
        ExpiresIn=expires_in
    )
    
    async with httpx.AsyncClient() as client:
        response = await client.put(signed_url, content=video_data)
        
    if response.status_code == 200:
        return {"status": "success", "file_key": file_key, "message": f"Video uploaded successfully to {file_key}"}
    else:
        raise Exception(f"Failed to upload video: {response.status_code} - {response.text}")