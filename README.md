# 🏛️ Campus Lost & Found Registry Portal

An official, enterprise-grade cloud-native web application for reporting, cataloging, verifying, and claiming lost & found property across university facilities. Built with **Python Flask + Jinja + vanilla JS** and architected for deployment on **AWS EC2**.

## 🌟 Unique Selling Proposition (USP) Features

| Feature | Description | Value for Campus |
|---------|-------------|------------------|
| **🤖 Heuristic Smart Match Engine** | Cross-matches reported LOST items against active FOUND records using token similarity, category, and location heuristics with match confidence scores (e.g., `85% Match`). | Dramatically speeds up property recovery without manual searching. |
| **📱 Digital QR Asset Tagging** | Dynamically renders a client-side SVG QR code for every logged item encoding its official recovery record. | Instant mobile scanning by campus security and students. |
| **🖨️ Printable Campus Notice Poster** | Built-in `@media print` formatting generates an official university bulletin board poster with QR code, reference ID, and security desk instructions. | Physical notices for campus noticeboards and dorms. |
| **🛡️ Ownership Challenge Verification** | Finders can set a security question (e.g., *"What is the phone lock screen image?"*) which claimants must answer before property release. | Prevents prank or fraudulent claims on valuable items. |
| **🏢 Campus Facility & Category Directory** | Multi-faceted filtering by campus zone (Library, Engineering, Gym, Canteen) and item category. | Enables precision filtering across large campus grounds. |
| **📥 Administrative Audit Log (CSV Export)** | 1-click CSV export of all claim filings, verification answers, and timestamps for security compliance. | Campus Security audit readiness and ledger accountability. |
| **🌗 Formal Institutional UI with Dark Mode** | Clean executive design system built with *Plus Jakarta Sans* & *Inter*, subtle borders, and soft elevation. | Professional university service appearance. |

## ☁️ AWS Architecture

| Service | Purpose |
|---------|---------|
| **EC2** | Hosts the Flask app via Gunicorn |
| **RDS (MySQL)** | Stores users, items, and claims |
| **S3** | Stores uploaded item photos |
| **SNS** | Sends notifications when claims are submitted |
| **CloudWatch** | Centralized logging and alarms |
| **SSM Parameter Store** | Secure configuration management |
| **IAM Role** | EC2 instance role — no hardcoded credentials |

## 🏗 Project Structure

```
├── app.py              # Flask routes & smart matcher endpoints
├── config.py           # SSM Parameter Store / local defaults
├── db.py               # Database layer (RDS MySQL / SQLite with migrations)
├── storage.py          # S3 photo upload / local uploads
├── notify.py           # SNS notifications
├── logs.py             # CloudWatch logging
├── schema.sql          # MySQL table definitions with taxonomy & verification
├── seed.py             # Sample dataset with categories & challenges
├── requirements.txt    # Python dependencies
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Formal university layout & topbar
│   ├── index.html      # Executive hero, multi-filter & USP showcase
│   ├── register.html   # Student single sign-on registration
│   ├── login.html      # Authentication with demo credential helpers
│   ├── items.html      # Faceted registry search & catalog
│   ├── item_new.html   # Property registration wizard
│   ├── item_detail.html# Item dossier, QR tag, challenge & smart matches
│   ├── admin.html      # Security custody console & CSV export
│   └── error.html      # Branded 403, 404, 500 error pages
└── static/
    ├── style.css       # Formal institutional design system stylesheet
    └── app.js          # QR generator, copy reference, print poster & counters
```


## 🚀 Run Locally

**Prerequisites:** Python 3.8+

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed the database with sample data
set LOCAL_DEV=1
python seed.py

# 3. Run the development server
set LOCAL_DEV=1
python app.py
```

Open **http://localhost:5000** in your browser.

### Default Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@campus.edu | admin123 |
| Student | alice@campus.edu | student123 |
| Student | bob@campus.edu | student456 |

## 🌐 Run on AWS EC2

### 1. Launch an EC2 Instance

- AMI: Amazon Linux 2 or Ubuntu 22.04
- Instance type: t2.micro (free tier)
- Security group: allow HTTP (80) and SSH (22)
- Attach an **IAM role** with policies for: RDS, S3, SNS, SSM, CloudWatch Logs

### 2. Store Configuration in SSM Parameter Store

```bash
aws ssm put-parameter --name /lostfound/db_host     --value "your-rds-endpoint" --type String
aws ssm put-parameter --name /lostfound/db_user     --value "admin"             --type String
aws ssm put-parameter --name /lostfound/db_password  --value "your-password"     --type SecureString
aws ssm put-parameter --name /lostfound/db_name     --value "lostfound"         --type String
aws ssm put-parameter --name /lostfound/bucket_name  --value "your-s3-bucket"    --type String
aws ssm put-parameter --name /lostfound/sns_topic_arn --value "arn:aws:sns:..."  --type String
aws ssm put-parameter --name /lostfound/secret_key   --value "random-secret"     --type SecureString
```

### 3. Set Up the Database

```bash
mysql -h your-rds-endpoint -u admin -p < schema.sql
```

### 4. Deploy the App

```bash
# On the EC2 instance:
sudo yum install python3 python3-pip -y   # Amazon Linux
pip3 install -r requirements.txt

# Run with Gunicorn on port 80
sudo gunicorn -w 4 -b 0.0.0.0:80 app:app
```

### 5. (Optional) Run as a systemd service

Create `/etc/systemd/system/lostfound.service`:

```ini
[Unit]
Description=Campus Lost & Found Portal
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/mini-CCL
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:80 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable lostfound
sudo systemctl start lostfound
```

## 🔍 Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Home page with search |
| GET/POST | `/register` | Create account |
| GET/POST | `/login` | Log in |
| GET | `/logout` | Log out |
| GET | `/items` | Browse items (search + filter) |
| GET/POST | `/items/new` | Report lost/found item |
| GET | `/items/<id>` | Item detail + claim form |
| POST | `/items/<id>/claim` | Submit a claim |
| GET | `/admin` | Admin dashboard |
| POST | `/admin/claims/<id>/<action>` | Approve or reject claim |
| GET | `/health` | Health check |
| GET | `/simulate-error` | Trigger 500 for CloudWatch alarm demo |

## 🎨 Design

- **Style:** Playful neo-brutalist with thick borders, hard offset shadows, and bold colors
- **Palette:** Electric yellow, hot pink, mint green, ink black, off-white paper
- **Cards:** Styled as claim tickets / luggage tags with perforated edges and rotated status stamps
- **Features:** Animated marquee, card tilt on hover, button press effects, drag-and-drop upload, confetti on approval, animated stat counters, dark mode toggle
