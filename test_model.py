from dotenv import load_dotenv
load_dotenv()

from model_client import call_model

response = call_model(
    messages=[
        {
            "role": "user",
            "content": "Reply with the word READY."
        }
    ],
    item_id="CONFIG-TEST",
)

print(response)