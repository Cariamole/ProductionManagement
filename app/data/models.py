from app.data.database import Base
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Enum


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    admin = Column(Boolean, default=False)
    hashed_password = Column(String)
    active = Column(Boolean, default=True)
    job = Column(Enum('coupeur', 'plieur', 'soudeur', 'bureau', name='job_types'))
    quantity = Column(Integer)

class Task(Base):
    __tablename__ = 'task'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    timeSoudure = Column(Integer)
    timeCoupe = Column(Integer)
    timePliage = Column(Integer)
    finished = Column(Boolean, default=False)
    priority = Column(Integer, default=2)
