from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime, timezone
import httpx


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class SavedRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_identifier: str = Field(default="default_user")
    name: str
    method: str
    endpoint: str
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    category: str
    is_favorite: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SavedRequestCreate(BaseModel):
    name: str
    method: str
    endpoint: str
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    category: str
    is_favorite: bool = False


class SavedRequestUpdate(BaseModel):
    name: Optional[str] = None
    is_favorite: Optional[bool] = None


class RequestHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_identifier: str = Field(default="default_user")
    method: str
    endpoint: str
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    response_data: Any = None
    status_code: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FigmaProxyRequest(BaseModel):
    method: str
    endpoint: str
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None


# Figma API Routes
@api_router.post("/figma/proxy")
async def proxy_figma_request(request: FigmaProxyRequest):
    """Proxy requests to Figma API to handle CORS"""
    # Validate HTTP method first, before try block
    if request.method.upper() not in ["GET", "POST", "PUT", "DELETE"]:
        raise HTTPException(status_code=400, detail="Unsupported HTTP method")
    
    try:
        base_url = "https://api.figma.com/v1"
        full_url = f"{base_url}{request.endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if request.method.upper() == "GET":
                response = await client.get(full_url, headers=request.headers)
            elif request.method.upper() == "POST":
                response = await client.post(full_url, headers=request.headers, json=request.body)
            elif request.method.upper() == "PUT":
                response = await client.put(full_url, headers=request.headers, json=request.body)
            elif request.method.upper() == "DELETE":
                response = await client.delete(full_url, headers=request.headers)
            
            # Save to history
            history_item = RequestHistory(
                method=request.method,
                endpoint=request.endpoint,
                headers=request.headers,
                body=str(request.body) if request.body else None,
                response_data=response.json() if response.status_code == 200 else response.text,
                status_code=response.status_code
            )
            
            doc = history_item.model_dump()
            doc['timestamp'] = doc['timestamp'].isoformat()
            await db.request_history.insert_one(doc)
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "headers": dict(response.headers)
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/figma/page")
async def get_figma_page(request: FigmaProxyRequest):
    """Get only the first page (canvas) from a Figma file"""
    try:
        # Extract file_key from endpoint
        if not request.endpoint.startswith('/files/'):
            raise HTTPException(status_code=400, detail="Endpoint must be in format /files/:file_key")
        
        base_url = "https://api.figma.com/v1"
        full_url = f"{base_url}{request.endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(full_url, headers=request.headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract first page: root > document > children[0]
                if 'document' in data and 'children' in data['document'] and len(data['document']['children']) > 0:
                    first_page = data['document']['children'][0]
                    
                    # Save to history
                    history_item = RequestHistory(
                        method="PAGE",
                        endpoint=request.endpoint,
                        headers=request.headers,
                        body=None,
                        response_data=first_page,
                        status_code=200
                    )
                    
                    doc = history_item.model_dump()
                    doc['timestamp'] = doc['timestamp'].isoformat()
                    await db.request_history.insert_one(doc)
                    
                    return {
                        "status_code": 200,
                        "data": first_page,
                        "headers": dict(response.headers)
                    }
                else:
                    raise HTTPException(status_code=404, detail="No pages found in document")
            else:
                return {
                    "status_code": response.status_code,
                    "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    "headers": dict(response.headers)
                }
                
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Saved Requests Routes
@api_router.get("/saved-requests", response_model=List[SavedRequest])
async def get_saved_requests():
    requests = await db.saved_requests.find({}, {"_id": 0}).to_list(1000)
    for req in requests:
        if isinstance(req.get('created_at'), str):
            req['created_at'] = datetime.fromisoformat(req['created_at'])
    return requests


@api_router.post("/saved-requests", response_model=SavedRequest)
async def create_saved_request(request: SavedRequestCreate):
    saved_req = SavedRequest(**request.model_dump())
    doc = saved_req.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.saved_requests.insert_one(doc)
    return saved_req


@api_router.put("/saved-requests/{request_id}")
async def update_saved_request(request_id: str, update: SavedRequestUpdate):
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.saved_requests.update_one(
        {"id": request_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return {"message": "Request updated successfully"}


@api_router.delete("/saved-requests/{request_id}")
async def delete_saved_request(request_id: str):
    result = await db.saved_requests.delete_one({"id": request_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"message": "Request deleted successfully"}


# Request History Routes
@api_router.get("/request-history", response_model=List[RequestHistory])
async def get_request_history():
    history = await db.request_history.find({}, {"_id": 0}).sort("timestamp", -1).to_list(100)
    for item in history:
        if isinstance(item.get('timestamp'), str):
            item['timestamp'] = datetime.fromisoformat(item['timestamp'])
    return history


@api_router.delete("/request-history")
async def clear_request_history():
    await db.request_history.delete_many({})
    return {"message": "History cleared successfully"}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()