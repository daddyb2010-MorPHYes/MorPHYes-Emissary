# MorPHYes-Emissary
MorPHYes Emissary - Clean, human-only Gmail history. Automatically removes noreply spam, job alerts, signatures, and quoted replies. Shows conversations in simple Them/Me format.
# MorPHYes Emissary

**Clean, human-only Gmail history.**  
No noreply spam. No quoted garbage. No signatures. Just real conversations.

### What it does
- Groups all your conversations by person (most recent first)
- Shows full history in clean **Them / Me** format
- Aggressively removes job alerts, security alerts, noreply emails, and anything with “unsubscribe”
- Removes signatures, disclaimers, quoted replies, and everything below the actual message
- Lets you export any full relationship as a clean .txt file

### Quick Start
1. Download the folder
2. Put your `google_credentials.json` file in the **same folder** as `emissary.py`
3. Run:
   ```bash
   pip install streamlit google-auth-oauthlib google-auth-httplib2 google-api-python-client
   streamlit run emissary.py
