from fastapi import FastAPI, APIRouter, HTTPException
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, Any
import httpx
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

class FigmaProxyRequest(BaseModel):
    method: str
    endpoint: str
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None

# Figma API Routes (without MongoDB dependency)
@api_router.post("/figma/proxy")
async def proxy_figma_request(request: FigmaProxyRequest):
    """Proxy requests to Figma API to handle CORS"""
    # Validate HTTP method first
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
            
            # Return response without saving to database
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

# Mock endpoints for saved requests and history (return empty data)
@api_router.get("/saved-requests")
async def get_saved_requests():
    return []

@api_router.post("/saved-requests")
async def create_saved_request(request: dict):
    return {"message": "Request saved (MongoDB not available)", "id": "mock-id"}

@api_router.put("/saved-requests/{request_id}")
async def update_saved_request(request_id: str, update: dict):
    return {"message": "Request updated (MongoDB not available)"}

@api_router.delete("/saved-requests/{request_id}")
async def delete_saved_request(request_id: str):
    return {"message": "Request deleted (MongoDB not available)"}

@api_router.get("/request-history")
async def get_request_history():
    return []

@api_router.delete("/request-history")
async def clear_request_history():
    return {"message": "History cleared (MongoDB not available)"}

# Health check endpoint
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Server running without MongoDB"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)