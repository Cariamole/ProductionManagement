from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.data.database import get_db
from app.data.models import User
from app.routes.task import whenFinished

testTime = datetime(2024,8,8,19)
testTime1 = datetime(2024,8,10,10)

if(testTime > testTime1):
    print("Test")


