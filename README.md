# Campus Lost & Found Portal

A cloud-hosted web app where students report lost or found items with a photo,
search and filter listings, and claim items. An admin reviews and approves
claims. Built as a Cloud Computing mini project on AWS (Mumbai, ap-south-1).

## Features
- Register and log in (passwords hashed with werkzeug)
- Report lost or found items with photo upload (images only, max 5 MB)
- Search and filter by status (All / Lost / Found / Claimed)
- Claim an item with a message; admin approves or rejects
- Admin dashboard with stats and a claims table
- Email notification to the admin on every new claim
- Dark mode, responsive layout, drag-and-drop photo upload

## Architecture
Browser -> EC2 (Flask + gunicorn, public subnet) -> RDS MySQL (private subnet),
S3 (photos), SNS (email alerts), SSM Parameter Store (secrets), CloudWatch (logs + alarm).

| AWS service | Role in the project |
|---|---|
| VPC + Security Groups | Custom network; the database only accepts traffic from the web security group |
| EC2 | Runs the Flask app |
| RDS (MySQL) | Stores users, items and claims in private subnets |
| S3 | Private photo bucket; photos are served through presigned URLs |
| IAM | EC2 role with least-privilege access (no access keys in code) |
| SSM Parameter Store | DB credentials, bucket name, SNS ARN and secret key |
| CloudWatch | App logs, ERROR metric filter and alarm |
| SNS | Emails on new claims and on alarms |
| Budgets | $5 monthly cost alert |

## Project structure
| File | Purpose | Owner |
|---|---|---|
| `app.py` | Flask routes | Srushti |
| `storage.py` | S3 upload and presigned URLs | Srushti |
| `db.py`, `config.py`, `schema.sql` | Database access, settings from SSM, tables | Adhija |
| `logs.py`, `notify.py` | CloudWatch logging, SNS notifications | Sancia |
| `templates/`, `static/` | Frontend (HTML, CSS, JS) | Srushti |

## Run locally (no AWS needed)
LOCAL_DEV=1 uses SQLite and a local `uploads/` folder.

    pip install -r requirements.txt
    LOCAL_DEV=1 python app.py

On Windows PowerShell: `$env:LOCAL_DEV=1; python app.py`

## Run on EC2
1. Create the VPC, security groups, EC2 instance, RDS, S3 bucket, SNS topic and IAM role.
2. Add the `/lostfound/*` parameters in SSM Parameter Store
   (db_host, db_user, db_password, db_name, bucket_name, sns_topic_arn, secret_key).
3. On the instance:

       sudo dnf install python3-pip git -y
       git clone <repo-url> && cd <repo>
       sudo pip3 install -r requirements.txt
       sudo python3 -m gunicorn -w 2 -b 0.0.0.0:80 app:app

4. Open `http://<EC2-PUBLIC-IP>`.

## Useful routes
- `/health` returns `ok`
- `/simulate-error` logs an ERROR and returns a 500, used to demo the CloudWatch alarm

## Security notes
- No credentials in the code; secrets are read from SSM at start-up
- RDS has no public access; only `web-sg` can reach port 3306
- S3 bucket is private; direct URLs return AccessDenied
- All SQL uses parameterized queries

## Team
- **Srushti**: IAM, S3, website
- **Adhija**: RDS, SSM Parameter Store
- **Sancia**: CloudWatch, SNS, Budget

## Cleanup
Stop or delete EC2 and RDS after the demo to avoid charges.
