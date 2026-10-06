from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
import json
import datetime
from config import STORAGE_DIR

class Question(BaseModel):
    id: int
    type: str  # "mcq", "true_false", "descriptive"
    level: str # "beginner", "intermediate", "senior", "architect"
    topic: str
    question: str
    options: Optional[List[str]] = None      # For MCQ (4 options)
    correct_answer: Optional[str] = None     # For MCQ / True_False
    explanation: Optional[str] = None        # Explanation / rationale
    key_points: Optional[List[str]] = None   # For descriptive questions
    source_reference: Optional[str] = None   # Grounded RAG document / header

class CandidateAnswer(BaseModel):
    question_id: int
    user_answer: str
    time_taken_seconds: Optional[int] = 0

class QuestionEvaluation(BaseModel):
    question_id: int
    question: str
    type: str
    level: str
    topic: str
    user_answer: str
    correct_answer: Optional[str] = None
    is_correct: bool
    score: float                             # 0.0 to 10.0
    feedback: str
    what_to_learn: Optional[str] = None      # Explicit guidance on what to learn
    how_to_learn: Optional[str] = None       # Actionable technique on how to learn
    strengths: Optional[str] = None
    improvements: Optional[str] = None
    source_reference: Optional[str] = None

class Scorecard(BaseModel):
    session_id: str
    overall_score: float                     # 0 to 100
    level: str
    focus_area: Optional[str] = "All Topics"
    verdict: str
    summary: str
    total_questions: int
    correct_count: int
    partial_count: int
    incorrect_count: int
    topic_breakdown: Dict[str, Dict[str, Any]]
    type_breakdown: Dict[str, Dict[str, Any]]
    evaluations: List[QuestionEvaluation]
    actionable_roadmap: List[Dict[str, str]] # What to do, How to do, How to improve

class InterviewSession:
    def __init__(
        self,
        level: str = "intermediate",
        total_questions: int = 10,
        focus_area: str = "all",
        selected_topics: Optional[List[str]] = None,
        question_types: Optional[List[str]] = None
    ):
        self.session_id = str(uuid.uuid4())[:8]
        self.created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.level = level.lower()
        self.total_questions = total_questions
        self.focus_area = focus_area
        self.selected_topics = selected_topics or []
        self.question_types = question_types or ["mcq", "true_false", "descriptive"]
        self.questions: List[Question] = []
        self.answers: Dict[int, CandidateAnswer] = {}
        self.status = "created"  # created, in_progress, completed
        self.current_question_index = 0
        self.scorecard: Optional[Scorecard] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "level": self.level,
            "focus_area": self.focus_area,
            "total_questions": self.total_questions,
            "status": self.status,
            "current_index": self.current_question_index,
            "answered_count": len(self.answers),
            "questions": [q.model_dump() for q in self.questions],
            "scorecard": self.scorecard.model_dump() if self.scorecard else None
        }

class InterviewHistoryManager:
    """Persists completed interview rounds to disk for historical review and tracking."""
    def __init__(self):
        self.file_path = STORAGE_DIR / "interview_history.json"
        self.history: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load interview history: {e}")
                self.history = []

    def _save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save interview history: {e}")

    def add_session(self, session: InterviewSession):
        if not session.scorecard:
            return
            
        record = {
            "session_id": session.session_id,
            "date": session.created_at,
            "level": session.level,
            "focus_area": session.focus_area,
            "overall_score": session.scorecard.overall_score,
            "verdict": session.scorecard.verdict,
            "total_questions": session.total_questions,
            "correct_count": session.scorecard.correct_count,
            "scorecard": session.scorecard.model_dump()
        }
        # Prepend to list (newest first)
        self.history.insert(0, record)
        self._save()

    def get_all(self) -> List[Dict[str, Any]]:
        return self.history

    def get_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        for item in self.history:
            if item["session_id"] == session_id:
                return item
        return None
