
def generate_text(client, model, prompt):
    """Generate text using an OpenAI-compatible chat completion."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    if not response.choices:
        raise ValueError("Model returned no choices.")

    content = response.choices[0].message.content

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Model returned empty or non-text content.")

    return content
