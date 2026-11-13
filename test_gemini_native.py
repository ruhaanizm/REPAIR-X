

import os

import requests
from dotenv import load_dotenv
from requests.exceptions import Timeout, RequestException

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not api_key:
    raise SystemExit("GEMINI_API_KEY is missing.")

url = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{model}:generateContent"
)

try:
    response = requests.post(
        url,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "contents": [
                {
                    "parts": [
                        {"text": "Reply with exactly CONNECTED"}
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 100,
            },
        },
        timeout=(10, 90),
    )

except Timeout:
    raise SystemExit(
        "TIMEOUT: Gemini did not respond within the allowed time."
    )

except RequestException as exc:
    raise SystemExit(
        f"NETWORK ERROR: {type(exc).__name__}: {exc}"
    )

print("HTTP status:", response.status_code)

if response.ok:
    data = response.json()
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if "text" in part:
                print("Response:", part["text"])
else:
    try:
        error = response.json().get("error", {})
        print("Error status:", error.get("status"))
        print("Error message:", error.get("message"))
    except ValueError:
        print("Unexpected non-JSON error response.")
