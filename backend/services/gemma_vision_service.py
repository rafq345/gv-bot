import requests
import base64
import os
import json
import copy

class GemmaVisionService:

    @staticmethod
    def detect_products(image_bytes):

        api_key = os.getenv("YANDEX_API_KEY")
        folder_id = os.getenv("YANDEX_FOLDER_ID")

        model_uri = f"gpt://{folder_id}/gemma-3-27b-it/latest"
        url = "https://llm.api.cloud.yandex.net/v1/chat/completions"

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        headers = {
            "Authorization": f"Api-Key {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_uri,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты эксперт по анализу питания. Отвечай строго JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """
                            Проанализируй изображение еды.
                            Определи продукты на тарелке.
                            Верни строго JSON массив:
                            [
                              {"name": "название продукта", "grams": примерный вес в граммах}
                            ]
                            Никакого текста кроме JSON.
                            """
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 800,
            "temperature": 0.0
        }

        response = requests.post(url, headers=headers, json=payload)
        debug_payload = copy.deepcopy(payload)

# Заменяем длинную base64 строку на маркер
        for msg in debug_payload.get("messages", []):
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    if item.get("type") == "image_url":
                        item["image_url"]["url"] = "[BASE64_IMAGE_REMOVED]"

        print("=== PAYLOAD SENT TO GEMMA ===")
        print(debug_payload)
        print("=============≈===============")
        if response.status_code != 200:
            raise Exception(f"Gemma API error: {response.text}")

        data = response.json()
        text_answer = data["choices"][0]["message"]["content"]

        # Очистка markdown если модель добавила ```json
        if "```" in text_answer:
            text_answer = text_answer.replace("```json", "")
            text_answer = text_answer.replace("```", "")
            text_answer = text_answer.strip()

        return json.loads(text_answer)
