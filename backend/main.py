# Стандартная библиотека Python
import os
import time
import logging
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from urllib.parse import parse_qsl

# Сторонние библиотеки
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError
from jose import jwt
from models import Base, User, Meal

# Локальные/проектные модули
from tasks import vision_task
from database import get_db


SECRET_KEY = os.getenv("SECRET_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60))
ALGORITHM = "HS256"
security = HTTPBearer()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://gv_user:gv_pass@db:5432/gv_bot"

engine = create_engine(DATABASE_URL)

# Ждём пока Postgres станет доступен
for _ in range(10):
    try:
        with engine.connect() as connection:
            break
    except OperationalError:
        logger.warning("Waiting for database...")
        time.sleep(2)

SessionLocal = sessionmaker(bind=engine)

app = FastAPI()

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"status": "GV Bot backend running"}

@app.get("/health")
def health():
    return {"health": "ok"}

@app.post("/create_user/{telegram_id}")
def create_user(telegram_id: str):
    logger.info(f"Creating user with telegram_id={telegram_id}")
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if user:
        return {"message": "User already exists"}

    new_user = User(telegram_id=telegram_id)
    db.add(new_user)
    db.commit()


    return {"message": "User created"}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/check_access/{telegram_id}")
def check_access(telegram_id: str):
    logger.info(f"Checking access for telegram_id={telegram_id}")

    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        return {"access": False, "reason": "User not found"}

    if user.status == "trial":
        return {"access": True, "status": "trial"}

    return {"access": False, "reason": "Access denied"}

@app.post("/auth/telegram")
def telegram_auth(init_data: str = Body(...)):

    data = dict(parse_qsl(init_data))

    # 1️⃣ СНАЧАЛА достаём hash
    received_hash = data.pop("hash", None)

    if not received_hash:
        raise HTTPException(status_code=400, detail="Hash missing")

    # 2️⃣ проверяем auth_date
    auth_date = int(data.get("auth_date", 0))
    now = int(datetime.utcnow().timestamp())

    if now - auth_date > 60:
        raise HTTPException(status_code=403, detail="Auth data expired")

    # 3️⃣ формируем строку для проверки
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )

    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    # 4️⃣ сравниваем
    if calculated_hash != received_hash:
        raise HTTPException(status_code=403, detail="Invalid Telegram signature")

    # 5️⃣ работаем с user
    user_data = json.loads(data["user"])
    telegram_id = str(user_data["id"])

    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()

    token = create_access_token({"telegram_id": telegram_id})

    return {"access_token": token}

@app.get("/me")
def get_me(payload: dict = Depends(verify_token)):
    return {"user": payload}

@app.post("/analyze-meal")
def analyze_meal(
    file: UploadFile = File(...),
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    contents = file.file.read()
    print("BACKEND: received image, size =", len(contents))

    task = vision_task.delay(
        image_bytes=contents,
        telegram_id=payload["telegram_id"]
    )

    return {"task_id": task.id}

@app.get("/meals/last/{telegram_id}")
def get_last_meal(telegram_id: int):
    db = SessionLocal()
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return {"error": "user not found"}
    
    meal = (
        db.query(Meal)
        .filter(Meal.user_id == user.id)
        .order_by(Meal.created_at.desc())
        .first()
    )
    
    if not meal:
        return {"error": "no meals"}
    
    return {
        "meal_id": meal.id,
        "foods": meal.vision_json,
        "status": meal.status
    }
