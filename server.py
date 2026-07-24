from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from googleapiclient.errors import HttpError

from youtube import fetch_channel_info, handle_api_error


class SearchRequest(BaseModel):
    channel_name: str


app = FastAPI(title="YouTube Channel Info API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "YouTube Channel Info API is running"}


@app.post("/search")
def search_channel(request: SearchRequest):
    channel_name = request.channel_name.strip()
    if not channel_name:
        raise HTTPException(status_code=400, detail="Channel name is required")

    try:
        result = fetch_channel_info(channel_name)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HttpError as exc:
        raise HTTPException(status_code=502, detail=handle_api_error(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
