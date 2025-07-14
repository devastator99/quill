from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from solana_utils import shared_solana_client 
from endpoints import router

app = FastAPI(title="Socratic")

# Create database tables
Base.metadata.create_all(bind=engine)

# Include API endpoints
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    # Any startup tasks can be added here
    pass

@app.on_event("shutdown")
async def shutdown_event():
    await shared_solana_client.close()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
