import base64
from email import message_from_bytes
from email.mime.text import MIMEText
import requests
from googleapiclient.discovery import build
from oauth2client import file, client, tools
import base64
import json
import subprocess

# ---------------------------
# CONFIG
# ---------------------------

OLLAMA_MODEL = "qwen2.5:14b" # "llama3.1:8b"  # "mailbox-ai"
OLLAMA_URL = "http://localhost:11434/api/generate"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify"
]

TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"


def list_installed_models():
    """
    Returns a set of installed Ollama model names.
    """
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True
        )

        if result.returncode != 0:
            return set()

        installed = set()
        for line in result.stdout.splitlines():
            if ":" in line:
                model = line.split(":")[0].strip()
                installed.add(model)

        return installed

    except Exception:
        return set()


def verify_models(models_needed):
    installed = list_installed_models()
    missing = []

    for model in models_needed:
        # Strip tag so "llama3.1:8b" counts if "llama3.1" is installed
        base = model.split(":")[0]
        if base not in installed:
            missing.append(model)

    if missing:
        print("\nWARNING: The following Ollama models are not installed:")
        for m in missing:
            print("  -", m)
        print("Install them with:  ollama pull MODELNAME\n")


# ---------------------------
# GOOGLE AUTH
# ---------------------------

def get_gmail_service():
    store = file.Storage(TOKEN_PATH)
    creds = store.get()

    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(CREDS_PATH, SCOPES)
        creds = tools.run_flow(flow, store)

    return build('gmail', 'v1', credentials=creds)


# ---------------------------
# FETCH EMAILS
# ---------------------------

def get_message_body(service, msg_id):
    import re
    from bs4 import BeautifulSoup

    msg = service.users().messages().get(
        userId="me", id=msg_id, format="raw"
    ).execute()

    raw_bytes = base64.urlsafe_b64decode(msg['raw'])
    email_msg = message_from_bytes(raw_bytes)

    plain_parts = []
    html_parts = []

    # Walk every MIME section
    for part in email_msg.walk():
        content_type = part.get_content_type()
        content_dispo = str(part.get("Content-Disposition")).lower()

        # Skip attachments
        if "attachment" in content_dispo:
            continue

        # Extract text/plain
        if content_type == "text/plain":
            try:
                plain_parts.append(
                    part.get_payload(decode=True).decode(errors="ignore")
                )
            except:
                pass

        # Extract text/html
        elif content_type == "text/html":
            try:
                html_parts.append(
                    part.get_payload(decode=True).decode(errors="ignore")
                )
            except:
                pass

    # Prefer plain text if available
    if plain_parts:
        combined = "\n".join(plain_parts).strip()
        if combined:
            return combined

    # Fall back to HTML (strip tags)
    if html_parts:
        soup = BeautifulSoup("\n".join(html_parts), "html.parser")
        text = soup.get_text("\n")
        cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
        if cleaned:
            return cleaned

    return "(no readable text content found)"


def fetch_inbox(service, max_results=5):
    results = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=max_results
    ).execute()

    return results.get("messages", [])


# ---------------------------
# OLLAMA CALL
# ---------------------------

def run_llm(email_text, task):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"USER_EMAIL:\n{email_text}\n\nTASK:\n{task}\n",
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)
    data = response.json()

    return data.get("response", "").strip()


# ---------------------------
# DRAFT CREATION
# ---------------------------

def create_gmail_draft(service, reply_text, original_msg):
    headers = original_msg['payload']['headers']
    subject = None
    sender = None

    for h in headers:
        if h['name'] == 'Subject':
            subject = h['value']
        if h['name'] == 'From':
            sender = h['value']

    if subject is None:
        subject = "(no subject)"

    mime_message = MIMEText(reply_text)
    mime_message['to'] = sender
    mime_message['subject'] = "Re: " + subject

    encoded = base64.urlsafe_b64encode(
        mime_message.as_bytes()
    ).decode()

    draft_body = {
        'message': {'raw': encoded}
    }

    draft = service.users().drafts().create(
        userId='me', body=draft_body
    ).execute()

    return draft


# ---------------------------
# LLM TASK
# ---------------------------

EMAIL_REPLY_TASK = """
You are generating an email reply on behalf of the user.

Rules:
1. Do not invent facts or pretend you know details not present.
2. If the email contains questions, answer them directly.
3. If the sender is making a request, acknowledge it and respond appropriately.
4. Keep the tone natural and human, not robotic.
5. Maintain a polite, concise style unless the original email is from a friend.
6. If the email is personal or emotional, respond with appropriate empathy.
7. If the email is business-related, be professional and crisp.
8. If the email is spam, write: "This appears to be spam. No response needed."

Your output must be ONLY the full email reply text.
"""


# ---------------------------
# MAIN PIPELINE
# ---------------------------

def process_inbox(task=EMAIL_REPLY_TASK):
    service = get_gmail_service()
    messages = fetch_inbox(service, max_results=5)

    if not messages:
        print("Inbox empty. What a thrilling life you lead.")
        return

    for msg in messages:
        msg_full = service.users().messages().get(
            userId="me", id=msg['id'], format="full"
        ).execute()

        body = get_message_body(service, msg['id'])

        print("\n-------------------------------------------")
        print("EMAIL:")
        print(body[:500] + ("..." if len(body) > 500 else ""))

        print("\nLLM OUTPUT:")
        reply = run_llm(body, task)
        print(reply)

        draft = create_gmail_draft(service, reply, msg_full)
        print(f"\nDraft created: {draft.get('id')}")
        print("-------------------------------------------\n")


# ---------------------------
# RUN
# ---------------------------

if __name__ == "__main__":
    verify_models([
        "mailbox-ai",
        "llama3.1:8b",
        "mistral",
        "qwen2.5:7b"
    ])

    process_inbox(task=EMAIL_REPLY_TASK)

