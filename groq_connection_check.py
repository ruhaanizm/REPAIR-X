
"""Groq + Qwen connectivity check for REPAIR-X."""

from dotenv import load_dotenv

load_dotenv()

from llm_providers.factory import create_provider
from llm_providers.generate import generate_text


def main():
    client, model = create_provider("groq")

    print("Testing Groq provider...")
    print("Model:", model)

    response = generate_text(
        client,
        model,
        "Reply with exactly one word: CONNECTED",
    )

    print("Response:", repr(response))

    if response.strip() == "CONNECTED":
        print("PASS: Groq + Qwen provider is responding.")
    else:
        print("API responded, but output differed from the requested word.")


if __name__ == "__main__":
    main()
