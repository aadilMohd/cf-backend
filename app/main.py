from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.models.models import User
from app.security import get_current_user
from app.remainders import check_and_send_reminders
from app.push_notifications import send_push
from app.routers import auth, cheques, users, invites

# Database imports (uncomment if using automatic table creation on startup)
# from app.database import engine, Base
# Base.metadata.create_all(bind=engine)

# Import all API routers
from app.routers import auth, cheques, users, invites

app = FastAPI(title="ChequeFlow Engine", version="1.0")

# Enable CORS (allows frontend applications to communicate with this backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(cheques.router)
app.include_router(invites.router)


@app.get("/")
def read_root():
    return {"status": "ChequeFlow Core Engine Running"}

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(
        check_and_send_reminders, "interval", hours=1,
        max_instances=1, coalesce=True, id="cheque-reminders",
    )
    scheduler.start()

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown(wait=False)


# TEMPORARY: delete both before the pilot
if settings.environment == "dev":
    @app.post("/_debug/trigger-reminders")
    def debug_trigger_reminders(_: User = Depends(get_current_user)):
        check_and_send_reminders()
        return {"status": "triggered"}

    @app.post("/_debug/test-push")
    def debug_test_push(current_user: User = Depends(get_current_user)):
        return {"sent": send_push(current_user.fcm_token, "Test", "This is a test notification")}