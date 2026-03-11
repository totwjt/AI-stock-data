from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import json
from app.database import async_session
from app.models.log import ApiLog


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        params = None
        if request.method in ["GET", "POST"]:
            try:
                if request.method == "GET":
                    params = str(request.query_params)
                else:
                    body = await request.body()
                    if body:
                        params = body.decode()
            except:
                pass
        
        response = await call_next(request)
        
        response_time = (time.time() - start_time) * 1000
        
        error_message = None
        if response.status_code >= 400:
            try:
                error_message = str(response.body)
            except:
                error_message = "Error"
        
        async with async_session() as session:
            log = ApiLog(
                api_name=request.url.path.split("/")[-1] or "root",
                method=request.method,
                path=str(request.url.path),
                params=params,
                response_status=response.status_code,
                response_time=response_time,
                error_message=error_message
            )
            session.add(log)
            await session.commit()
        
        return response
