import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import BASE_DIR, UPLOADS_DIR, WORKSPACE_DIR, GEMINI_API_KEY
from ingestion.parser import parse_file
from ingestion.scraper import scrape_url
from ingestion.chunker import chunk_text
from rag.vector_store import VectorStore
from interview.session import InterviewSession, CandidateAnswer, InterviewHistoryManager
from interview.generator import QuestionGenerator
from interview.evaluator import InterviewEvaluator
from interview.ollama_client import OllamaClient

app = FastAPI(title="Interview Assist API", version="1.0.0")

# Enable CORS for local cross-origin development if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from interview.session import InterviewSession, CandidateAnswer, InterviewHistoryManager
from interview.generator import QuestionGenerator
from interview.evaluator import InterviewEvaluator
from interview.ollama_client import OllamaClient
from interview.llm_manager import LLMManager

# Global services & active sessions state
llm_manager = LLMManager()
vector_store = VectorStore(api_key=GEMINI_API_KEY)
ollama_client = llm_manager.ollama_client
history_manager = InterviewHistoryManager()
active_sessions: Dict[str, InterviewSession] = {}
current_settings = {
    "gemini_api_key": GEMINI_API_KEY,
    "ollama_model": "qwen3-coder:30b",
    "default_questions": 10,
    "default_level": "intermediate"
}

# --- Request/Response Models ---
class ScrapeUrlRequest(BaseModel):
    url: str

class RagSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    doc_id: Optional[str] = None

class StartInterviewRequest(BaseModel):
    level: str = "intermediate"       # beginner, intermediate, senior, architect
    total_questions: int = 10         # default 10
    focus_area: Optional[str] = "all" # all, csharp, sql, aspnet, azure, patterns, algorithms
    question_types: Optional[List[str]] = ["mcq", "true_false", "descriptive"]
    doc_ids: Optional[List[str]] = None

class SubmitAnswerRequest(BaseModel):
    question_id: int
    user_answer: str
    time_taken_seconds: Optional[int] = 0

class SettingsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    default_questions: Optional[int] = None
    default_level: Optional[str] = None


# --- Ingestion Endpoints ---
@app.post("/api/ingest/files")
async def ingest_files(files: List[UploadFile] = File(...)):
    """Uploads and ingests files (PDF, Markdown, TXT, DOCX) into RAG vector memory."""
    results = []
    for file in files:
        safe_filename = Path(file.filename).name
        target_path = UPLOADS_DIR / safe_filename
        
        # Save file to disk
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        try:
            parsed = parse_file(target_path)
            chunks = chunk_text(
                parsed["text"],
                source_name=safe_filename,
                metadata={"file_type": parsed.get("file_type", "unknown")}
            )
            doc_id = await vector_store.add_document(
                title=safe_filename,
                source=safe_filename,
                file_type=parsed.get("file_type", "unknown"),
                chunks=chunks
            )
            results.append({
                "filename": safe_filename,
                "doc_id": doc_id,
                "chunks_indexed": len(chunks),
                "status": "success"
            })
        except Exception as e:
            results.append({
                "filename": safe_filename,
                "error": str(e),
                "status": "failed"
            })
            
    return {"results": results, "stats": vector_store.get_stats()}

@app.post("/api/ingest/url")
async def ingest_url(req: ScrapeUrlRequest):
    """Scrapes a web URL and ingests its semantic content into RAG memory."""
    try:
        scraped = await scrape_url(req.url)
        chunks = chunk_text(
            scraped["text"],
            source_name=scraped["title"],
            metadata={"source_url": req.url, "file_type": "web_url"}
        )
        if not chunks:
            raise HTTPException(status_code=400, detail="No readable text content could be extracted from URL.")
            
        doc_id = await vector_store.add_document(
            title=scraped["title"],
            source=req.url,
            file_type="web_url",
            chunks=chunks
        )
        return {
            "status": "success",
            "doc_id": doc_id,
            "title": scraped["title"],
            "url": req.url,
            "chunks_indexed": len(chunks),
            "stats": vector_store.get_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to scrape URL: {str(e)}")

@app.post("/api/ingest/workspace")
async def ingest_workspace():
    """Auto-discovers and ingests all .md learning files in the current repository workspace."""
    md_files = sorted(list(WORKSPACE_DIR.glob("*.md")))
    if not md_files:
        raise HTTPException(status_code=404, detail="No .md files found in workspace root.")
        
    ingested = []
    for f in md_files:
        try:
            parsed = parse_file(f)
            chunks = chunk_text(
                parsed["text"],
                source_name=f.name,
                metadata={"file_type": "markdown", "workspace_file": True}
            )
            doc_id = await vector_store.add_document(
                title=f.name,
                source=str(f.name),
                file_type="markdown",
                chunks=chunks
            )
            ingested.append({"filename": f.name, "doc_id": doc_id, "chunks": len(chunks)})
        except Exception as e:
            print(f"Error ingesting {f.name}: {e}")
            
    return {
        "status": "success",
        "ingested_count": len(ingested),
        "files": ingested,
        "stats": vector_store.get_stats()
    }

@app.get("/api/documents")
async def get_documents():
    """Returns all ingested documents and vector store stats."""
    return {
        "documents": vector_store.get_documents(),
        "stats": vector_store.get_stats()
    }

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Deletes a document and its semantic chunks from memory and physically removes uploaded file from disk."""
    doc = vector_store.documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    source_name = doc.get("source") or doc.get("title")
    if source_name:
        file_path = UPLOADS_DIR / source_name
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                print(f"[Delete] Removed file from disk: {file_path}")
            except Exception as e:
                print(f"[Delete] Warning: Could not delete disk file {file_path}: {e}")

    deleted = vector_store.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "status": "success",
        "stats": vector_store.get_stats(),
        "areas": vector_store.get_knowledge_areas()
    }

@app.post("/api/rag/search")
async def search_rag(req: RagSearchRequest):
    """Performs semantic search over RAG memory."""
    results = await vector_store.search(query=req.query, top_k=req.top_k or 5, doc_id=req.doc_id)
    return {"query": req.query, "results": results}


# --- Interview Engine Endpoints ---
@app.post("/api/interview/start")
async def start_interview(req: StartInterviewRequest):
    """Configures and initializes a new interview session with generated questions."""
    session = InterviewSession(
        level=req.level,
        total_questions=req.total_questions,
        focus_area=req.focus_area or "all",
        question_types=req.question_types
    )
    
    generator = QuestionGenerator(
        vector_store,
        api_key=llm_manager.get_provider_config("gemini").get("api_key"),
        ollama_model=llm_manager.get_provider_config("ollama").get("model"),
        llm_manager=llm_manager
    )
    questions = await generator.generate_questions(
        level=req.level,
        total_questions=req.total_questions,
        focus_area=req.focus_area or "all",
        question_types=req.question_types,
        doc_ids=req.doc_ids
    )
    
    session.questions = questions
    session.status = "in_progress"
    active_sessions[session.session_id] = session
    
    return session.to_dict()

@app.get("/api/interview/{session_id}")
async def get_interview_session(session_id: str):
    """Fetches session state and questions."""
    session = active_sessions.get(session_id)
    if not session:
        # Check historical sessions
        hist = history_manager.get_by_id(session_id)
        if hist:
            return hist
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return session.to_dict()

@app.post("/api/interview/{session_id}/answer")
async def submit_answer(session_id: str, req: SubmitAnswerRequest):
    """Submits a candidate answer to a specific question."""
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
        
    session.answers[req.question_id] = CandidateAnswer(
        question_id=req.question_id,
        user_answer=req.user_answer,
        time_taken_seconds=req.time_taken_seconds
    )
    
    return {
        "status": "recorded",
        "question_id": req.question_id,
        "answered_count": len(session.answers),
        "total_questions": len(session.questions)
    }

@app.post("/api/interview/{session_id}/complete")
async def complete_interview(session_id: str):
    """Completes the interview, runs evaluations, records to history, and returns Scorecard."""
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")
        
    evaluator = InterviewEvaluator(
        api_key=llm_manager.get_provider_config("gemini").get("api_key"),
        ollama_model=llm_manager.get_provider_config("ollama").get("model"),
        llm_manager=llm_manager
    )
    scorecard = await evaluator.evaluate_session(session)
    scorecard.focus_area = session.focus_area
    
    # Save to persistent history
    history_manager.add_session(session)
    
    return {
        "status": "completed",
        "session": session.to_dict(),
        "scorecard": scorecard.model_dump()
    }

@app.get("/api/interview/history/all")
async def get_interview_history():
    """Returns all past completed interview rounds."""
    return {"history": history_manager.get_all()}

@app.get("/api/interview/history/{session_id}")
async def get_historical_interview(session_id: str):
    """Returns a specific past interview round."""
    item = history_manager.get_by_id(session_id)
    if not item:
        raise HTTPException(status_code=404, detail="Historical session not found.")
    return item

@app.get("/api/knowledge/areas")
async def get_knowledge_areas():
    """Returns dynamic technology areas and topics discovered from memory."""
    areas = vector_store.get_knowledge_areas()
    return {
        "areas": areas,
        "documents": vector_store.get_documents(),
        "stats": vector_store.get_stats()
    }

@app.post("/api/ingest/reindex-all")
async def reindex_all():
    """Re-scans all uploaded files and workspace markdown notes, clearing and re-indexing the entire knowledge base."""
    vector_store.clear()
    
    reindexed = []
    
    # 1. Re-index uploads directory
    if UPLOADS_DIR.exists():
        for file_path in UPLOADS_DIR.iterdir():
            if file_path.is_file() and not file_path.name.startswith("."):
                try:
                    parsed = parse_file(file_path)
                    chunks = chunk_text(
                        parsed["text"],
                        source_name=file_path.name,
                        metadata={"file_type": parsed["file_type"], "source": "upload"}
                    )
                    doc_id = await vector_store.add_document(
                        title=file_path.name,
                        source=str(file_path.name),
                        file_type=parsed["file_type"],
                        chunks=chunks
                    )
                    reindexed.append({"title": file_path.name, "type": parsed["file_type"], "chunks": len(chunks)})
                except Exception as e:
                    print(f"[Reindex] Error processing upload {file_path.name}: {e}")

    # 2. Re-index workspace markdown files
    if WORKSPACE_DIR.exists():
        for f in sorted(list(WORKSPACE_DIR.glob("*.md"))):
            try:
                parsed = parse_file(f)
                chunks = chunk_text(
                    parsed["text"],
                    source_name=f.name,
                    metadata={"file_type": "markdown", "workspace_file": True}
                )
                doc_id = await vector_store.add_document(
                    title=f.name,
                    source=str(f.name),
                    file_type="markdown",
                    chunks=chunks
                )
                reindexed.append({"title": f.name, "type": "markdown", "chunks": len(chunks)})
            except Exception as e:
                print(f"[Reindex] Error processing workspace {f.name}: {e}")

    return {
        "status": "success",
        "reindexed_count": len(reindexed),
        "stats": vector_store.get_stats(),
        "areas": vector_store.get_knowledge_areas()
    }


# --- Multi-Provider LLM Endpoints (Ollama, LM Studio, Gemini, Claude, OpenRouter) ---
class TestLlmRequest(BaseModel):
    provider: str
    config_override: Optional[Dict[str, Any]] = None

class FetchModelsRequest(BaseModel):
    provider: str
    config_override: Optional[Dict[str, Any]] = None

class SelectLlmRequest(BaseModel):
    provider: str
    model: str

class UpdateLlmConfigRequest(BaseModel):
    active_provider: Optional[str] = None
    active_model: Optional[str] = None
    default_questions: Optional[int] = None
    default_level: Optional[str] = None
    providers: Optional[Dict[str, Any]] = None

@app.get("/api/llm/config")
async def get_llm_config():
    """Returns full multi-provider configuration with masked secrets and active model status."""
    return {
        "config": llm_manager.get_config(),
        "active": llm_manager.get_active_info()
    }

@app.post("/api/llm/config")
async def update_llm_config(req: UpdateLlmConfigRequest):
    """Updates and persists provider settings."""
    updated = llm_manager.update_config(req.model_dump(exclude_unset=True))
    return {
        "status": "success",
        "config": updated,
        "active": llm_manager.get_active_info()
    }

@app.post("/api/llm/test")
async def test_llm_provider(req: TestLlmRequest):
    """Executes a live latency test ping against the selected LLM provider and model."""
    result = await llm_manager.test_connection(req.provider, req.config_override)
    return result

@app.post("/api/llm/models")
async def fetch_llm_models(req: FetchModelsRequest):
    """Queries and returns list of installed/available models for the specified provider."""
    models = await llm_manager.fetch_models(req.provider, req.config_override)
    return {"provider": req.provider, "models": models}

@app.post("/api/llm/select")
async def select_active_llm(req: SelectLlmRequest):
    """Switches the globally active LLM provider and model."""
    llm_manager.update_config({
        "active_provider": req.provider,
        "active_model": req.model
    })
    return {
        "status": "success",
        "active": llm_manager.get_active_info()
    }


# --- Legacy Compatibility Settings Endpoints ---
@app.get("/api/ollama/status")
async def get_ollama_status():
    """Returns availability and installed models from local Ollama service."""
    avail = await ollama_client.is_available()
    models = await ollama_client.get_models() if avail else []
    best = await ollama_client.get_best_model() if avail else None
    active = llm_manager.get_provider_config("ollama").get("model") or best
    return {
        "available": avail,
        "active_model": active,
        "models": models,
        "recommended": best
    }

class SelectOllamaModelRequest(BaseModel):
    model: str

@app.post("/api/ollama/select-model")
async def select_ollama_model(req: SelectOllamaModelRequest):
    llm_manager.update_config({
        "active_provider": "ollama",
        "active_model": req.model,
        "providers": {"ollama": {"model": req.model}}
    })
    return {"status": "success", "active_model": req.model}

@app.get("/api/settings")
async def get_settings():
    ollama_info = await get_ollama_status()
    cfg = llm_manager.get_config()
    return {
        "has_gemini_key": bool(llm_manager.get_provider_config("gemini").get("api_key")),
        "ollama": ollama_info,
        "active_llm": llm_manager.get_active_info(),
        "default_questions": cfg.get("default_questions", 10),
        "default_level": cfg.get("default_level", "intermediate"),
        "llm_config": cfg
    }

@app.post("/api/settings")
async def update_settings(req: SettingsUpdateRequest):
    updates: Dict[str, Any] = {}
    if req.gemini_api_key is not None:
        updates.setdefault("providers", {})["gemini"] = {"api_key": req.gemini_api_key}
        vector_store.set_api_key(req.gemini_api_key)
    if req.default_questions is not None:
        updates["default_questions"] = req.default_questions
    if req.default_level is not None:
        updates["default_level"] = req.default_level

    if updates:
        llm_manager.update_config(updates)
    return {"status": "updated", "settings": await get_settings()}


# --- Static Frontend Serving ---
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
