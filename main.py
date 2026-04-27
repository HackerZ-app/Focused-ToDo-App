from fastapi import FastAPI, Request, Form, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta, date

import models
from database import SessionLocal, engine

from fastapi.staticfiles import StaticFiles

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dynamic To-Do List")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Auth Config
SECRET_KEY = "super-secret-key-for-development-only"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    user = db.query(models.User).filter(models.User.username == username).first()
    return user

def htmx_redirect(url: str):
    response = HTMLResponse(status_code=status.HTTP_401_UNAUTHORIZED)
    response.headers["HX-Redirect"] = url
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid username or password"})
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        if len(password) < 4:
            return templates.TemplateResponse(request=request, name="register.html", context={"error": "Password must be at least 4 characters"})
        user = db.query(models.User).filter(models.User.username == username).first()
        if user:
            return templates.TemplateResponse(request=request, name="register.html", context={"error": "Username already registered"})
        
        hashed_password = get_password_hash(password)
        new_user = models.User(username=username, hashed_password=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user.username}, expires_delta=access_token_expires
        )
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        return response
    except Exception as e:
        print(f"Registration Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, filter: str = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Render the main page with all tasks."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    query = db.query(models.Task).filter(models.Task.user_id == current_user.id)
    if filter and filter in ["High", "Medium", "Low"]:
        query = query.filter(models.Task.priority == filter)
        
    tasks = query.order_by(models.Task.id.desc()).all()
    
    badge_thresholds = [3, 5, 10, 20]
    context = {"tasks": tasks, "current_user": current_user, "badge_thresholds": badge_thresholds, "now": datetime.now(), "filter": filter}
    
    if "HX-Request" in request.headers:
        return templates.TemplateResponse(request=request, name="task_list.html", context=context)
        
    return templates.TemplateResponse(request=request, name="index.html", context=context)

@app.get("/board", response_class=HTMLResponse)
async def board(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Render the Kanban board page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    tasks = db.query(models.Task).filter(models.Task.user_id == current_user.id).order_by(models.Task.id.desc()).all()
    
    badge_thresholds = [3, 5, 10, 20]
    return templates.TemplateResponse(request=request, name="board.html", context={"tasks": tasks, "current_user": current_user, "badge_thresholds": badge_thresholds, "now": datetime.now()})

@app.get("/focus", response_class=HTMLResponse)
async def focus(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Render the Focus Mode page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    tasks = db.query(models.Task).filter(
        models.Task.user_id == current_user.id,
        models.Task.completed == False,
        models.Task.status != "Done"
    ).order_by(models.Task.id.desc()).all()
    
    badge_thresholds = [3, 5, 10, 20]
    return templates.TemplateResponse(request=request, name="focus.html", context={"tasks": tasks, "current_user": current_user, "badge_thresholds": badge_thresholds})

@app.get("/stats", response_class=HTMLResponse)
async def stats(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Render the Insights/Stats page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    completed_tasks = db.query(models.Task).filter(
        models.Task.user_id == current_user.id,
        models.Task.completed == True,
        models.Task.completed_at != None
    ).all()
    
    # 30-day activity dict
    activity_dict = {}
    today = date.today()
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        activity_dict[day.isoformat()] = 0
        
    for task in completed_tasks:
        if task.completed_at:
            task_date = task.completed_at.isoformat()
            if task_date in activity_dict:
                activity_dict[task_date] += 1
                
    badge_thresholds = [3, 5, 10, 20]
    return templates.TemplateResponse(request=request, name="stats.html", context={"activity_dict": activity_dict, "current_user": current_user, "badge_thresholds": badge_thresholds})

@app.put("/tasks/{task_id}/status", response_class=HTMLResponse)
async def update_task_status(request: Request, task_id: int, status_val: str = Form(..., alias="status"), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Update a task's status and return the board columns HTML snippet."""
    if not current_user:
        return htmx_redirect("/login")
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == current_user.id).first()
    if task:
        task.status = status_val
        if status_val == "Done" and not task.completed:
            task.completed = True
            task.completed_at = date.today()
            current_user.total_completed_tasks += 1
            if current_user.last_completed_date == date.today() - timedelta(days=1):
                current_user.daily_streak += 1
            elif current_user.last_completed_date != date.today():
                current_user.daily_streak = 1
            current_user.last_completed_date = date.today()
        elif status_val != "Done" and task.completed:
            task.completed = False
            task.completed_at = None
            current_user.total_completed_tasks = max(0, current_user.total_completed_tasks - 1)
            
        db.commit()
        
    tasks = db.query(models.Task).filter(models.Task.user_id == current_user.id).order_by(models.Task.id.desc()).all()
    return templates.TemplateResponse(request=request, name="board_columns.html", context={"tasks": tasks, "now": datetime.now()})

@app.post("/tasks", response_class=HTMLResponse)
async def add_task(request: Request, title: str = Form(...), due_date: str = Form(None), priority: str = Form("Medium"), tag: str = Form(None), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Add a new task and return the task HTML snippet."""
    if not current_user:
        return htmx_redirect("/login")
        
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.fromisoformat(due_date)
        except ValueError:
            pass

    new_task = models.Task(title=title, completed=False, due_date=parsed_due_date, priority=priority, tag=tag, user_id=current_user.id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return templates.TemplateResponse(request=request, name="task.html", context={"task": new_task, "now": datetime.now()})

@app.put("/tasks/{task_id}/toggle", response_class=HTMLResponse)
async def toggle_task(request: Request, task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Toggle a task's completion status and return the updated task HTML snippet."""
    if not current_user:
        return htmx_redirect("/login")
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == current_user.id).first()
    if task:
        task.completed = not task.completed
        
        # Gamification logic
        today = date.today()
        if task.completed:
            task.completed_at = today
            current_user.total_completed_tasks += 1
            if current_user.last_completed_date == today - timedelta(days=1):
                current_user.daily_streak += 1
            elif current_user.last_completed_date != today:
                current_user.daily_streak = 1
            current_user.last_completed_date = today
        else:
            task.completed_at = None
            current_user.total_completed_tasks = max(0, current_user.total_completed_tasks - 1)
            
        db.commit()
        db.refresh(task)
        
        badge_thresholds = [3, 5, 10, 20]
        task_html = templates.TemplateResponse(request=request, name="task.html", context={"task": task, "now": datetime.now()}).body.decode('utf-8')
        dashboard_html = templates.TemplateResponse(request=request, name="dashboard.html", context={"current_user": current_user, "badge_thresholds": badge_thresholds, "oob": True}).body.decode('utf-8')
        
        return HTMLResponse(content=task_html + dashboard_html)
    return HTMLResponse(status_code=404)

@app.delete("/tasks/{task_id}", response_class=HTMLResponse)
async def delete_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Delete a task and return an empty response to remove it from the DOM."""
    if not current_user:
        return htmx_redirect("/login")
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.user_id == current_user.id).first()
    if task:
        db.delete(task)
        db.commit()
    return HTMLResponse(content="")
