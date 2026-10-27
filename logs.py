"""
logs.py — Centralized logging
AWS Service: Amazon CloudWatch Logs (via watchtower library)
On AWS: streams logs to the /lostfound/app log group in ap-south-1.
Locally (LOCAL_DEV=1): logs to the console with a colored formatter.
"""

import os
import logging


def setup_logging(app):
    """
    Configure Flask app logging.
    On AWS: sends to CloudWatch via watchtower.
    Locally: colorful console output.
    """
    logger = logging.getLogger("lostfound")
    logger.setLevel(logging.INFO)

    if os.environ.get("LOCAL_DEV") == "1":
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        import watchtower
        import boto3

        cw_client = boto3.client("logs", region_name="ap-south-1")
        handler = watchtower.CloudWatchLogHandler(
            log_group="/lostfound/app",
            stream_name="flask-app",
            boto3_client=cw_client,
        )
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(module)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Also attach to Flask's app logger
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    return logger
