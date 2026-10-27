"""
storage.py — File upload and retrieval
AWS Service: Amazon S3
On AWS: uploads to an S3 bucket and generates presigned URLs (10 min expiry).
         Uses EC2 IAM role for credentials — NO access keys hardcoded.
Locally (LOCAL_DEV=1): saves files to ./uploads/ and serves them via Flask.
"""

import os
import uuid

_local = os.environ.get("LOCAL_DEV") == "1"
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

# Allowed image MIME types
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB


def _validate_image(file_obj):
    """Check that the upload is an allowed image type and under 5 MB."""
    if file_obj.content_type not in ALLOWED_TYPES:
        raise ValueError("Only JPEG, PNG, GIF, and WebP images are allowed.")
    # Read to check size, then seek back
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(0)
    if size > MAX_SIZE:
        raise ValueError("Image must be smaller than 5 MB.")


def upload_photo(cfg, file_obj):
    """
    Upload a photo and return its storage key.
    On AWS this goes to S3; locally it saves to ./uploads/.
    """
    _validate_image(file_obj)

    ext = os.path.splitext(file_obj.filename)[1].lower() or ".jpg"
    key = f"photos/{uuid.uuid4().hex}{ext}"

    if _local:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        dest = os.path.join(UPLOAD_DIR, key.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        file_obj.save(dest)
    else:
        import boto3
        s3 = boto3.client("s3", region_name="ap-south-1")
        s3.upload_fileobj(
            file_obj,
            cfg["bucket_name"],
            key,
            ExtraArgs={"ContentType": file_obj.content_type},
        )

    return key


def photo_url(cfg, key):
    """
    Return a URL for the given photo key.
    On AWS: a presigned S3 URL valid for 10 minutes.
    Locally: a path served by Flask's static/uploads route.
    """
    if not key:
        return None

    if _local:
        return f"/uploads/{key}"
    else:
        import boto3
        s3 = boto3.client("s3", region_name="ap-south-1")
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": cfg["bucket_name"], "Key": key},
            ExpiresIn=600,  # 10 minutes
        )
