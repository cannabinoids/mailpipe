# Mailpipe – AI-Powered Email Reply Assistant

Mailpipe fetches your Gmail inbox, generates suggested replies using an LLM (Ollama-supported models), and creates Gmail drafts automatically.

---

## Features

- Fetches latest emails from Gmail
- Extracts plaintext or HTML content
- Sends emails to an LLM for summarization or reply generation
- Creates Gmail drafts with the generated reply
- Threaded processing for multiple emails
- Model selection from installed Ollama models

---

## Requirements

See `requirements.txt` for Python dependencies.

---

## Installation

1. Clone or copy the project folder to your machine.
2. Install Python 3.10+ and pip.
3. Install dependencies:

```bash
pip install -r requirements.txt


## Google OAuth Setup (Gmail API)

Go to Google Cloud Console
.

Create a new project.

Enable the Gmail API for the project.

Create OAuth 2.0 credentials (Desktop App type).

Download the credentials.json and place it in your project folder.

On first run, the script will generate token.json via browser auth.

Scopes required in SCOPES:

https://www.googleapis.com/auth/gmail.readonly

https://www.googleapis.com/auth/gmail.compose

https://www.googleapis.com/auth/gmail.modify
