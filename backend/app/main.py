from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas.chat import ChatRequest
from app.services.intent import IntentError, interpret
from app.services.orchestrator import execute

app = FastAPI(title="TaskPilot API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TaskPilot API"}


@app.post("/api/chat")
def chat(request: ChatRequest):
    events = ["Request received"]
    try:
        task = interpret(request.message)
    except IntentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    events.extend(["Intent identified", "Input validated", "CLI process started", "Website crawling in progress"])
    execution = execute(task)
    events.append("CLI output captured")
    events.append("JSON validated" if execution["result"] else "JSON validation failed")
    events.append("Execution completed" if execution["status"] == "success" else "Execution failed")
    result = execution["result"]
    response = result["summary"] if result else execution.get("parse_error") or "The crawler could not complete the request."
    return {"status": execution["status"], "task": task.model_dump(), "execution": execution,
            "original_request": request.message, "response": response, "events": events}
