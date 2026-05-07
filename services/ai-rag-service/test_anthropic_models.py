"""
Test script to find available Anthropic models
"""
import anthropic

# Your API key
api_key = "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"

client = anthropic.Anthropic(api_key=api_key)

# List of models to test (from Anthropic documentation)
models_to_test = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-3-7-sonnet-20250219",  # Latest as of Jan 2026
    "claude-sonnet-4-20250514",
]

print("Testing Anthropic models...\n")

for model in models_to_test:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✅ {model} - WORKS")
    except anthropic.NotFoundError:
        print(f"❌ {model} - NOT FOUND")
    except Exception as e:
        print(f"⚠️  {model} - ERROR: {str(e)[:50]}")

print("\nTest complete!")
