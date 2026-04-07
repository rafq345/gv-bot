from celery_app import celery_app
from services.gemma_vision_service import GemmaVisionService
from services.nutrition_service import NutritionService

from database import SessionLocal
from models import Meal
import requests
import os

vision = GemmaVisionService()
nutrition = NutritionService()


@celery_app.task
def process_food(image_bytes: bytes, chat_id: str, meal_id: int):
    print(f"[CELERY] Start processing")

    db = SessionLocal()

    try:
        # 1. Vision
        vision_result = vision.detect_products(image_bytes)
        print(f"[CELERY] Vision result: {vision_result}")

        # 2. Nutrition
        nutrition_result = nutrition.analyze(vision_result)
        print(f"[CELERY] Nutrition result: {nutrition_result}")

        # 3. Сохраняем в БД
        meal = db.query(Meal).filter(Meal.id == meal_id).first()
        meal.vision_json = vision_result
        meal.status = "done"
        db.commit()

        # 4. Формируем текст
        text = "Вот что я нашёл:\n\n"

        for item in vision_result:
            text += f"• {item['name']} — {item.get('grams', '?')} г\n"

        text += "\nВсё верно?"

        # 5. Кнопки
        buttons = [
            [
                {"text": "✅ Да", "callback_data": f"confirm_yes:{meal_id}"},
                {"text": "✏️ Изменить", "callback_data": f"confirm_edit:{meal_id}"}
            ]
        ]

        # 6. Отправка в Telegram
        BOT_TOKEN = os.getenv("BOT_TOKEN")

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "reply_markup": {"inline_keyboard": buttons}
            }
        )

    except Exception as e:
        print(f"[CELERY ERROR] {e}")

    finally:
        db.close()
