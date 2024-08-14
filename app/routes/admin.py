from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from starlette.responses import RedirectResponse
from app.data.database import engine, get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.routes.task import successful_response
from app.routes.user import get_current_user_from_cookie, is_authenticated
from app.data.models import User, Task

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/task", response_class=HTMLResponse)
async def get_users(
        request: Request,
        current_user: User = Depends(get_current_user_from_cookie)
):
    if not current_user.admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized to access this page")
    return templates.TemplateResponse("admin_task.html", {"request": request, "current_user": current_user})


@router.get("/task/finished", response_class=HTMLResponse)
async def get_task(
        request: Request,
        current_user: User = Depends(get_current_user_from_cookie),
        db: Session = Depends(get_db)
):
    if not current_user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not admin")
    tasks = (db.query(Task).filter(Task.soudureDoneBy <= 0 , Task.soudureDoneBy>-2).all())
    return templates.TemplateResponse("admin_task_finished.html", {"request": request, "tasks": tasks,"current_user": current_user})


@router.get("/task/prebuild", response_class=HTMLResponse)
async def get_task(
        request: Request,
        current_user: User = Depends(get_current_user_from_cookie),
        db: Session = Depends(get_db)
):
    if not current_user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not admin")
    tasks = (db.query(Task).filter(Task.save==1).all())
    return templates.TemplateResponse("admin_task_prebuild.html", {"request": request, "tasks": tasks,"current_user": current_user})

# @router.get("/users", response_class=HTMLResponse)
# async def get_users(
#         request: Request,
#         current_user: User = Depends(get_current_user_from_cookie),
#         db: Session = Depends(get_db)
# ):
#     if not current_user.admin:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized to access this page")
#
#     all_users = (
#         db.query(models.Users).all()
#     )
#     return templates.TemplateResponse("admin_user.html", {"request": request, "user": all_users, "current_user": current_user})
#

# @router.put("/deactivate/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def admin_deactivate(user_id: int,
#                     db: Session = Depends(get_db)):
#
#     user_model = db.query(models.Users).filter(models.Users.id == user_id).first()
#     if not user_model:
#         raise HTTPException(status_code=404, detail="User not found")
#     user_model.active = not user_model.active
#     db.commit()
#     return successful_response(status_code=204)
#
# @router.put("/administrate/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def admin_administrate(user_id: int,
#                     db: Session = Depends(get_db)):
#
#     user_model = db.query(models.Users).filter(models.Users.id == user_id).first()
#     if not user_model:
#         raise HTTPException(status_code=404, detail="User not found")
#     user_model.admin= not user_model.admin
#     db.commit()
#     return successful_response(status_code=204)
