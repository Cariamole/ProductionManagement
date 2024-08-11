from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.routes.user import router as user_router

app = FastAPI(title="Management app")
app.include_router(user_router)


templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(response_class=RedirectResponse):
    response = RedirectResponse(url="/task")
    return response

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("error404.html", {"request": request}, status_code=404)
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("error.html", {"request": request, "error_message": exc.detail})

