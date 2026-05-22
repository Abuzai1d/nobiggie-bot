import requests
import base64
import os

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "Abuzai1d/nobiggie-bot"


def upload_pdf_to_github(pdf_path, filename):
    headers = {
        "Authorization": "token " + GITHUB_TOKEN,
        "Accept": "application/vnd.github.v3+json"
    }
    with open(pdf_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    path = "quotes/" + filename
    r = requests.get(
        "https://api.github.com/repos/" + REPO + "/contents/" + path,
        headers=headers
    )
    sha = r.json().get("sha") if r.status_code == 200 else None
    payload = {"message": "add quote " + filename, "content": content}
    if sha:
        payload["sha"] = sha
    r = requests.put(
        "https://api.github.com/repos/" + REPO + "/contents/" + path,
        headers=headers,
        json=payload
    )
    if r.status_code in (200, 201):
        download_url = "https://raw.githubusercontent.com/" + REPO + "/main/" + path
        return download_url
    return None
