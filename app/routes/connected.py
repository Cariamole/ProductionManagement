from datetime import timedelta, datetime

from fastapi import Depends, APIRouter, Request, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from typing import Annotated
from starlette.templating import Jinja2Templates
from app.data import models
from app.data.database import get_db
from app.routes.user import get_current_user_from_cookie, UserBase
from app.data.models import Task
from app.data.models import User

router = APIRouter(prefix="/connected", tags=["connected"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/home", response_class=HTMLResponse)
async def all_tasks(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user_from_cookie)],
        db: Session = Depends(get_db)
):
    tasks = db.query(Task).all()
    timeElapsed = datetime.now() - timedelta(weeks=2)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return templates.TemplateResponse("connected_home.html", {"request": request, "current_user": current_user, "tasks": tasks, "timeElapsed": timeElapsed})



@router.get("/mytask", response_class=HTMLResponse)
async def get_task(
        request: Request,
        current_user: User = Depends(get_current_user_from_cookie),
        db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED_FORBIDDEN, detail="Not logged")
    tasks = (db.query(Task).filter(or_((Task.soudureDoneBy==current_user.id),(Task.pliageDoneBy==current_user.id),(Task.coupeDoneBy == current_user.id))).all())
    return templates.TemplateResponse("connected_mytask.html", {"request": request, "tasks": tasks,"current_user": current_user})
@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response
#
#
# @router.get("/check_connection", response_model=UserBase)
# async def check_connection(current_user: Annotated[models.Users, Depends(get_current_user_from_cookie)]):
#     return current_user
