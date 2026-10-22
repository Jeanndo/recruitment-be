from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException,status,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.schemas.job import JobCreate,JobResponse


app = FastAPI()

# Test Jobs data

jobs: list[dict] = [
    {
        "id":1,
        "title":"Software Engineer",
        "location":"New York, NY",
        "description":"Develop and maintain software applications.",
        "employment_type": "Full-time",
        "responsibilities": ["string1","string2","string3"],
        "requirements": ["string1","string2","string3"],
        "summary": "A short summary of the Software Engineer role.",
        "closing_date": "2026-10-22",
        "status": "Draft",
        "created_at": "2026-10-22T12:20:12.757Z",
        "updated_at": "2026-10-22T12:20:12.758Z"
    },
    {
            "id":2,
            "title":"Software Engineer",
            "location":"New York, NY",
            "description":"Develop and maintain software applications.",
            "employment_type": "Full-time",
            "responsibilities": ["string1","string2","string3"],
            "requirements": ["string1","string2","string3"],
            "summary": "A short summary of the Software Engineer role.",
            "closing_date": "2026-10-22",
            "status": "Draft",
            "created_at": "2026-10-22T12:20:12.757Z",
            "updated_at": "2026-10-22T12:20:12.758Z"
    }
] 

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/jobs", response_model=list[JobResponse])
def get_jobs():
    return jobs



@app.post("/api/v1/jobs", response_model=JobResponse,status_code=status.HTTP_201_CREATED)
def create_job(job:JobCreate):
    new_id = max(j["id"] for j in jobs) + 1 if jobs else 1
    now = datetime.now(UTC).isoformat()

    new_job = {
        "id":new_id,
        "title":job.title,
        "location": job.location,
        "employment_type": job.employment_type,
        "summary": job.summary,
        "description": job.description,
        "responsibilities": job.responsibilities,
        "requirements": job.requirements,
        "closing_date": job.closing_date,
        # The status comes from the payload, which defaults to "Draft".
        "status": job.status,
        "created_at": now,
        "updated_at": now

        }

    jobs.append(new_job)
    
    return new_job


@app.get("/api/v1/jobs/{job_id}",response_model=JobResponse)
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

    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": message},
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    
    errors = [
        {
            "loc": list(error["loc"]),
            "msg": error["msg"],
            "type": error["type"],
        }
        for error in exception.errors()
    ]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": errors},
    )
