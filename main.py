from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
from database import engine, get_db
from auth import get_current_user, get_password_hash, verify_password, create_access_token, get_current_user_from_cookie

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Swi9a")

import os
os.makedirs("static/css", exist_ok=True)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request, product: str = None, city: str = None, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    query = db.query(models.PrixPublic)
    if product:
        query = query.filter(models.PrixPublic.product.ilike(f"%{product}%"))
    if city:
        query = query.filter(models.PrixPublic.city.ilike(f"%{city}%"))
    prices = query.order_by(models.PrixPublic.created_at.desc()).all()
    return templates.TemplateResponse(request=request, name="home.html", context={"prices": prices, "user": user})

@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={})

@app.post("/register")
def register(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if db_user:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "Username already exists"})
    
    hashed_pass = get_password_hash(password)
    new_user = models.User(username=username, password_hash=hashed_pass)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid username or password"})
    
    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    total_expenses = db.query(func.sum(models.Depense.amount)).filter(models.Depense.user_id == current_user.id).scalar() or 0.0
    recent_expenses = db.query(models.Depense).filter(models.Depense.user_id == current_user.id).order_by(models.Depense.created_at.desc()).limit(10).all()
    
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": current_user,
        "total_expenses": total_expenses,
        "recent_expenses": recent_expenses
    })

@app.get("/add-prix", response_class=HTMLResponse)
def add_prix_form(request: Request, current_user: models.User = Depends(get_current_user)):
    return templates.TemplateResponse(request=request, name="add_prix.html", context={"user": current_user})

@app.post("/add-prix")
def add_prix(
    request: Request,
    product: str = Form(...),
    price: float = Form(...),
    city: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_prix = models.PrixPublic(product=product, price=price, city=city, user_id=current_user.id)
    db.add(new_prix)
    db.commit()
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@app.get("/add-depense", response_class=HTMLResponse)
def add_depense_form(request: Request, current_user: models.User = Depends(get_current_user)):
    return templates.TemplateResponse(request=request, name="add_depense.html", context={"user": current_user})

@app.post("/add-depense")
def add_depense(
    request: Request,
    amount: float = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    avg_expense = db.query(func.avg(models.Depense.amount)).filter(
        models.Depense.user_id == current_user.id,
        models.Depense.category == category
    ).scalar()
    
    ai_message = ""
    if avg_expense is None:
        ai_message = f"First expense in {category}. Keep tracking to see insights!"
    elif amount > avg_expense:
        ai_message = "You are spending more than usual on this category."
    elif amount < avg_expense:
        ai_message = "Good job, your spending is under average."
    else:
        ai_message = "You are spending exactly your usual average."

    new_depense = models.Depense(amount=amount, category=category, user_id=current_user.id)
    db.add(new_depense)
    db.commit()
    
    return templates.TemplateResponse(request=request, name="add_depense.html", context={
        "user": current_user,
        "success_msg": "Expense added successfully!",
        "ai_message": ai_message
    })
