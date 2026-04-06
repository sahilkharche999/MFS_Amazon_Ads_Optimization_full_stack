import boto3
import os
import json
import tempfile
from pathlib import Path
from typing import Optional

# S3 Configuration
S3_BUCKET = os.environ.get("S3_BUCKET")
S3_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_PUBLIC_URL = f"https://{S3_BUCKET}.s3.amazonaws.com"

# Initialize S3 client (allowing for missing credentials during startup to prevent crash if not yet set)
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=S3_REGION
    )
except Exception as e:
    print(f"[S3 INIT ERROR] Credentials likely missing: {e}")
    s3_client = None

def get_content_type(file_path: Path) -> str:
    if file_path.suffix == '.mp4':
        return 'video/mp4'
    elif file_path.suffix == '.png':
        return 'image/png'
    elif file_path.suffix == '.json':
        return 'application/json'
    else:
        return 'application/octet-stream'

def upload_to_s3(local_path: Path, s3_key: str) -> Optional[str]:
    if not s3_client or not S3_BUCKET:
        print("[S3 ERROR] S3 client or bucket not configured")
        return None
    try:
        content_type = get_content_type(local_path)
        s3_client.upload_file(
            str(local_path),
            S3_BUCKET,
            s3_key,
            ExtraArgs={'ContentType': content_type}
        )
        return f"{S3_PUBLIC_URL}/{s3_key}"
    except Exception as e:
        print(f"[S3 ERROR] {e}")
        return None

def upload_video(local_path: Path, job_id: str, video_index: int) -> Optional[str]:
    return upload_to_s3(local_path, f"videos/{job_id}_video_{video_index}.mp4")

def upload_image(local_path: Path, job_id: str, category: str, index: int) -> Optional[str]:
    return upload_to_s3(local_path, f"images/{job_id}_{category}_{index}.png")

def upload_manifest(job_id: str, manifest_data: dict) -> Optional[str]:
    s3_key = f"manifest/{job_id}.json"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(manifest_data, f, indent=2)
        temp_file_name = f.name
        
    temp_path = Path(temp_file_name)
    url = upload_to_s3(temp_path, s3_key)
    temp_path.unlink()
    return url
