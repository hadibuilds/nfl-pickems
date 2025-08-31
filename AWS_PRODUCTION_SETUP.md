# AWS Production Setup Guide for NFL Pickems

This guide walks you through setting up AWS infrastructure for your NFL Pickems app with custom domain `pickems.fun` for 12 users (private beta).

## Architecture Options

### Option A: Full AWS (Recommended for Production)
- **Frontend**: AWS Amplify for React app hosting
- **Backend**: AWS App Runner for Django API
- **Database**: AWS RDS PostgreSQL
- **Storage**: AWS S3 for user avatars
- **Domain**: Route 53 for DNS management

### Option B: Hybrid (Current Setup)
- **Frontend**: AWS Amplify for React app hosting  
- **Backend**: Render.com (existing setup)
- **Storage**: AWS S3 for user avatars
- **Domain**: Route 53 for DNS management

**This guide covers both options - choose based on your preference.**

## Prerequisites
- AWS Account with billing enabled
- Domain `pickems.fun` purchased from any registrar
- Access to your existing Render.com backend

---

## Step 1: Domain Setup with Route 53

### 1.1 Create Hosted Zone
1. Go to **Route 53** in AWS Console
2. Click **Create hosted zone**
3. Enter domain name: `pickems.fun`
4. Type: **Public hosted zone**
5. Click **Create hosted zone**

### 1.2 Update Domain Nameservers
1. Copy the 4 nameservers from your new hosted zone (they look like `ns-123.awsdns-12.com`)
2. Go to your domain registrar (where you bought `pickems.fun`)
3. Update nameservers to use the AWS Route 53 nameservers
4. **Wait 24-48 hours for DNS propagation**

---

## Step 2: S3 Bucket for Avatar Storage

### 2.1 Create S3 Bucket
1. Go to **S3** in AWS Console
2. Click **Create bucket**
3. Bucket settings:
   - **Bucket name**: `nfl-pickems-avatars-prod` (must be globally unique)
   - **AWS Region**: `us-east-1` (recommended for Amplify compatibility)
   - **Bucket type**: **General purpose** (not Directory)
   - **Object Ownership**: **ACLs disabled** (recommended)
   - **Block Public Access**: **Keep all 4 checkboxes CHECKED** (important for security)
   - **Bucket Versioning**: **Disable** (not needed for avatars)
   - **Server-side encryption**: **Enable with Amazon S3 managed keys (SSE-S3)**
4. Click **Create bucket**

### 2.2 Create IAM User for S3 Access
1. Go to **IAM** > **Users**
2. Click **Create user**
3. User name: `nfl-pickems-s3-user`
4. **Don't** check "Provide user access to AWS Management Console"
5. Click **Next**

### 2.3 Create IAM Policy for S3 Access
1. In the permissions step, click **Attach policies directly**
2. Click **Create policy**
3. Switch to **JSON** tab and paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::nfl-pickems-avatars-prod/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::nfl-pickems-avatars-prod"
        }
    ]
}
```

4. Click **Next**
5. Policy name: `NFLPickemsS3Policy`
6. Click **Create policy**

### 2.4 Attach Policy to User
1. Go back to user creation
2. Search for `NFLPickemsS3Policy` and check it
3. Click **Next** > **Create user**

### 2.5 Create Access Keys
1. Click on your newly created user
2. Go to **Security credentials** tab
3. Click **Create access key**
4. Select **Application running outside AWS**
5. Click **Next** > **Create access key**
6. **IMPORTANT**: Copy and save:
   - Access key ID
   - Secret access key
   - You won't see the secret key again!

---

## Step 3A: Backend with AWS App Runner (Full AWS Option)

### 3A.1 Create RDS PostgreSQL Database
1. Go to **RDS** in AWS Console
2. Click **Create database**
3. Choose **Standard create**
4. Engine: **PostgreSQL**
5. Version: **Latest stable** (14.x or 15.x)
6. Template: **Free tier** (if eligible) or **Production**
7. DB instance identifier: `nfl-pickems-db`
8. Master username: `nfl_pickems_admin`
9. Master password: **Auto generate** (save this!)
10. Instance class: **db.t3.micro** (sufficient for 12 users)
11. Storage: **20 GB** General Purpose SSD
12. **Enable** storage autoscaling, max 100 GB
13. Connectivity:
    - **Don't connect to EC2**
    - VPC: **Default**
    - Subnet group: **default**
    - **Yes** to public access (needed for App Runner)
    - VPC security group: **Create new**
    - Security group name: `nfl-pickems-db-sg`
14. Database authentication: **Password authentication**
15. Additional configuration:
    - Initial database name: `nfl_pickems`
    - **Enable** automated backups (7 days retention)
16. Click **Create database**
17. **Save the auto-generated password!**

### 3A.2 Configure Database Security Group
1. Go to **EC2** > **Security Groups**
2. Find `nfl-pickems-db-sg`
3. Edit **Inbound rules**
4. Add rule:
   - Type: **PostgreSQL**
   - Port: **5432**
   - Source: **Anywhere IPv4** (0.0.0.0/0)
   - Description: `App Runner access`

### 3A.3 Create App Runner Service
1. Go to **App Runner** in AWS Console
2. Click **Create service**
3. Source: **Source code repository**
4. Connect to GitHub (authorize AWS to access your repo)
5. Repository: Select your `nfl-pickems` repo
6. Branch: `main`
7. Deployment trigger: **Automatic**
8. Configuration file: **Use configuration file** (we'll create this)
9. Click **Next**

### 3A.4 Create App Runner Configuration File
In your backend root directory, create `apprunner.yaml`:

```yaml
version: 1.0
runtime: python3.11
build:
  commands:
    build:
      - echo "Build started"
      - pip install -r requirements.txt
      - python manage.py collectstatic --noinput
      - echo "Build completed"
run:
  runtime-version: python3.11
  command: gunicorn nfl_pickems.wsgi:application --bind 0.0.0.0:8000
  network:
    port: 8000
    env: PORT
  env:
    - name: DJANGO_SETTINGS_MODULE
      value: nfl_pickems.settings.prod
```

### 3A.5 Configure App Runner Environment Variables
In App Runner service configuration, add these environment variables:

```bash
# Django Settings
DEBUG=False
DJANGO_SETTINGS_MODULE=nfl_pickems.settings.prod
SECRET_KEY=your_django_secret_key_here

# Database (get from RDS endpoint)
DATABASE_URL=postgresql://nfl_pickems_admin:your_db_password@your-rds-endpoint.region.rds.amazonaws.com:5432/nfl_pickems

# AWS S3 Configuration
USE_CLOUD_STORAGE=True
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_STORAGE_BUCKET_NAME=nfl-pickems-avatars-prod
AWS_S3_REGION_NAME=us-east-1

# Domain Settings
ALLOWED_HOSTS=pickems.fun,www.pickems.fun,your-apprunner-url.region.awsapprunner.com
CORS_ALLOWED_ORIGINS=https://pickems.fun,https://www.pickems.fun
CSRF_TRUSTED_ORIGINS=https://pickems.fun,https://www.pickems.fun

# Email Configuration
EMAIL_HOST_USER=your_gmail_here
EMAIL_HOST_PASSWORD=your_app_password_here
```

### 3A.6 Custom Domain for App Runner
1. In your App Runner service, go to **Custom domains**
2. Click **Link domain**
3. Domain name: `api.pickems.fun`
4. Copy the CNAME record values
5. Go to Route 53, create CNAME record:
   - Name: `api`
   - Value: The App Runner CNAME target
6. Wait for SSL certificate validation (15-30 minutes)

## Step 3B: Backend Environment Variables (Render.com - Hybrid Option)

Add these environment variables to your Render.com backend service:

```bash
# AWS S3 Configuration
USE_CLOUD_STORAGE=True
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_STORAGE_BUCKET_NAME=nfl-pickems-avatars-prod
AWS_S3_REGION_NAME=us-east-1

# Production Domain Settings (update existing)
ALLOWED_HOSTS=pickems.fun,www.pickems.fun,nfl-pickems.onrender.com
CORS_ALLOWED_ORIGINS=https://pickems.fun,https://www.pickems.fun
CSRF_TRUSTED_ORIGINS=https://pickems.fun,https://www.pickems.fun
```

### 3.1 Update Django Settings
Your existing `prod.py` file should already handle these variables. Verify it includes:

```python
# Media files for production
if config('USE_CLOUD_STORAGE', default=False, cast=bool):
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = 'private'  # IMPORTANT: Keep avatars private
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
```

---

## Step 4: Frontend Setup with AWS Amplify

### 4.1 Create Amplify App
1. Go to **AWS Amplify** in AWS Console
2. Click **Create new app** > **Host web app**
3. Select **Deploy without Git provider** (we'll use manual deployment initially)
4. App name: `nfl-pickems-frontend`
5. Environment name: `prod`
6. Click **Save and deploy**

### 4.2 Build Your Frontend
In your frontend directory, create production build:

```bash
cd frontend
npm install
npm run build
```

### 4.3 Upload Build to Amplify
1. Zip your `dist` folder: `zip -r dist.zip dist/`
2. In Amplify console, drag and drop `dist.zip`
3. Wait for deployment to complete

### 4.4 Configure Custom Domain
1. In your Amplify app, go to **Domain management**
2. Click **Add domain**
3. Domain: `pickems.fun`
4. Click **Configure domain**
5. Add subdomains:
   - `pickems.fun` (root)
   - `www.pickems.fun` (redirect to root)
6. Click **Save**
7. **Wait 15-45 minutes** for SSL certificate creation and DNS setup

### 4.5 Environment Variables for Frontend
In Amplify app settings > Environment variables, add:

```bash
VITE_API_URL=https://nfl-pickems.onrender.com
```

### 4.6 Build Settings (Optional - for Git integration later)
If you want to connect GitHub later, use this build spec:

```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm install
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: frontend/dist
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
```

---

## Step 5: DNS Configuration

### 5.1 Create A Record for Backend (if needed)
If you want `api.pickems.fun` to point to your Render backend:

1. In Route 53 hosted zone for `pickems.fun`
2. Click **Create record**
3. Record name: `api`
4. Record type: **CNAME**
5. Value: `nfl-pickems.onrender.com`
6. TTL: `300`
7. Click **Create records**

Then update your frontend environment variable:
```bash
VITE_API_URL=https://api.pickems.fun
```

---

## Step 6: Security and Performance (Optional but Recommended)

### 6.1 CloudFront Distribution
1. Go to **CloudFront**
2. Click **Create distribution**
3. Origin domain: Your Amplify domain (e.g., `main.d123456789.amplifyapp.com`)
4. Viewer protocol policy: **Redirect HTTP to HTTPS**
5. Cache behavior: **CachingOptimized**
6. Create distribution

### 6.2 WAF (Web Application Firewall) - Optional for 12 users
For a small private league, WAF might be overkill, but if you want basic protection:

1. Go to **AWS WAF**
2. Create web ACL with basic rules:
   - AWS managed rules for common attacks
   - Rate limiting (e.g., 1000 requests per 5 minutes per IP)

---

## Step 7: Testing and Validation

### 7.1 Test Checklist
- [ ] `https://pickems.fun` loads your React app
- [ ] `https://www.pickems.fun` redirects to root domain
- [ ] User registration works
- [ ] Avatar upload works and files appear in S3
- [ ] Avatar display works (private S3 serving through Django)
- [ ] CORS works between frontend and backend
- [ ] SSL certificates are valid (no browser warnings)

### 7.2 Monitor Costs
- **S3**: ~$0.10/month for 12 users (avatars only)
- **Route 53**: $0.50/month per hosted zone
- **Amplify**: ~$1/month for small site
- **Total estimated**: ~$2-5/month

---

## Step 8: Environment Variables Summary

### Backend (Render.com)
```bash
# Existing
DEBUG=False
DATABASE_URL=your_postgres_url
SECRET_KEY=your_secret_key
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_app_password

# New AWS Settings
USE_CLOUD_STORAGE=True
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=nfl-pickems-avatars-prod
AWS_S3_REGION_NAME=us-east-1

# Updated Domain Settings
ALLOWED_HOSTS=pickems.fun,www.pickems.fun,nfl-pickems.onrender.com
CORS_ALLOWED_ORIGINS=https://pickems.fun,https://www.pickems.fun
CSRF_TRUSTED_ORIGINS=https://pickems.fun,https://www.pickems.fun
```

### Frontend (Amplify)

For **Full AWS** (Option A):
```bash
VITE_API_URL=https://api.pickems.fun
```

For **Hybrid** (Option B):
```bash
VITE_API_URL=https://nfl-pickems.onrender.com
# OR if using api subdomain:
# VITE_API_URL=https://api.pickems.fun
```

---

## Troubleshooting

### Common Issues
1. **DNS not resolving**: Wait 24-48 hours after nameserver changes
2. **CORS errors**: Ensure CORS_ALLOWED_ORIGINS matches your exact domain
3. **Avatar uploads failing**: Check S3 permissions and AWS credentials
4. **SSL certificate pending**: Can take 15-45 minutes, check Route 53 records

### Useful Commands
```bash
# Test DNS propagation
nslookup pickems.fun

# Test CORS from browser console
fetch('https://nfl-pickems.onrender.com/api/health/', {credentials: 'include'})

# Check S3 bucket policy
aws s3api get-bucket-policy --bucket nfl-pickems-avatars-prod
```

---

## Cost Comparison for 12 Users

### Full AWS (Option A) - Monthly Costs:
- **App Runner**: ~$7-15/month (includes 2 vCPU, 4GB RAM)
- **RDS db.t3.micro**: ~$12-15/month (PostgreSQL)
- **S3**: ~$0.10/month (avatars only)
- **Route 53**: $0.50/month (hosted zone)
- **Amplify**: ~$1/month (small site)
- **Total**: ~$20-32/month

### Hybrid (Option B) - Monthly Costs:
- **Render.com**: ~$7/month (starter plan)
- **S3**: ~$0.10/month (avatars only)
- **Route 53**: $0.50/month (hosted zone)
- **Amplify**: ~$1/month (small site)
- **Total**: ~$8-10/month

## Cost Optimization for 12 Users

- Use S3 Intelligent Tiering for rarely accessed avatars
- Enable S3 lifecycle policies to delete old avatar versions
- Monitor CloudWatch for usage patterns
- Consider Reserved Capacity if usage grows
- **For Full AWS**: RDS has free tier (750 hours/month) if you qualify

## Why Choose Full AWS (Option A)?

### Pros:
- **Better reliability**: AWS SLA vs Render uptime
- **Auto-scaling**: Handles traffic spikes better
- **Integrated monitoring**: CloudWatch metrics included
- **Professional setup**: Everything in one AWS ecosystem
- **Future-proof**: Easy to add CloudFront, WAF, etc.

### Cons:
- **Higher cost**: ~$20 more per month
- **More complex**: More AWS services to manage

---

This setup will give you a professional production environment for your private beta with 12 users, with room to scale as needed!