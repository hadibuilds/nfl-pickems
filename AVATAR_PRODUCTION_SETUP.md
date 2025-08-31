# 🔒 **Secure Avatar System - Production Deployment Guide**

This guide provides concrete steps to deploy the secure avatar system in production while maintaining security.

## 🚨 **CRITICAL SECURITY NOTICE**

**Your current setup serves media files publicly without authentication!** This guide fixes that.

---

## 📋 **Prerequisites**

1. **Production Django Environment** (Render, Heroku, AWS, etc.)
2. **AWS S3 Account** (recommended) OR **Nginx/Apache server**
3. **Domain with HTTPS** (required for secure cookies)

---

## 🛠️ **Step-by-Step Implementation**

### **Step 1: Update Dependencies**

Your `requirements.txt` already includes the necessary packages:
```txt
django-storages==1.14.4
boto3==1.35.84
Pillow==11.1.0
```

Install them in production:
```bash
pip install -r requirements.txt
```

### **Step 2: Choose Your Storage Strategy**

#### **Option A: AWS S3 (Recommended)**

**2.1. Create AWS S3 Bucket:**
1. Go to AWS S3 Console
2. Create bucket: `your-app-name-media-files`
3. **Block all public access** ✅ (CRITICAL for security)
4. Enable versioning (optional)

**2.2. Create IAM User:**
1. Go to AWS IAM Console
2. Create user: `your-app-s3-user`
3. Attach policy: `AmazonS3FullAccess` (or custom policy below)
4. Save Access Key ID and Secret Access Key

**Custom S3 Policy (More Secure):**
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
            "Resource": "arn:aws:s3:::your-app-name-media-files/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::your-app-name-media-files"
        }
    ]
}
```

**2.3. Environment Variables:**
Add to your production environment:
```bash
# S3 Configuration
USE_CLOUD_STORAGE=True
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_STORAGE_BUCKET_NAME=your-app-name-media-files
AWS_S3_REGION_NAME=us-east-1
```

#### **Option B: Local Storage with Secure Serving**

**2.1. Environment Variables:**
```bash
USE_CLOUD_STORAGE=False
MEDIA_ROOT=/path/to/secure/media/folder
```

**2.2. Create Secure Media Directory:**
```bash
mkdir -p /var/www/your-app/secure-media
chown www-data:www-data /var/www/your-app/secure-media
chmod 750 /var/www/your-app/secure-media
```

### **Step 3: Update Production Settings**

Your `prod.py` already includes the S3 configuration. Ensure these settings are active:

```python
# In backend/nfl_pickems/settings/prod.py

# The configuration is already added - just ensure environment variables are set
if config('USE_CLOUD_STORAGE', default=False, cast=bool):
    # S3 settings will be automatically applied
    pass
else:
    # Local secure storage settings will be applied
    pass
```

### **Step 4: Secure Media URL Routing**

**Update your main `urls.py`** to use secure media serving:

```python
# In backend/nfl_pickems/urls.py

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('predictions/', include('predictions.urls')),
    path('games/', include('games.urls')),
    path('analytics/', include('analytics.urls')),
]

# REMOVE the old public media serving:
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# REPLACE with secure serving via accounts app:
# Secure media serving is now handled by accounts/urls.py -> SecureMediaView

# Catch-all route for React SPA (must be last)
urlpatterns += [
    re_path(r'^.*$', TemplateView.as_view(template_name="index.html")),
]
```

### **Step 5: Update Frontend Avatar URLs**

The backend is already configured to generate secure URLs. Your frontend will automatically receive secure URLs through the API.

### **Step 6: Nginx Configuration (Local Storage Only)**

If using Option B (local storage), configure Nginx:

```nginx
# In your nginx configuration
server {
    listen 443 ssl;
    server_name yourdomain.com;

    # Your existing configuration...

    # Block direct access to media files
    location /media/ {
        deny all;
        return 404;
    }
    
    # Django handles secure media serving
    location /accounts/secure-media/ {
        proxy_pass http://your-django-app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🚀 **Deployment Steps**

### **For Render Deployment:**

1. **Set Environment Variables:**
   - Go to Render Dashboard → Your Service → Environment
   - Add the variables from Step 2

2. **Deploy:**
   ```bash
   git add .
   git commit -m "Add secure avatar system for production"
   git push
   ```

3. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Collect Static Files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

### **For AWS/Heroku/Other Platforms:**

1. **Set Environment Variables** in your platform's dashboard
2. **Deploy your code**
3. **Run migrations and collectstatic**

---

## 🔍 **Testing Your Secure Setup**

### **1. Test Avatar Upload:**
1. Go to Settings page
2. Upload an avatar
3. Verify it appears immediately (no refresh needed)
4. Check that avatar URLs start with your domain, not raw S3/media URLs

### **2. Test Security:**
1. **Logged Out Test:** Try accessing avatar URLs while logged out - should return 404/403
2. **Direct S3 Test:** Try accessing S3 URLs directly - should be blocked
3. **Cross-User Test:** User A shouldn't be able to access User B's avatar URL directly

### **3. Test Performance:**
1. Avatar uploads should be fast
2. Avatar display should be instant after upload
3. No broken image links

---

## 🛡️ **Security Features Implemented**

✅ **Private S3 bucket** - No public access  
✅ **Authentication required** - Only logged-in users can access avatars  
✅ **Path validation** - Prevents directory traversal attacks  
✅ **File type validation** - Only images allowed  
✅ **Size limits** - 5MB maximum  
✅ **Automatic cleanup** - Old avatars are deleted  
✅ **HTTPS only** - Secure transmission  
✅ **CSRF protection** - Prevents unauthorized uploads  

---

## 🐛 **Troubleshooting**

### **Avatars not loading:**
- Check environment variables are set
- Verify AWS credentials work
- Check Django logs for errors

### **Upload failing:**
- Check file size (max 5MB)
- Check file type (JPEG, PNG, GIF, WebP only)
- Verify CSRF token is included

### **Permission errors:**
- Check S3 bucket permissions
- Verify IAM user has correct policies
- Check local file system permissions

### **Performance issues:**
- Enable S3 CloudFront for faster delivery
- Check S3 region matches your server region
- Monitor S3 transfer costs

---

## 💰 **Cost Optimization**

### **AWS S3 Costs:**
- **Storage:** ~$0.023/GB/month
- **Requests:** ~$0.0004 per 1,000 requests
- **Data Transfer:** Free for first 1GB/month

### **Expected Costs for 1000 Users:**
- **Storage (50MB average):** ~$1.15/month
- **Uploads (5/user/month):** ~$0.002/month
- **Downloads (100/user/month):** ~$0.04/month
- **Total:** ~$1.20/month

---

## ✅ **Final Verification Checklist**

- [ ] Environment variables set in production
- [ ] S3 bucket created and configured (if using S3)
- [ ] IAM user created with correct permissions (if using S3)
- [ ] Django migrations run successfully
- [ ] Avatar upload works without refresh
- [ ] Avatars display across the app (leaderboard, standings, peek)
- [ ] Security test: logged-out users can't access avatar URLs
- [ ] Performance test: uploads are fast and reliable
- [ ] No broken image links anywhere in the app

---

## 🚨 **Security Reminders**

1. **Never commit AWS credentials to code**
2. **Always use HTTPS in production**
3. **Regularly rotate AWS access keys**
4. **Monitor S3 access logs for suspicious activity**
5. **Keep dependencies updated**

---

**🎉 Your secure avatar system is now production-ready!**

For questions or issues, check the Django logs and AWS CloudTrail for detailed error information.