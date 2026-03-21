from sqlalchemy.orm import Session
from database import SessionLocal
from models import Meal, User
from services.gemma_vision_service import GemmaVisionService
from celery_app import celery


@celery.task(name="tasks.vision_task")
def vision_task(image_bytes: bytes, telegram_id: int):

    print("=== TASK START ===")

    detected_foods = GemmaVisionService.detect_products(image_bytes)
    print("DETECTED:", detected_foods)

    db = SessionLocal()

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    print("USER:", user)

    if not user:
        print("USER NOT FOUND → creating")
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    try:
        meal = Meal(
            user_id=user.id,
            vision_json=detected_foods,
            status="waiting_confirmation"
        )

        print("ADDING MEAL")

        db.add(meal)
        db.commit()
        db.refresh(meal)

        print("MEAL SAVED:", meal.id)

    except Exception as e:
        print("ERROR SAVING MEAL:", str(e))
        db.rollback()

    finally:
        db.close()

    print("=== TASK END ===")

    return {"meal_id": meal.id, "foods": detected_foods}
