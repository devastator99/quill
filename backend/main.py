from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from solana_utils import shutdown_event
from endpoints import router

# Initialize FastAPI app
app = FastAPI(title="Socratic")

# Create database tables
Base.metadata.create_all(bind=engine)

@app.on_event("shutdown")
async def app_shutdown_event():
    await shutdown_event()

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
