from typing import Annotated
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from sqlalchemy import desc
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy.testing.pickleable import User
from starlette.responses import RedirectResponse


from app.data import models
from app.data.database import engine, get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.routes.user import get_current_user_from_cookie, is_authenticated
from app.data.models import User, Task

router = APIRouter(prefix="/task", tags=["task"])
templates = Jinja2Templates(directory="app/templates")
nowTime = datetime.now()


class TaskBase(BaseModel):
    name: str
    serialNumber: str
    description: str
    timeSoudure: int
    timeCoupe: int
    timePliage: int
    priority: int


class TaskModel(TaskBase):
    id: int


models.Base.metadata.create_all(bind=engine)


def firstDispo(job: str, db: Session = Depends(get_db())):
    tab = db.query(User).filter(User.job == job).all()
    dispo = tab[0]
    for i in tab:
        if i.lastJob < dispo.lastJob:
            dispo = i
    return dispo


def worker_set_now(db: Session = Depends(get_db())):
    for coupeur in db.query(User).filter(User.job == "coupeur").all():
        working = False
        for task in db.query(Task).all():
            if (coupeur.id == task.coupeDoneBy):
                print(coupeur.id)
                working = True
        if (not working):
            coupeur.lastJob = datetime.now()

    for plieur in db.query(User).filter(User.job == "plieur").all():
        working = False
        for task in db.query(Task).all():
            if (plieur.id == task.pliageDoneBy):
                working = True
        if (not working):
            plieur.lastJob = datetime.now()

    for soudeur in db.query(User).filter(User.job == "soudeur").all():
        working = False
        for task in db.query(Task).all():
            if (soudeur.id == task.soudureDoneBy):
                working = True
        if (not working):
            soudeur.lastJob = datetime.now()

    if (db.query(Task).count() == 0):
        for userU in db.query(User).all():
            userU.lastJob = datetime.now()

    db.commit()


@router.get("/", response_class=HTMLResponse)
# users = db.query(models.Users).all()
# books = db.query(models.Books).all()
async def get_task(
        request: Request,
        db: Session = Depends(get_db)
):
    if is_authenticated(request):
        return RedirectResponse(url="/connected/")
    task = (
        db.query(models.Task).all()
    )
    return templates.TemplateResponse("task.html", {"request": request, "task": task})


@router.get("/create", response_class=HTMLResponse)
async def create_page(request: Request, current_user: User = Depends(get_current_user_from_cookie),db: Session = Depends(get_db)):
    preTask = db.query(Task).filter(Task.save).all()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return templates.TemplateResponse("task_create.html", {"request": request, "current_user": current_user,"preTask":preTask})


@router.post("/create", response_model=TaskModel)
async def create_task(
        name: str = Form(...),
        serialNumber: str = Form(...),
        description: str = Form(...),
        timePliage: int = Form(...),
        timeCoupe: int = Form(...),
        timeSoudure: int = Form(...),
        save: bool = Form(False),
        current_user: User = Depends(get_current_user_from_cookie),
        db: Session = Depends(get_db)):
    worker_set_now(db)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    dispoCoupe = db.query(User).filter(User.job == "coupeur").order_by(User.lastJob).first()
    estimCoupe = whenFinished(dispoCoupe.lastJob, timeCoupe)
    dispoPliage = db.query(User).filter(User.job == "plieur").order_by(User.lastJob).first()
    if estimCoupe > dispoPliage.lastJob:
        dispoPliage.lastJob = estimCoupe
    estimPliage = whenFinished(dispoPliage.lastJob, timePliage)
    dispoSoudure = db.query(User).filter(User.job == "soudeur").order_by(User.lastJob).first()
    if estimPliage > dispoSoudure.lastJob:
        dispoSoudure.lastJob = estimPliage
    estimSoudure = whenFinished(dispoSoudure.lastJob, timeSoudure)
    if not dispoCoupe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user created for cutting job")
    if not dispoPliage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user created for folding job")
    if not dispoCoupe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user created for welding job")
    db_task = models.Task(name=name,
                          serialNumber=serialNumber,
                          description=description,
                          timePliage=timePliage,
                          timeCoupe=timeCoupe,
                          timeSoudure=timeSoudure,
                          coupeDoneBy=dispoCoupe.id,
                          pliageDoneBy=dispoPliage.id,
                          soudureDoneBy=dispoSoudure.id,
                          estimatedCoupe=estimCoupe,
                          estimatedPliage=estimPliage,
                          estimatedSoudure=estimSoudure,
                          save=save
                          )
    dispoCoupe.lastJob = whenFinished(dispoCoupe.lastJob, timeCoupe)
    dispoPliage.lastJob = whenFinished(dispoPliage.lastJob, timePliage)
    dispoSoudure.lastJob = whenFinished(dispoSoudure.lastJob, timeSoudure)

    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return RedirectResponse(url="/connected/home", status_code=303)


def whenFinished(startTime: datetime, addMinutes: int) -> datetime:
    if(startTime.hour > 15 and startTime.hour <=23):
        if startTime.weekday()==4:
            startTime = startTime + timedelta(days=3)
        elif startTime.weekday()==5:
            startTime = startTime + timedelta(days=2)
        else :
            startTime = startTime + timedelta(days=1)
        startTime = startTime.replace(hour=7, minute=0, second=0)
    if startTime.hour < 7 and startTime.hour >= 0:
        if startTime.weekday()==5:
            startTime = startTime + timedelta(days=2)
        if startTime.weekday()==6:
            startTime = startTime + timedelta(days=1)
        startTime = startTime.replace(hour=7, minute=0, second=0)
    while addMinutes > 0:
        current_day_end = startTime.replace(hour=15, minute=0, second=0, microsecond=0)
        minutes_until_end_of_day = (current_day_end - startTime).total_seconds() / 60

        if addMinutes <= minutes_until_end_of_day:
            endTime = startTime + timedelta(minutes=addMinutes)
            return endTime
        else:
            addMinutes -= minutes_until_end_of_day
            startTime = current_day_end + timedelta(days=1)
            startTime = startTime.replace(hour=7, minute=0, second=0, microsecond=0)
            if startTime.weekday() == 5:
                startTime += timedelta(days=2)
            elif startTime.weekday() == 6:
                startTime += timedelta(days=1)
    return startTime


def rearrangeCoupe(db: Session = Depends(get_db())):
    for user in db.query(User).filter(User.job == "coupeur").all():
        user.lastJob = datetime.now()

    for task in db.query(Task).order_by(Task.id).all():
        if task.coupeDoneBy != 0:
            dispoCoupe = firstDispo("coupeur",db)

            timeToGo = (task.estimatedCoupe - datetime.now()).total_seconds() // 60
            if timeToGo < task.timeCoupe:
                if timeToGo < 0:
                    task.coupeDoneBy = 0
                if task.coupeDoneBy != 0:
                    task.estimatedCoupe = whenFinished(dispoCoupe.lastJob, int(timeToGo))
                    task.coupeDoneBy = dispoCoupe.id
                    dispoCoupe.lastJob = task.estimatedCoupe
            else:
                task.estimatedCoupe = whenFinished(dispoCoupe.lastJob, task.timeCoupe)
                task.coupeDoneBy = dispoCoupe.id
                dispoCoupe.lastJob = task.estimatedCoupe


def rearrangePliage(db: Session = Depends(get_db())):
    for user in db.query(User).filter(User.job == "plieur").all():
        user.lastJob = datetime.now()

    for task in db.query(Task).order_by(Task.timePliage).all():
        if task.pliageDoneBy != 0:
            dispoPliage = firstDispo("plieur",db)

            timeToGo = (task.estimatedPliage - datetime.now()).total_seconds() // 60
            if timeToGo < task.timePliage:
                if timeToGo < 0:
                    task.pliageDoneBy = 0
                if task.pliageDoneBy != 0:
                    if dispoPliage.lastJob < task.estimatedCoupe:
                        task.estimatedPliage = whenFinished(task.estimatedCoupe, int(timeToGo))
                    else:
                        task.estimatedPliage = whenFinished(dispoPliage.lastJob, int(timeToGo))
                    task.pliageDoneBy = dispoPliage.id
                    dispoPliage.lastJob = task.estimatedPliage
            else:
                if dispoPliage.lastJob < task.estimatedCoupe:
                    task.estimatedPliage = whenFinished(task.estimatedCoupe, task.timePliage)
                else:
                    task.estimatedPliage = whenFinished(dispoPliage.lastJob, task.timePliage)
                task.pliageDoneBy = dispoPliage.id
                dispoPliage.lastJob = task.estimatedPliage


def rearrangeSoudure(db: Session = Depends(get_db())):
    for user in db.query(User).filter(User.job == "soudeur").all():
        user.lastJob = datetime.now()

    for task in db.query(Task).order_by(Task.id).all():
        if task.soudureDoneBy >0:
            dispoSoudure = firstDispo("soudeur",db)
            timeToGo = (task.estimatedSoudure - datetime.now()).total_seconds()//60
            if timeToGo < task.timeSoudure:
                if timeToGo < 0:
                    task.soudureDoneBy = 0
                if task.soudureDoneBy != 0:
                    if dispoSoudure.lastJob < task.estimatedPliage:
                        task.estimatedSoudure = whenFinished(task.estimatedPliage, int(timeToGo))
                    else:
                        task.estimatedSoudure = whenFinished(dispoSoudure.lastJob, int(timeToGo))
                    task.soudureDoneBy = dispoSoudure.id
                    dispoSoudure.lastJob = task.estimatedSoudure
            else:
                if dispoSoudure.lastJob < task.estimatedPliage:
                    task.estimatedSoudure = whenFinished(task.estimatedPliage, task.timeSoudure)
                else:
                    task.estimatedSoudure = whenFinished(dispoSoudure.lastJob, task.timeSoudure)
                task.soudureDoneBy = dispoSoudure.id
                dispoSoudure.lastJob = task.estimatedSoudure
            # for usera in db.query(User).filter(User.job == "soudeur").order_by(User.lastJob).all():
            #     print(usera.lastJob)

@router.put("/finish_coupe/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def finish_coupe(task_id: int,
                       db: Session = Depends(get_db)):
    taskU = db.query(Task).filter(Task.id == task_id).first()
    if not taskU:
        raise HTTPException(status_code=404, detail="Task not found")
    taskU.coupeDoneBy = 0
    rearrangeCoupe(db)
    db.commit()
    return successful_response(status_code=204)


@router.put("/finish_pliage/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def finish_pliage(task_id: int,
                        db: Session = Depends(get_db)):
    taskU = db.query(Task).filter(Task.id == task_id).first()
    if not taskU:
        raise HTTPException(status_code=404, detail="Task not found")
    taskU.pliageDoneBy = 0
    taskU.coupeDoneBy = 0
    rearrangeCoupe(db)
    rearrangePliage(db)
    db.commit()
    return successful_response(status_code=204)


@router.put("/finish_soudure/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def finish_soudure(task_id: int,
                         db: Session = Depends(get_db)):
    taskU = db.query(Task).filter(Task.id == task_id).first()
    if not taskU:
        raise HTTPException(status_code=404, detail="Task not found")
    if(taskU.soudureDoneBy>=0):
        taskU.soudureDoneBy = 0
    taskU.pliageDoneBy = 0
    taskU.coupeDoneBy = 0
    rearrangeCoupe(db)
    rearrangePliage(db)
    rearrangeSoudure(db)
    taskU.estimatedSoudure = datetime.now()
    db.commit()
    return successful_response(status_code=204)


@router.put("/finish_task/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def finish_task(task_id: int,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user_from_cookie)):
    taskU = db.query(Task).filter(Task.id == task_id).first()
    if not taskU:
        raise HTTPException(status_code=404, detail="Task not found")
    if(taskU.coupeDoneBy==current_user.id):
        taskU.coupeDoneBy = 0
    elif(taskU.pliageDoneBy==current_user.id):
        taskU.pliageDoneBy = 0
        taskU.coupeDoneBy = 0
    elif(taskU.soudureDoneBy==current_user.id):
        if taskU.soudureDoneBy >= 0:
            taskU.soudureDoneBy = 0
        taskU.pliageDoneBy = 0
        taskU.coupeDoneBy = 0
    rearrangeCoupe(db)
    rearrangePliage(db)
    rearrangeSoudure(db)
    if(taskU.soudureDoneBy==1):
        taskU.estimatedSoudure = datetime.now()
    db.commit()
    return successful_response(status_code=204)

@router.delete("/delete/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def task_book(task_id: int, db: Session = Depends(get_db)):

    taskModel = db.query(Task).filter(Task.id == task_id).first()
    if taskModel is None:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(taskModel)
    db.commit()
    return successful_response(status_code=204)


@router.put("/admin_hide/{task_id}")
async def update_owner(task_id: int,
                       db: Session = Depends(get_db)):
    taskModel = db.query(Task).filter(Task.id == task_id).first()
    if not taskModel:
        raise HTTPException(status_code=404, detail="Book not found")
    taskModel.soudureDoneBy = -2
    db.commit()
    print("taskModel updated ", taskModel.soudureDoneBy)

@router.put("/hide/{task_id}")
async def update_owner(task_id: int,
                       db: Session = Depends(get_db)):
    taskModel = db.query(Task).filter(Task.id == task_id).first()
    if not taskModel:
        raise HTTPException(status_code=404, detail="Book not found")
    taskModel.soudureDoneBy = -1
    db.commit()
    print("taskModel updated ", taskModel.soudureDoneBy)

def successful_response(status_code: int):
    return {
        'status': status_code,
        'transaction': 'Successful'
    }
#
#
#
#
# @router.get("/edit/{book_id}", response_class=HTMLResponse)
# async def edit_book(request: Request, book_id: int,
#                     db: Session = Depends(get_db),
#                     current_user: Users = Depends(get_current_user_from_cookie)):
#     book = db.query(models.Books).filter(models.Books.id == book_id).first()
#     if not book:
#         raise HTTPException(status_code=404, detail="Book not found")
#     if not current_user:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
#     if current_user.id != book.owners:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized to edit this book")
#     return templates.TemplateResponse("connected_edit_book.html", {"request": request, "book": book, "current_user": current_user})
#
#
# @router.post("/edit/{book_id}")
# async def update_book(book_id: int,
#                       price: float = Form(...),
#                       db: Session = Depends(get_db)):
#     book = db.query(models.Books).filter(models.Books.id == book_id).first()
#     if not book:
#         raise HTTPException(status_code=404, detail="Book not found")
#
#     book.price = price
#
#     db.commit()
#     return RedirectResponse(url="/connected/", status_code=303)
#
#
#
# @router.get("/editAdmin/{book_id}", response_class=HTMLResponse)
# async def edit_book(request: Request, book_id: int,
#                     db: Session = Depends(get_db),
#                     current_user: Users = Depends(get_current_user_from_cookie)):
#     book = db.query(models.Books).filter(models.Books.id == book_id).first()
#     if not book:
#         raise HTTPException(status_code=404, detail="Book not found")
#     if not current_user:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
#     if current_user.id != book.owners and not current_user.admin:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized to edit this book")
#     return templates.TemplateResponse("admin_edit_book.html", {"request": request, "book": book, "current_user": current_user})
#
#
# @router.post("/editAdmin/{book_id}")
# async def update_book(book_id: int,
#                       name: str = Form(...),
#                       author: str = Form(...),
#                       publisher: str = Form(...),
#                       price: float = Form(...),
#                       db: Session = Depends(get_db)):
#     book = db.query(models.Books).filter(models.Books.id == book_id).first()
#     if not book:
#         raise HTTPException(status_code=404, detail="Book not found")
#
#     book.price = price
#     book.name = name
#     book.author = author
#     book.publisher = publisher
#
#     db.commit()
#     return RedirectResponse(url="/connected/allbooks/", status_code=303)
#





