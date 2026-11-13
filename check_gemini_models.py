
from dotenv import load_dotenv
from llm_providers.factory import create_provider
from openai import APIStatusError

load_dotenv()

try:
    client, selected_model = create_provider("gemini")

    print("Configured model:", selected_model)
    print("\nAvailable Gemini models:")

    models = client.models.list()

    model_ids = sorted(model.id for model in models.data)

    for model_id in model_ids:
        if "gemini" in model_id.lower():
            print(" -", model_id)

    normalized_ids = {
    model_id.removeprefix("models/")
    for model_id in model_ids
    }

    print("\nConfigured model found:", selected_model in normalized_ids)

except APIStatusError as exc:
    print("HTTP status:", exc.status_code)
    print("API error:", str(exc)[:1500])

except Exception as exc:
    print("Error:", type(exc).__name__, str(exc)[:1000])
