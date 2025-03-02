import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi.middleware.cors import CORSMiddleware
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all frontend URLs (use specific URLs in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# ---------------------------
# Serve Frontend Files
# ---------------------------
# Assumes project structure:
# chat-app/
# ├── backend/
# │   └── main.py
# └── frontend/
#     ├── index.html
#     ├── client.js
#     └── style.css (optional)
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.join(current_dir, "..", "frontend")

# Serve index.html at the root URL
@app.get("/")
async def get_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# Mount static assets (client.js, style.css, etc.) at /static
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Optional test API endpoint
@app.get("/api/hello")
def read_root():
    return {"message": "Hello, your API is live!"}

# ---------------------------
# Database Setup
# ---------------------------
DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, index=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ---------------------------
# WebSocket Connection Manager
# ---------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# ---------------------------
# WebSocket Endpoint for Chat
# ---------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    db = SessionLocal()
    
    # Send chat history on connection
    messages = db.query(ChatMessage).order_by(ChatMessage.timestamp).all()
    for msg in messages:
        await websocket.send_text(f"{msg.timestamp} {msg.sender}: {msg.content}")
    
    try:
        while True:
            data = await websocket.receive_text()
            # Expected format: "username: message"
            sender, content = data.split(":", 1)
            
            # Save message to database
            chat_message = ChatMessage(sender=sender.strip(), content=content.strip())
            db.add(chat_message)
            db.commit()
            
            # Broadcast message to all connected clients
            await manager.broadcast(f"{chat_message.timestamp} {chat_message.sender}: {chat_message.content}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        db.close()

# ---------------------------
# Clear Chat Endpoint
# ---------------------------
@app.delete("/api/clear")
async def clear_chat():
    db = SessionLocal()
    try:
        db.query(ChatMessage).delete()
        db.commit()  # ✅ Ensure database commit before closing
    finally:
        db.close()

    await manager.broadcast("clear_chat")  # ✅ Notify all clients to clear chat UI
    return {"message": "Chat cleared"}


