"""
config.py — Configuration loader
AWS Service: SSM Parameter Store (Systems Manager)
On AWS: reads parameters from /lostfound/* in ap-south-1
Locally (LOCAL_DEV=1): returns safe defaults for development
"""

import os


def get_config():
    """Return configuration dict. Uses SSM on AWS, local defaults otherwise."""
    if os.environ.get("LOCAL_DEV") == "1":
        return {
            "db_host": "localhost",
            "db_user": "root",
            "db_password": "",
            "db_name": "lostfound",
            "bucket_name": "local-uploads",
            "sns_topic_arn": "",
            "secret_key": "dev-secret-key-change-in-production",
            "local_dev": True,
        }

    # On AWS EC2 — read from SSM Parameter Store (no credentials needed; IAM role)
    import boto3

    ssm = boto3.client("ssm", region_name="ap-south-1")

    param_names = [
        "/lostfound/db_host",
        "/lostfound/db_user",
        "/lostfound/db_password",
        "/lostfound/db_name",
        "/lostfound/bucket_name",
        "/lostfound/sns_topic_arn",
        "/lostfound/secret_key",
    ]

    response = ssm.get_parameters(Names=param_names, WithDecryption=True)

    params = {}
    for p in response["Parameters"]:
        # Strip the prefix to get the short key name
        key = p["Name"].split("/")[-1]
        params[key] = p["Value"]

    params["local_dev"] = False
    return params
