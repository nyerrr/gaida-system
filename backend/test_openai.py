from app.services.openai_client import client

response = client.responses.create(
    model="gpt-4.1-mini",
    input="Say hello in a friendly way."
)

print(response.output[0].content[0].text)