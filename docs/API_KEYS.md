# API Keys Setup Guide

This guide walks you through obtaining the necessary API credentials for the Quantum Intelligence Newsletter Generator.

## Required API Keys

You'll need three sets of credentials:
1. Google Gemini API Key
2. Tavily Search API Key
3. Gmail App Password

---

## 1. Google Gemini API Key

### Prerequisites
- Google account
- Access to Google AI Studio

### Steps

1. **Visit Google AI Studio**
   - Go to https://makersuite.google.com/app/apikey
   - Sign in with your Google account

2. **Create API Key**
   - Click "Create API Key"
   - Select or create a Google Cloud project
   - Click "Create API key in new project" (or select existing project)

3. **Copy and Save**
   - Copy the generated API key
   - Store it securely (you won't be able to see it again)

4. **Add to .env**
   ```bash
   Gemini_API_Key=your_actual_api_key_here
   ```

### Pricing
- Free tier: 60 requests per minute
- See https://ai.google.dev/pricing for current rates

---

## 2. Tavily Search API Key

### Prerequisites
- Email address for account creation

### Steps

1. **Sign Up for Tavily**
   - Go to https://tavily.com
   - Click "Sign Up" or "Get API Key"
   - Create an account with your email

2. **Access API Dashboard**
   - Log in to your Tavily account
   - Navigate to API Keys section in dashboard

3. **Generate API Key**
   - Click "Create New API Key"
   - Copy the generated key

4. **Add to .env**
   ```bash
   TAVILY_API_KEY=your_tavily_api_key_here
   ```

### Pricing
- Free tier: 1,000 searches per month
- See https://tavily.com/pricing for current rates

---

## 3. Gmail App Password

### Prerequisites
- Gmail account
- 2-Factor Authentication (2FA) enabled on your Google account

### Important Notes
⚠️ **DO NOT use your regular Gmail password** - use an app-specific password instead  
⚠️ **2FA must be enabled** - app passwords are only available with 2FA

### Steps

1. **Enable 2-Factor Authentication** (if not already enabled)
   - Go to https://myaccount.google.com/security
   - Under "Signing in to Google", select "2-Step Verification"
   - Follow the prompts to enable 2FA

2. **Generate App Password**
   - Go to https://myaccount.google.com/apppasswords
   - You may need to sign in again
   - Select "Mail" as the app
   - Select "Other" as the device, enter "Quantum Newsletter"
   - Click "Generate"

3. **Copy App Password**
   - Google will display a 16-character password
   - Copy this password (spaces don't matter)
   - **Save it immediately** - you won't be able to see it again

4. **Add to .env**
   ```bash
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASS=your_16_character_app_password
   EMAIL_RECIPIENT=recipient@example.com
   ```

### Troubleshooting

**"App passwords" option not available:**
- Ensure 2FA is enabled on your account
- Wait 24 hours after enabling 2FA
- Try accessing https://myaccount.google.com/apppasswords directly

**SMTP authentication fails:**
- Verify you're using the app password, not your regular password
- Check that EMAIL_USER is the full email address (user@gmail.com)
- Remove any spaces from the app password

---

## Security Best Practices

### Storing API Keys

✅ **DO:**
- Use `.env` file for local development
- Add `.env` to `.gitignore`
- Use environment variables in production
- Rotate keys periodically (every 90 days)
- Use separate keys for dev/staging/production environments

❌ **DON'T:**
- Commit API keys to Git
- Share API keys via email/Slack
- Hardcode keys in source code
- Reuse keys across multiple projects
- Store keys in plain text files

### Monitoring API Usage

**Google Gemini:**
- Monitor usage at https://makersuite.google.com/app/apikey
- Set up billing alerts in Google Cloud Console

**Tavily:**
- Check usage in Tavily dashboard
- Set up notifications for quota limits

**Gmail:**
- Review sent emails in your Gmail account
- Monitor for suspicious activity in Google Security Checkup

### Key Rotation

If you suspect a key has been compromised:

1. **Immediately revoke the old key**
   - Gemini: Delete key in Google AI Studio
   - Tavily: Revoke key in dashboard
   - Gmail: Remove app password from account settings

2. **Generate new key** following steps above

3. **Update `.env` file** with new credentials

4. **Test** to ensure newsletter still works

---

## Validation

After adding all keys to your `.env` file, test the setup:

```bash
# Verify environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Gemini:', os.getenv('Gemini_API_Key')[:10] + '...'); print('Tavily:', os.getenv('TAVILY_API_KEY')[:10] + '...'); print('Email User:', os.getenv('EMAIL_USER'))"
```

Expected output:
```
Gemini: AIzaSyB...
Tavily: tvly-K7...
Email User: your_email@gmail.com
```

## Support

**Issues with API keys?**
- Check logs in `quantum_newsletter.log` for specific errors
- Verify `.env` file format (no quotes around values)
- Ensure `.env` is in the same directory as `quantum_intelligence.py`

**Still having problems?**
- Contact your team lead
- Create an issue in the GitHub repository
- See [README.md](../README.md) troubleshooting section
