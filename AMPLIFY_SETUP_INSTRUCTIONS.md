# AWS Amplify Fresh Setup Instructions for Pickems.fun

## 📦 Deployment Package
**ZIP File Location:** `/Users/hadiabdul-hadi/dev-8-25/nfl-pickems/frontend/pickems-frontend-fresh-20250901-125756.zip` (or similar timestamp)

---

## 🚀 Step-by-Step Amplify Setup

### 1. Navigate to AWS Amplify
1. Go to **AWS Console** → Search for **"Amplify"** → Click **AWS Amplify**
2. You should see the Amplify dashboard (empty since you deleted the old app)

### 2. Create New Amplify App
1. Click **"Create new app"**
2. Select **"Deploy without Git provider"**
3. Click **"Continue"**

### 3. Configure App Settings
**App name:** `pickems-fun`
**Environment name:** `production`
**Method:** Upload your build

### 4. Upload Your Build
1. Click **"Choose files"**
2. Navigate to `/Users/hadiabdul-hadi/dev-8-25/nfl-pickems/frontend/`
3. Select the **`pickems-frontend-fresh-XXXXXX-XXXXXX.zip`** file
4. Click **"Save and deploy"**

### 5. Wait for Deployment (2-3 minutes)
You'll see these phases:
- ✅ **Provision** - Creating infrastructure
- ✅ **Deploy** - Extracting and deploying files  
- ✅ **Verify** - Running health checks

---

## 🌐 Domain Configuration

### 6. Add Custom Domains
1. Once deployment completes, click **"Domain management"** in left sidebar
2. Click **"Add domain"**
3. Enter: **`pickems.fun`**
4. **CRITICAL:** Make sure to **ONLY** add these subdomains:
   - ✅ `pickems.fun` (root domain)
   - ✅ `www.pickems.fun` (www subdomain)
   - ❌ **DO NOT ADD** `api.pickems.fun` (this goes to your backend!)

### 7. Configure Redirects
1. Click **"Rewrites and redirects"** in left sidebar
2. You should see one rule already created:
   ```
   Source: </^[^.]+$/>
   Target: /index.html
   Type: 200 (Rewrite)
   ```
3. If it's not there, click **"Add rule"** and add it manually

---

## 📊 DNS Configuration (Route 53)

### 8. Update DNS Records
**You need to update Route 53 to point to your new Amplify app:**

1. Go to **Route 53** → **Hosted zones** → **pickems.fun**
2. **Delete** any old records pointing to the previous Amplify app
3. **Add** new CNAME records:

```
Type: CNAME
Name: pickems.fun
Value: [NEW_AMPLIFY_DOMAIN].amplifyapp.com

Type: CNAME  
Name: www.pickems.fun
Value: [NEW_AMPLIFY_DOMAIN].amplifyapp.com
```

**To find your new Amplify domain:**
- In Amplify console → Domain management
- Copy the domain ending in `.amplifyapp.com`

### 9. SSL Certificate
Amplify will automatically provision SSL certificates for your domains. This may take 10-30 minutes.

---

## ✅ Verification Steps

### 10. Test Your Deployment

1. **Wait for domains to propagate** (5-15 minutes)
2. **Test URLs:**
   - `https://pickems.fun` ✅ Should load your React app
   - `https://www.pickems.fun` ✅ Should load your React app
   - `https://api.pickems.fun/healthz` ✅ Should return `{"ok": true}`

3. **Test Login/Signup:**
   - Go to `https://pickems.fun/login`
   - Try logging in - should work without redirect errors
   - Check browser network tab - API calls should go to `api.pickems.fun`

---

## 🔧 Important Notes

### Domain Conflicts
- **NEVER** add `api.pickems.fun` to Amplify - it should point to your ECS backend
- If you accidentally add it, delete it immediately from Amplify

### Cache Issues
- If you see old content, try:
  - Hard refresh: `Cmd/Ctrl + Shift + R`
  - Incognito/private browsing mode
  - Clear browser cache

### Environment Variables
- The build already includes `VITE_API_URL=https://api.pickems.fun`
- No additional environment variables needed in Amplify

---

## 📱 Expected Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  pickems.fun    │    │  api.pickems.fun │    │   S3 Bucket     │
│  (Amplify)      │────→  (ECS Backend)   │────→  (Avatars)      │
│  React Frontend │    │  Django API      │    │  Images         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## 🆘 Troubleshooting

### If login still redirects to localhost:
1. Check browser network tab during login
2. Verify API calls are going to `https://api.pickems.fun`
3. If not, the wrong build was deployed

### If domain doesn't work:
1. Check Route 53 DNS records
2. Ensure no conflicting A records exist
3. Wait for DNS propagation (up to 24 hours)

### If SSL certificate fails:
1. Verify domain ownership in Amplify
2. Check that DNS points correctly to Amplify
3. Wait - SSL can take 30 minutes to provision

---

## ✅ Success Criteria

When setup is complete, you should be able to:
- ✅ Access `https://pickems.fun` and see your app
- ✅ Login/signup without redirect errors  
- ✅ API calls go to `https://api.pickems.fun` (visible in browser dev tools)
- ✅ Upload avatar images (they go to S3)
- ✅ No console errors in browser dev tools

---

**🎉 That's it! Your fresh Amplify deployment should now work correctly.**