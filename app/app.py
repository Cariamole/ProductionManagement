from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.data.database import Base, engine, get_db
from app.data.models import Task, User
from app.routes.user import router as user_router, get_current_user_from_cookie, is_authenticated
from app.routes.connected import router as connected_router
from app.routes.task import router as task_router
from app.routes.admin import router as admin_router

app = FastAPI(title="Management app")
app.include_router(user_router)
app.include_router(connected_router)
app.include_router(task_router)
app.include_router(admin_router)

templates = Jinja2Templates(directory="app/templates")

# Base.metadata.drop_all(bind=engine)
# Base.metadata.create_all(bind=engine)
# Task.__table__.drop(engine)
# Task.__table__.create(engine)



@app.get("/")
async def home(request: Request,
               db: Session = Depends(get_db)
               ):
    if (is_authenticated(request)):
        return RedirectResponse(url="/connected/home")
    tasks = db.query(Task).filter(Task.soudureDoneBy>0).all()
    return templates.TemplateResponse("home.html", {"request": request, "tasks": tasks})


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("error404.html", {"request": request}, status_code=404)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("error.html", {"request": request, "error_message": exc.detail})

