from fastapi import FastAPI, HTTPException,status,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.schemas.job import JobCreate,JobResponse
from backend.schemas.user import UserCreate,UserResponse
from backend.schemas.application import ApplicationCreate, ApplicationResponse


app = FastAPI()

# Test Jobs data
jobs: list[dict] = [
    {
        "id":1,
        "title":"Software Engineer",
        "company":"Tech Corp",
        "location":"New York, NY",
        "description":"Develop and maintain software applications."
    },
    {
            "id":2,
            "title":"Software Engineer",
            "company":"Tech Corp",
            "location":"New York, NY",
            "description":"Develop and maintain software applications."
        }
] 

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/jobs")
def get_jobs():
    return jobs

@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: int):
    for job in jobs:

        if job.get("id") == job_id:
            return job
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
        )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )
