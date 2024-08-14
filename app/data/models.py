from app.data.database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String)
    admin = Column(Boolean, default=False)
    hashed_password = Column(String)
    active = Column(Boolean, default=True)
    job = Column(Enum('coupeur', 'plieur', 'soudeur', 'bureau', name='job'))
    lastJob = Column(DateTime)

class Task(Base):
    __tablename__ = 'task'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    serialNumber = Column(String)
    description = Column(String)
    timeCoupe = Column(Integer)
    timePliage = Column(Integer)
    timeSoudure = Column(Integer)
    estimatedCoupe = Column(DateTime)
    estimatedPliage = Column(DateTime)
    estimatedSoudure = Column(DateTime)
    coupeDoneBy = Column(Integer, ForeignKey('user.id'))
    pliageDoneBy = Column(Integer, ForeignKey('user.id'))
    soudureDoneBy = Column(Integer, ForeignKey('user.id'))
    save = Column(Boolean)
