from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=func.now())
