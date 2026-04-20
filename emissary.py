import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from pathlib import Path
import streamlit as st
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pickle
from googleapiclient.discovery import build
import re
import base64
from collections import defaultdict

CREDENTIALS_FILE = Path(__file__).parent / "google_credentials.json"
TOKEN_FILE = Path(__file__).parent / "google_token.pickle"

st.set_page_config(page_title="MorPHYes Emissary", page_icon="📧", layout="wide")

st.title("📧 MorPHYes Emissary")
st.caption("Clean Human-Only History • Chronological • Export or Discard")

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_google_credentials():
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                st.error("google_credentials.json not found in the same folder!")
                st.stop()
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
    return creds

MY_EMAILS = ["your-email@gmail.com", "second-email@gmail.com"]

def get_clean_body(msg):
    payload = msg.get('payload', {})
    body = ""
    if 'body' in payload and 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    elif 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain' and 'body' in part and 'data' in part['body']:
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                break
    body = re.sub(r'From:.*', '', body)
    body = re.sub(r'Sent:.*', '', body)
    body = re.sub(r'To:.*', '', body)
    body = re.sub(r'Cc:.*', '', body)
    body = re.sub(r'Subject:.*', '', body)
    body = re.sub(r'ATTENTION!.*', '', body, flags=re.IGNORECASE)
    body = re.sub(r'https?://\S+', '', body)
    body = re.sub(r'On .* wrote:', '', body, flags=re.IGNORECASE)
    body = re.sub(r'^>.*$', '', body, flags=re.MULTILINE)
    body = re.sub(r'\n{3,}', '\n\n', body)
    return body.strip()

def is_spam(sender, subject, body):
    text = (sender + " " + subject + " " + body).lower()
    if "unsubscribe" in text:
        return True
    if any(x in sender.lower() for x in ["no-reply", "noreply", "do not reply", "info@", "alerts@", "notifications@"]):
        return True
    if any(x in subject.lower() for x in ["job alert", "career", "security alert"]):
        return True
    return False

if "grouped_by_sender" not in st.session_state:
    st.session_state.grouped_by_sender = {}
if "history" not in st.session_state:
    st.session_state.history = {}

if st.button("🔐 Connect & Load All Conversations", use_container_width=True):
    try:
        creds = get_google_credentials()
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().threads().list(userId='me', maxResults=400).execute()
        threads = results.get('threads', [])
        
        grouped = defaultdict(list)
        
        for thread in threads:
            detail = service.users().threads().get(userId='me', id=thread['id']).execute()
            messages = detail.get('messages', [])
            if not messages:
                continue
            
            other_person = None
            for msg in messages:
                from_email = next((h['value'] for h in msg['payload']['headers'] if h['name'] == 'From'), '')
                if not any(my in from_email for my in MY_EMAILS):
                    other_person = from_email
                    break
            
            if not other_person:
                continue
            
            latest = messages[-1]
            subject = next((h['value'] for h in latest['payload']['headers'] if h['name'] == 'Subject'), '(No Subject)')
            body = get_clean_body(latest)
            
            if is_spam(other_person, subject, body):
                continue
            
            grouped[other_person].append({
                'thread_id': thread['id'],
                'subject': subject,
                'message_count': len(messages),
                'latest_date': latest.get('internalDate', '')
            })
        
        for sender in grouped:
            grouped[sender].sort(key=lambda x: x['latest_date'], reverse=True)
        
        st.session_state.grouped_by_sender = dict(grouped)
        st.success(f"✅ Loaded conversations with {len(grouped)} people")
        
    except Exception as e:
        st.error(f"Error: {e}")

st.subheader("📂 People You've Emailed (Most Recent First)")

if st.session_state.grouped_by_sender:
    for sender, threads in sorted(st.session_state.grouped_by_sender.items(), 
                                   key=lambda x: x[1][0]['latest_date'], reverse=True):
        
        with st.expander(f"{sender} ({len(threads)} conversations)"):
            
            if st.button(f"📖 View Full History", key=f"view_{sender}"):
                try:
                    creds = get_google_credentials()
                    service = build('gmail', 'v1', credentials=creds)
                    
                    history = []
                    for t in threads:
                        thread_detail = service.users().threads().get(userId='me', id=t['thread_id']).execute()
                        for msg in thread_detail['messages']:
                            from_ = next((h['value'] for h in msg['payload']['headers'] if h['name'] == 'From'), '')
                            date_str = datetime.fromtimestamp(int(msg.get('internalDate', 0)) / 1000).strftime("%Y-%m-%d %H:%M")
                            body = get_clean_body(msg)
                            
                            if any(my in from_ for my in MY_EMAILS):
                                history.append(f"Me ({date_str}): {body}")
                            else:
                                history.append(f"Them ({date_str}): {body}")
                    
                    st.session_state.history[sender] = "\n\n".join(history)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error: {e}")
            
            if sender in st.session_state.history:
                st.write("**Full History (Them / Me):**")
                st.text_area("", st.session_state.history[sender], height=550)
                
                col1, col2 = st.columns(2)
                if col1.button(f"📄 Export Entire Relationship to TXT", key=f"export_{sender}"):
                    safe = sender.split('<')[0].strip().replace(' ', '_').replace('/', '_')
                    filename = f"Full_History_{safe}.txt"
                    filepath = Path(__file__).parent / "Emissary_Exports" / filename
                    filepath.parent.mkdir(exist_ok=True)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(f"Full Conversation History with: {sender}\n\n{st.session_state.history[sender]}")
                    st.success(f"✅ Exported to {filename}")
                
                if col2.button(f"🗑️ Discard This Preview", key=f"discard_{sender}"):
                    if sender in st.session_state.history:
                        del st.session_state.history[sender]
                    st.rerun()
else:
    st.info("Click the button above to load your conversations grouped by person.")

st.caption("MorPHYes Emissary • Human conversations only • Clean Them/Me • Export or Discard")