
from dotenv import load_dotenv

from llm_providers.factory import create_provider
from llm_providers.generate import generate_text

load_dotenv()

def main():
    client, model = create_provider("gemini")

    print("Testing Gemini provider...")
    print("Model:", model)

    response = generate_text(
        client,
        model,
        "Reply with exactly this word: CONNECTED",
    )

    print("Response:", repr(response))

    if response.strip() == "CONNECTED":
        print("PASS: Gemini provider is responding.")
    else:
        print("CONNECTED TO MODEL, but response differs from expected text.")


if __name__ == "__main__":
    main()
