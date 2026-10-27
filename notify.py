"""
notify.py — Notification service
AWS Service: Amazon SNS (Simple Notification Service)
On AWS: publishes a message to the configured SNS topic ARN.
Locally (LOCAL_DEV=1): prints the notification to the console.
"""

import os

_local = os.environ.get("LOCAL_DEV") == "1"


def notify_claim(cfg, item, claimer_email):
    """
    Send a notification when someone claims an item.
    On AWS this publishes to SNS; locally it prints to the console.
    """
    subject = f"New Claim on: {item['title']}"
    message = (
        f"A claim has been submitted!\n\n"
        f"Item: {item['title']}\n"
        f"Description: {item['description']}\n"
        f"Status: {item['status']}\n"
        f"Claimer: {claimer_email}\n\n"
        f"Log in to the admin panel to approve or reject this claim."
    )

    if _local:
        print(f"\n{'='*50}")
        print(f"[SNS NOTIFICATION — LOCAL]")
        print(f"Subject: {subject}")
        print(f"Message:\n{message}")
        print(f"{'='*50}\n")
    else:
        import boto3
        sns = boto3.client("sns", region_name="ap-south-1")
        sns.publish(
            TopicArn=cfg["sns_topic_arn"],
            Subject=subject,
            Message=message,
        )
