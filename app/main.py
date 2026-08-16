from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Database imports (uncomment if using automatic table creation on startup)
# from app.database import engine, Base
# Base.metadata.create_all(bind=engine)

# Import all API routers
from app.routers import auth, cheques, users

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