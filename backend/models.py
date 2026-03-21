from sqlalchemy import Column, Integer, BigInteger, Text, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)

    created_at = Column(TIMESTAMP, server_default=func.now())


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    created_at = Column(TIMESTAMP, server_default=func.now())

    meal_type = Column(Text)

    photo_url = Column(Text)

    vision_json = Column(JSON)

    status = Column(Text)
