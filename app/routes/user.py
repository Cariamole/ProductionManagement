from typing import Annotated, List
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, APIRouter, HTTPException, status, Request, Form, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from app.data import models
from app.data.database import SessionLocal, engine, get_db
from jwt.exceptions import InvalidTokenError

SECRET_KEY = "e2624cf391172a5065715ef40635f979380f7e6f105749d5a1fe940ccd2fef69"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

passwordContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/user", tags=["user"])
templates = Jinja2Templates(directory="templates")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None


class UserBase(BaseModel):
    username: str
    email: str
    firstname: str
    name: str
    admin: bool


class UserInDB(UserBase):
    hashed_password: str


# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/token")  # "token" ou ./token


def verify_password(plain_password, hashed_password):
    return passwordContext.verify(plain_password, hashed_password)


def get_password_hash(password):
    return passwordContext.hash(password)


def get_user(db: Session, username: str):
    return db.query(models.Users).filter(models.Users.username == username).first()


def authenticate_user(db: Session, usermame: str, password: str):
    user = get_user(db, usermame)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get("access_token")
    if not token:
        return False
    try:
        scheme, token = token.split()
        if scheme.lower() != "bearer":
            return False

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return bool(username)
    except (jwt.DecodeError, jwt.ExpiredSignatureError, InvalidTokenError):
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user_from_cookie(
        request: Request,
        db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        scheme, token = token.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = get_user(db, username=username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except (jwt.DecodeError, jwt.ExpiredSignatureError, InvalidTokenError):
        raise HTTPException(status_code=401, detail="Token is invalid or has expired")


@router.get("/register/", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register/")
async def register_user(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        email: str = Form(...),
        name: str = Form(...),
        firstname: str = Form(...),
        db: Session = Depends(get_db)):
    existing_user = get_user(db, username)
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already taken"})
    hashed_password = get_password_hash(password)

    new_user = models.Users(username=username, email=email, hashed_password=hashed_password, name=name,
                            firstname=firstname)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return RedirectResponse(url="/users/login/", status_code=303)


@router.get("/login/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login/", response_class=HTMLResponse)
async def login(request: Request,
                username: str = Form(...),
                password: str = Form(...),
                db: Session = Depends(get_db)
                ):
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Incorrect username or password"})
    if not user.active:
        return templates.TemplateResponse("login.html",
                                          {"request": request, "error": "You’ve been disabled by an admin"})

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    response = RedirectResponse(url="/connected/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response


@router.get("/edit/{user_id}", response_class=HTMLResponse)
async def edit_user(request: Request, user_id: int,
                    current_user: models.Users = Depends(get_current_user_from_cookie)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return templates.TemplateResponse("connected_edit_user.html", {"request": request, "current_user": current_user})


@router.post("/edit/{user_id}")
async def update_user(
        # username: str = Form(...),
        email: str = Form(...),
        name: str = Form(...),
        firstname: str = Form(...),
        db: Session = Depends(get_db),
        current_user: models.Users = Depends(get_current_user_from_cookie)):
    if not current_user:
        raise HTTPException(status_code=404, detail="user not found")
    # existing_user = db.query(models.Users).filter(models.Users.username == username).first()
    # if existing_user is not None and existing_user.id != current_user.id:
    #     raise HTTPException(status_code=400, detail="Username already taken")
    current_user.name = name
    current_user.firstname = firstname
    current_user.email = email
    db.commit()
    return RedirectResponse(url="/connected/", status_code=303)


@router.get("/password/", response_class=HTMLResponse)
async def edit_password_page(request: Request,
                             # user_id: int,
                             current_user: models.Users = Depends(get_current_user_from_cookie)):
    # if current_user.id != user_id:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return templates.TemplateResponse("connected_edit_password.html",
                                      {"request": request, "current_user": current_user})


@router.post("/password/")
async def update_password(
        # username: str = Form(...),
        current_password: str = Form(...),
        new_password: str = Form(...),
        confirm_password: str = Form(...),
        db: Session = Depends(get_db),
        current_user: models.Users = Depends(get_current_user_from_cookie)):
    if not current_user:
        raise HTTPException(status_code=400, detail="Wrong user")
    if verify_password(current_password, get_password_hash(new_password)):
        raise HTTPException(status_code=400, detail="Wrong password")
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords not the same")

    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    return RedirectResponse(url="/connected/", status_code=303)
