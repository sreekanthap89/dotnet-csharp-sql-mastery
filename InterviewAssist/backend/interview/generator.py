import json
import re
import random
from typing import List, Dict, Any, Optional
import httpx
from rag.vector_store import VectorStore
from interview.session import Question
from interview.ollama_client import OllamaClient
from interview.llm_manager import LLMManager

class QuestionGenerator:
    def __init__(
        self,
        vector_store: VectorStore,
        api_key: Optional[str] = None,
        ollama_model: Optional[str] = None,
        llm_manager: Optional[LLMManager] = None
    ):
        self.vector_store = vector_store
        self.api_key = api_key
        self.llm_manager = llm_manager
        self.ollama = OllamaClient(default_model=ollama_model or "qwen3-coder:30b")

    def set_ollama_model(self, model: str):
        self.ollama.default_model = model

    async def generate_questions(
        self,
        level: str = "intermediate",
        total_questions: int = 10,
        focus_area: str = "all",
        question_types: Optional[List[str]] = None,
        doc_ids: Optional[List[str]] = None
    ) -> List[Question]:
        # Clean and sanitize requested types
        valid_types = ["mcq", "true_false", "descriptive"]
        raw_types = question_types or valid_types
        types = [t for t in raw_types if t in valid_types]
        if not types:
            types = valid_types

        chunks = self.vector_store.chunks

        # Filter chunks by doc_ids if explicitly specified
        if doc_ids and chunks:
            filtered = [c for c in chunks if c.get("doc_id") in doc_ids]
            if filtered:
                chunks = filtered

        # Filter chunks by focus_area if specified
        if focus_area and focus_area.lower() != "all" and chunks:
            fa = focus_area.lower()
            # 1. Match against discovered knowledge areas first (exact doc_ids mapping)
            areas = self.vector_store.get_knowledge_areas()
            target_area = next((a for a in areas if a["id"].lower() == fa), None)

            if target_area and target_area.get("doc_ids"):
                area_doc_ids = set(target_area["doc_ids"])
                area_chunks = [c for c in chunks if c.get("doc_id") in area_doc_ids]
                if area_chunks:
                    chunks = area_chunks
            elif "doc_" in fa:
                target_doc_id = fa.replace("doc_", "")
                filtered = [c for c in chunks if c.get("doc_id") == target_doc_id]
                if filtered:
                    chunks = filtered
            else:
                # Keywords fallback
                keywords = []
                if "csharp" in fa or "c#" in fa or "oop" in fa:
                    keywords = ["01_", "02_", "03_", "04_", "05_", "06_", "07_", "08_", "09_", "10_", "11_", "12_", "13_", "oops", "generics", "garbage", "threading", "c#", "dotnet"]
                elif "sql" in fa or "database" in fa:
                    keywords = ["14_", "15_", "16_", "17_", "33_", "sql", "join", "index", "stored", "entity", "ef"]
                elif "api" in fa or "asp" in fa or "web" in fa:
                    keywords = ["18_", "19_", "20_", "21_", "22_", "23_", "24_", "web_api", "dependency", "service", "routing", "jwt", "cors"]
                elif "azure" in fa or "cloud" in fa:
                    keywords = ["32_", "33_", "34_", "35_", "36_", "37_", "azure", "functions", "event", "devops", "key_vault"]
                elif "pattern" in fa or "solid" in fa:
                    keywords = ["25_", "26_", "solid", "pattern", "design"]
                elif "algorithm" in fa or "problem" in fa:
                    keywords = ["27_", "28_", "29_", "30_", "31_", "coding", "array", "string", "number"]
                elif "python" in fa:
                    keywords = ["python", "fastapi", "django", "asyncio", "pandas", "numpy", "pytest", "learn_python"]
                elif "java" in fa:
                    keywords = ["java", "spring", "jvm", "hibernate"]
                elif "javascript" in fa or "typescript" in fa:
                    keywords = ["javascript", "typescript", "react", "node"]
                elif "golang" in fa or "go" in fa:
                    keywords = ["golang", "goroutine", "go"]

                if keywords:
                    filtered = [c for c in chunks if any(k in (c.get("doc_title") or "").lower() or k in (c.get("source") or "").lower() or k in (c.get("text") or "").lower() for k in keywords)]
                    if filtered:
                        chunks = filtered

        # Distribute question types strictly among requested types
        type_sequence = []
        for i in range(total_questions):
            type_sequence.append(types[i % len(types)])
        random.shuffle(type_sequence)

        # 1. PRIMARY ENGINE: Active LLM Provider (Ollama, LM Studio, Gemini, Claude, OpenRouter)
        if self.llm_manager:
            active_info = self.llm_manager.get_active_info()
            print(f"[QuestionGenerator] Dispatching to Active LLM: {active_info['icon']} {active_info['provider_name']} ({active_info['model']}) | Focus: {focus_area} | Types: {types}")
            llm_questions = await self._generate_with_llm(level, total_questions, type_sequence, chunks, focus_area=focus_area, allowed_types=types)
            if llm_questions and len(llm_questions) >= total_questions:
                strictly_typed = [q for q in llm_questions if q.type in types]
                if len(strictly_typed) >= total_questions:
                    return strictly_typed[:total_questions]

        # 2. LOCAL OLLAMA FALLBACK
        ollama_available = await self.ollama.is_available()
        if ollama_available:
            active_model = self.ollama.default_model or await self.ollama.get_best_model()
            print(f"[QuestionGenerator] Using Ollama model: {active_model} | Focus: {focus_area} | Types: {types} | Chunks: {len(chunks)}")
            ollama_questions = await self._generate_with_ollama(level, total_questions, type_sequence, chunks, focus_area=focus_area, allowed_types=types)
            if ollama_questions and len(ollama_questions) >= total_questions:
                strictly_typed = [q for q in ollama_questions if q.type in types]
                if len(strictly_typed) >= total_questions:
                    return strictly_typed[:total_questions]

        # 3. TOPIC-ALIGNED CURATED FALLBACK
        print(f"[QuestionGenerator] Using Topic-Aligned Curated Bank for [{focus_area}] with strict types: {types}")
        return self._generate_curated_questions(level, total_questions, type_sequence, chunks, focus_area=focus_area)

    async def _generate_with_llm(
        self,
        level: str,
        total_questions: int,
        type_sequence: List[str],
        chunks: List[Dict[str, Any]],
        focus_area: str = "all",
        allowed_types: Optional[List[str]] = None
    ) -> Optional[List[Question]]:
        """Generates authentic questions using active LLM provider via LLMManager."""
        try:
            allowed = allowed_types or list(set(type_sequence))

            # Sample diverse RAG chunks for rich context
            if chunks:
                sampled = random.sample(chunks, min(len(chunks), 4))
                context_parts = []
                for c in sampled:
                    doc_title = c.get("doc_title") or c.get("source") or "Study Notes"
                    header = c.get("header") or "Topic"
                    clean_chunk_text = c.get("text", "")[:350]
                    context_parts.append(f"### [Source: {doc_title} | Section: {header}]\n{clean_chunk_text}")
                rag_context = "\n\n".join(context_parts)
            else:
                rag_context = f"Focus on core concepts, runtime mechanics, syntax, and architecture of {focus_area.upper()}."

            type_counts = {t: type_sequence.count(t) for t in set(type_sequence)}

            # Build strict prompt based on allowed types
            if allowed == ["true_false"]:
                type_instructions = f"""CRITICAL CONSTRAINT - STRICT QUESTION TYPE:
The user selected EXCLUSIVELY True/False questions.
You MUST generate EXACTLY {total_questions} questions of type "true_false".
DO NOT generate ANY Multiple Choice (MCQ) questions.
DO NOT generate ANY Descriptive questions.
Every single question MUST:
- Have "type": "true_false"
- Have "question" starting with "True or False: "
- Have "options": null
- Have "correct_answer": "True" or "False"
- Have "explanation": detailed technical rationale citing runtime internals."""

                schema_example = f"""[
  {{
    "id": 1,
    "type": "true_false",
    "level": "{level}",
    "topic": "{focus_area.title()} Core Mechanics",
    "question": "True or False: Detailed technical statement exploring an edge case in {focus_area}.",
    "options": null,
    "correct_answer": "False",
    "explanation": "Detailed explanation of why the statement is false according to specification.",
    "source_reference": "{focus_area.title()} Reference"
  }}
]"""

            elif allowed == ["mcq"]:
                type_instructions = f"""CRITICAL CONSTRAINT - STRICT QUESTION TYPE:
The user selected EXCLUSIVELY Multiple Choice questions.
You MUST generate EXACTLY {total_questions} questions of type "mcq".
DO NOT generate ANY True/False questions.
DO NOT generate ANY Descriptive questions.
Every single question MUST:
- Have "type": "mcq"
- Have "options": array of 4 distinct choices starting with "A) ", "B) ", "C) ", "D) "
- Have "correct_answer": matching one of the options (e.g. "A) ...")
- Have "explanation": thorough explanation of why the correct option holds and why distractors fail."""

                schema_example = f"""[
  {{
    "id": 1,
    "type": "mcq",
    "level": "{level}",
    "topic": "{focus_area.title()} Architecture",
    "question": "Technical question testing deep knowledge of {focus_area}?",
    "options": [
      "A) Correct technical option",
      "B) Realistic distractor 1",
      "C) Realistic distractor 2",
      "D) Realistic distractor 3"
    ],
    "correct_answer": "A) Correct technical option",
    "explanation": "Detailed explanation of runtime behavior.",
    "source_reference": "{focus_area.title()} Architecture"
  }}
]"""

            elif allowed == ["descriptive"]:
                type_instructions = f"""CRITICAL CONSTRAINT - STRICT QUESTION TYPE:
The user selected EXCLUSIVELY Descriptive / Architectural Scenario questions.
You MUST generate EXACTLY {total_questions} questions of type "descriptive".
DO NOT generate ANY Multiple Choice or True/False questions.
Every single question MUST:
- Have "type": "descriptive"
- Have "options": null
- Have "key_points": list of 3-4 specific evaluation requirements / architectural criteria
- Have "explanation": comprehensive architectural model answer and trade-off comparison."""

                schema_example = f"""[
  {{
    "id": 1,
    "type": "descriptive",
    "level": "{level}",
    "topic": "{focus_area.title()} System Design",
    "question": "Architectural Scenario: In-depth scenario question for {focus_area}.",
    "options": null,
    "key_points": [
      "Requirement 1",
      "Requirement 2",
      "Requirement 3"
    ],
    "explanation": "Detailed architectural answer.",
    "source_reference": "{focus_area.title()} Documentation"
  }}
]"""

            else:
                # Mixed types
                mix_parts = []
                if type_counts.get("mcq"):
                    mix_parts.append(f"- {type_counts['mcq']} Multiple Choice Questions (type: 'mcq') with 4 options (A, B, C, D)")
                if type_counts.get("true_false"):
                    mix_parts.append(f"- {type_counts['true_false']} True/False Questions (type: 'true_false') starting with 'True or False: '")
                if type_counts.get("descriptive"):
                    mix_parts.append(f"- {type_counts['descriptive']} Descriptive Architectural Scenario Questions (type: 'descriptive') with key_points")

                type_instructions = f"""CRITICAL CONSTRAINT - QUESTION MIX:
You must generate EXACTLY {total_questions} questions strictly following this distribution:
{chr(10).join(mix_parts)}
DO NOT generate any types not listed above."""

                schema_example = f"""[
  {{
    "id": 1,
    "type": "mcq",
    "level": "{level}",
    "topic": "{focus_area.title()} Concept",
    "question": "Multiple choice question testing {focus_area}?",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_answer": "A) ...",
    "explanation": "Detailed reasoning.",
    "source_reference": "{focus_area.title()} Documentation"
  }},
  {{
    "id": 2,
    "type": "true_false",
    "level": "{level}",
    "topic": "{focus_area.title()} Internals",
    "question": "True or False: Technical statement about {focus_area}.",
    "options": null,
    "correct_answer": "True",
    "explanation": "Runtime mechanics explanation.",
    "source_reference": "{focus_area.title()} Documentation"
  }}
]"""

            domain_guardrail = ""
            if focus_area.lower() != "all":
                domain_guardrail = f"""STRICT DOMAIN ENFORCEMENT:
Every question MUST be 100% focused on {focus_area.upper()}.
DO NOT ask questions about unrelated technologies or languages.
All questions, code snippets, options, and explanations must exclusively test {focus_area.upper()}."""

            prompt = f"""You are a Principal Software Architect and elite Technical Interviewer conducting a rigorous interview for a {level.upper()} candidate.

TARGET DOMAIN / FOCUS AREA: {focus_area.upper()}
{domain_guardrail}

RAG STUDY CONTEXT FROM KNOWLEDGE BASE:
{rag_context}

{type_instructions}

SCHEMA INSTRUCTIONS:
Return a JSON array containing EXACTLY {total_questions} objects matching this structure:
{schema_example}

Output ONLY the JSON array."""

            res = await self.llm_manager.generate_json(
                prompt=prompt,
                system_prompt="You are a Principal Software Architect. Output strictly valid JSON arrays.",
                timeout=50.0
            )

            if isinstance(res, list) and len(res) > 0:
                questions = []
                for i, item in enumerate(res, start=1):
                    if isinstance(item, dict):
                        item["id"] = i
                        item["level"] = level
                        if "type" not in item or item["type"] not in allowed:
                            item["type"] = type_sequence[(i - 1) % len(type_sequence)]
                        if not item.get("topic"):
                            item["topic"] = f"{focus_area.title()} Engineering"
                        if not item.get("source_reference"):
                            item["source_reference"] = f"{focus_area.title()} Knowledge Base"

                        # Ensure correct format for True/False
                        if item["type"] == "true_false":
                            item["options"] = None
                            if not item.get("question", "").lower().startswith("true or false:"):
                                item["question"] = f"True or False: {item.get('question', '')}"
                            ans = str(item.get("correct_answer", "")).lower()
                            item["correct_answer"] = "True" if "true" in ans else "False"

                        # Ensure MCQ has 4 options
                        elif item["type"] == "mcq":
                            if not item.get("options") or len(item["options"]) < 2:
                                item["options"] = [
                                    f"A) {item.get('correct_answer', 'Valid option')}",
                                    "B) Incorrect alternative",
                                    "C) Partial implementation",
                                    "D) Deprecated API"
                                ]

                        # Ensure descriptive has key points
                        elif item["type"] == "descriptive":
                            item["options"] = None
                            if not item.get("key_points"):
                                item["key_points"] = ["Core architectural approach", "Performance & trade-offs", "Edge case handling"]

                        questions.append(Question(**item))

                return questions
            return None
        except Exception as e:
            print(f"[QuestionGenerator] LLM Manager generation error: {e}")
            return None
        """Generates authentic questions using local Ollama model with RAG context and strict type & domain enforcement."""
        try:
            allowed = allowed_types or list(set(type_sequence))

            # Sample diverse RAG chunks for rich context
            if chunks:
                sampled = random.sample(chunks, min(len(chunks), 4))
                context_parts = []
                for c in sampled:
                    doc_title = c.get("doc_title") or c.get("source") or "Study Notes"
                    header = c.get("header") or "Topic"
                    clean_chunk_text = c.get("text", "")[:350]
                    context_parts.append(f"### [Source: {doc_title} | Section: {header}]\n{clean_chunk_text}")
                rag_context = "\n\n".join(context_parts)
            else:
                rag_context = f"Focus on core concepts, runtime mechanics, syntax, and architecture of {focus_area.upper()}."

            type_counts = {t: type_sequence.count(t) for t in set(type_sequence)}

            # Build strict prompt based on allowed types
            if allowed == ["true_false"]:
                type_instructions = f"""CRITICAL CONSTRAINT - STRICT QUESTION TYPE:
The user selected EXCLUSIVELY True/False questions.
You MUST generate EXACTLY {total_questions} questions of type "true_false".
DO NOT generate ANY Multiple Choice (MCQ) questions.
DO NOT generate ANY Descriptive questions.
Every single question MUST:
- Have "type": "true_false"
- Have "question" starting with "True or False: "
- Have "options": null
- Have "correct_answer": "True" or "False"
- Have "explanation": detailed technical rationale citing runtime internals."""

                schema_example = f"""[
  {{
    "id": 1,
    "type": "true_false",
    "level": "{level}",
    "topic": "{focus_area.title()} Core Mechanics",
    "question": "True or False: Detailed technical statement exploring an edge case in {focus_area}.",
    "options": null,
    "correct_answer": "False",
    "explanation": "Detailed explanation of why the statement is false according to specification.",
    "source_reference": "{focus_area.title()} Reference"
  }}
]"""

            elif allowed == ["mcq"]:
                type_instructions = f"""CRITICAL CONSTRAINT - STRICT QUESTION TYPE:
The user selected EXCLUSIVELY Multiple Choice questions.
You MUST generate EXACTLY {total_questions} questions of type "mcq".
DO NOT generate ANY True/False questions.
DO NOT generate ANY Descriptive questions.
Every single question MUST:
- Have "type": "mcq"
- Have "options": array of 4 distinct choices starting with "A) ", "B) ", "C) ", "D) "
- Have "correct_answer": matching one of the options (e.g. "A) ...")
- Have "explanation": thorough explanation of why the correct option holds and why distractors fail."""

                schema_example = f"""[
  {{
    "id": 1,
    "type": "mcq",
    "level": "{level}",
    "topic": "{focus_area.title()} Architecture",
    "question": "Technical question testing deep knowledge of {focus_area}?",
    "options": [
      "A) Correct technical option",
      "B) Realistic distractor 1",
      "C) Realistic distractor 2",
      "D) Realistic distractor 3"
    ],
    "correct_answer": "A) Correct technical option",
    "explanation": "Detailed explanation of runtime behavior.",
    "source_reference": "{focus_area.title()} Architecture"
  }}
]"""

            elif allowed == ["descriptive"]:
                type_instructions = f"""CRITICAL CONSTRAINT - STRICT QUESTION TYPE:
The user selected EXCLUSIVELY Descriptive / Architectural Scenario questions.
You MUST generate EXACTLY {total_questions} questions of type "descriptive".
DO NOT generate ANY Multiple Choice or True/False questions.
Every single question MUST:
- Have "type": "descriptive"
- Have "options": null
- Have "key_points": list of 3-4 specific evaluation requirements / architectural criteria
- Have "explanation": comprehensive architectural model answer and trade-off comparison."""

                schema_example = f"""[
  {{
    "id": 1,
    "type": "descriptive",
    "level": "{level}",
    "topic": "{focus_area.title()} System Design",
    "question": "Architectural Scenario: In-depth scenario question for {focus_area}.",
    "options": null,
    "key_points": [
      "Requirement 1",
      "Requirement 2",
      "Requirement 3"
    ],
    "explanation": "Detailed architectural answer.",
    "source_reference": "{focus_area.title()} Documentation"
  }}
]"""

            else:
                # Mixed types
                mix_parts = []
                if type_counts.get("mcq"):
                    mix_parts.append(f"- {type_counts['mcq']} Multiple Choice Questions (type: 'mcq') with 4 options (A, B, C, D)")
                if type_counts.get("true_false"):
                    mix_parts.append(f"- {type_counts['true_false']} True/False Questions (type: 'true_false') starting with 'True or False: '")
                if type_counts.get("descriptive"):
                    mix_parts.append(f"- {type_counts['descriptive']} Descriptive Architectural Scenario Questions (type: 'descriptive') with key_points")

                type_instructions = f"""CRITICAL CONSTRAINT - QUESTION MIX:
You must generate EXACTLY {total_questions} questions strictly following this distribution:
{chr(10).join(mix_parts)}
DO NOT generate any types not listed above."""

                schema_example = f"""[
  {{
    "id": 1,
    "type": "mcq",
    "level": "{level}",
    "topic": "Topic Name",
    "question": "Technical MCQ question",
    "options": ["A) Choice 1", "B) Choice 2", "C) Choice 3", "D) Choice 4"],
    "correct_answer": "A) Choice 1",
    "explanation": "Technical rationale",
    "source_reference": "Reference"
  }},
  {{
    "id": 2,
    "type": "true_false",
    "level": "{level}",
    "topic": "Topic Name",
    "question": "True or False: Technical statement testing edge case.",
    "options": null,
    "correct_answer": "False",
    "explanation": "Technical rationale",
    "source_reference": "Reference"
  }}
]"""

            domain_restriction = ""
            if focus_area and focus_area.lower() != "all":
                domain_restriction = f"""
STRICT DOMAIN RESTRICTION - 100% EXCLUSIVE TO: {focus_area.upper()}
The candidate specifically chose to be interviewed on: {focus_area.upper()}
- Every single question MUST test concepts, syntax, libraries, internals, and best practices of {focus_area.upper()}.
- You MUST NOT ask questions about unrelated languages or technologies (e.g. if the domain is Python, DO NOT ask about C#, ASP.NET, or SQL Server unless specifically asked).
- Use syntax, idioms, keywords, and runtime conventions strictly for {focus_area.upper()}.
"""

            prompt = f"""You are a Principal Software Architect and elite Technical Interviewer conducting a realistic, in-depth technical interview at the '{level.upper()}' proficiency level.

TARGET PROFICIENCY LEVEL: {level.upper()}

{domain_restriction}

{type_instructions}

REFERENCE STUDY CONTEXT:
{rag_context}

Return a valid JSON array of objects following the exact schema:
{schema_example}

CRITICAL: Output strictly the JSON array. No conversational text or markdown code blocks."""

            data = await self.ollama.generate_json(prompt, timeout=120.0)
            if isinstance(data, list) and len(data) > 0:
                questions: List[Question] = []
                for idx, item in enumerate(data, 1):
                    q_type = str(item.get("type", "")).lower()

                    # Enforce allowed types
                    if q_type not in allowed:
                        target_type = type_sequence[(idx - 1) % len(type_sequence)]
                        if target_type == "true_false":
                            q_text = str(item.get("question", ""))
                            if not q_text.lower().startswith("true or false"):
                                q_text = f"True or False: {q_text}"
                            item["question"] = q_text
                            item["options"] = None
                            ans = str(item.get("correct_answer", "True")).strip()
                            item["correct_answer"] = "True" if "true" in ans.lower() or ans.startswith("A") else "False"
                            item["type"] = "true_false"
                        elif target_type == "mcq":
                            if not item.get("options") or len(item.get("options", [])) < 4:
                                continue
                            item["type"] = "mcq"
                        elif target_type == "descriptive":
                            item["options"] = None
                            item["type"] = "descriptive"
                            if not item.get("key_points"):
                                item["key_points"] = ["Core architectural flow", "Failure mitigation & resilience", "Production trade-offs"]

                    if item.get("type") in allowed:
                        item["id"] = len(questions) + 1
                        item["level"] = level
                        try:
                            questions.append(Question(**item))
                        except Exception as e:
                            print(f"[QuestionGenerator] Question validation error: {e}")

                if len(questions) >= total_questions:
                    return questions[:total_questions]

                # Top up remainder with topic-aligned curated bank
                needed = total_questions - len(questions)
                needed_types = type_sequence[len(questions):total_questions]
                fill_questions = self._generate_curated_questions(level, needed, needed_types, chunks, focus_area=focus_area)
                for q in fill_questions:
                    q.id = len(questions) + 1
                    questions.append(q)
                return questions[:total_questions]

        except Exception as e:
            print(f"[QuestionGenerator] Ollama generation exception: {e}")
            return None

    async def _generate_with_gemini(
        self,
        level: str,
        total_questions: int,
        type_sequence: List[str],
        chunks: List[Dict[str, Any]],
        allowed_types: Optional[List[str]] = None,
        focus_area: str = "all"
    ) -> Optional[List[Question]]:
        try:
            allowed = allowed_types or list(set(type_sequence))
            sampled = random.sample(chunks, min(len(chunks), 6)) if chunks else []
            rag_context = "\n\n".join(f"[{c.get('doc_title', 'Doc')}]: {c.get('text', '')[:600]}" for c in sampled)
            
            prompt = f"""Generate {total_questions} elite technical interview questions for {level.upper()} level.
FOCUS DOMAIN: {focus_area.upper()} - All questions must be strictly about {focus_area}.
Permitted types ONLY: {allowed}
Required types sequence: {type_sequence}
Context:
{rag_context}

Output strictly a JSON array of question objects."""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
                if resp.status_code == 200:
                    data = resp.json()
                    raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw = re.sub(r"^```json\s*", "", raw)
                    raw = re.sub(r"^```\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                    parsed = json.loads(raw)
                    return [Question(**{**q, "id": i}) for i, q in enumerate(parsed, 1) if q.get("type") in allowed]
        except Exception as e:
            print(f"Gemini fallback error: {e}")
            return None

    def _generate_curated_questions(
        self,
        level: str,
        total_questions: int,
        type_sequence: List[str],
        chunks: List[Dict[str, Any]],
        focus_area: str = "all"
    ) -> List[Question]:
        """
        Topic-aligned curated bank of high-caliber real interview questions.
        Dynamically filters by focus_area (Python, C#, SQL, Azure, etc.) and requested question types.
        """
        fa = (focus_area or "all").lower()

        # ==========================================
        # PYTHON CURATED BANK
        # ==========================================
        python_mcqs = [
            {
                "type": "mcq",
                "topic": "Python / Asyncio Event Loop",
                "question": "In Python asyncio, what happens if a CPU-bound synchronous calculation (e.g. heavy cryptography or matrix math) is called directly inside an `async def` function?",
                "options": [
                    "A) It blocks the single-threaded event loop, preventing all other concurrent coroutines and I/O tasks from executing until it finishes.",
                    "B) Python automatically allocates an OS thread from the GIL thread pool to run the calculation concurrently.",
                    "C) An AsyncExecutionError is raised at runtime.",
                    "D) The operating system preempts the Python process and schedules a worker thread."
                ],
                "correct_answer": "A) It blocks the single-threaded event loop, preventing all other concurrent coroutines and I/O tasks from executing until it finishes.",
                "explanation": "Python's asyncio runs on a cooperative single-threaded event loop. Any blocking synchronous computation freezes the entire thread. CPU-bound work must be offloaded with `asyncio.to_thread` or `ProcessPoolExecutor`.",
                "source_reference": "Python Async Architecture"
            },
            {
                "type": "mcq",
                "topic": "Python Memory & Mutable Default Arguments",
                "question": "In Python, what is the output when executing `def add_item(val, items=[]): items.append(val); return items` called twice as `add_item(1)` followed by `add_item(2)`?",
                "options": [
                    "A) [1, 2] because default argument expressions are evaluated once at function definition time, sharing the same list instance across invocations.",
                    "B) [2] because items is freshly initialized to a new empty list on each function call.",
                    "C) [1] and [2] as separate lists stored in thread-local storage.",
                    "D) TypeError: Mutable default arguments are prohibited in modern Python."
                ],
                "correct_answer": "A) [1, 2] because default argument expressions are evaluated once at function definition time, sharing the same list instance across invocations.",
                "explanation": "Python default argument expressions are evaluated once when the `def` statement executes. The created list object is stored on the function object's `__defaults__` tuple, persisting mutations across subsequent calls.",
                "source_reference": "Python Functions & Scoping"
            },
            {
                "type": "mcq",
                "topic": "Python Decorators & `functools.wraps`",
                "question": "Why is `@functools.wraps(func)` considered a mandatory best practice when writing custom Python decorators?",
                "options": [
                    "A) It preserves the decorated function's original metadata (__name__, __doc__, __annotations__) instead of being replaced by the wrapper's metadata.",
                    "B) It automatically compiles the decorator into C-extension bytecode for 10x faster execution.",
                    "C) It acquires the Global Interpreter Lock (GIL) to make the decorator thread-safe.",
                    "D) It ensures the wrapper function can only be invoked once per application lifecycle."
                ],
                "correct_answer": "A) It preserves the decorated function's original metadata (__name__, __doc__, __annotations__) instead of being replaced by the wrapper's metadata.",
                "explanation": "Without `functools.wraps`, introspecting the decorated function displays the wrapper's name (e.g. 'wrapper') and empty docstrings, breaking debuggers, logging, and FastAPI/Pydantic reflection.",
                "source_reference": "Python Advanced Functions"
            }
        ]

        python_true_falses = [
            {
                "type": "true_false",
                "topic": "Python GIL & Multithreading",
                "question": "True or False: In standard CPython, using the `threading` module allows multiple threads to execute Python bytecode simultaneously across multiple CPU cores in true parallelism.",
                "options": None,
                "correct_answer": "False",
                "explanation": "False. CPython's Global Interpreter Lock (GIL) ensures only one native thread executes Python bytecode at any instant. CPU parallelism in Python requires the `multiprocessing` module, C-extensions that release the GIL, or Python 3.13 free-threaded builds.",
                "source_reference": "Python Concurrency & GIL"
            },
            {
                "type": "true_false",
                "topic": "Python Identity vs Equality (`is` vs `==`)",
                "question": "True or False: In Python, the expression `a is b` evaluates to True whenever `a == b` is True for all objects.",
                "options": None,
                "correct_answer": "False",
                "explanation": "False. `==` checks value equality (via `__eq__`), while `is` checks object identity (whether `id(a) == id(b)` in memory). Two distinct lists `[1, 2] == [1, 2]` are equal in value, but `[1, 2] is [1, 2]` is False.",
                "source_reference": "Python Data Model"
            },
            {
                "type": "true_false",
                "topic": "Python Generators & Memory Footprint",
                "question": "True or False: A generator expression `(x * 2 for x in range(10_000_000))` consumes significantly less memory than a list comprehension `[x * 2 for x in range(10_000_000)]` because items are lazily produced on demand.",
                "options": None,
                "correct_answer": "True",
                "explanation": "True. The list comprehension immediately allocates memory on the heap for 10 million integers, whereas the generator expression creates a lightweight generator object with fixed memory footprint (~100 bytes) yielding one item at a time.",
                "source_reference": "Python Iterators & Generators"
            },
            {
                "type": "true_false",
                "topic": "Python Variable Scoping & LEGB Rule",
                "question": "True or False: In Python, modifying a variable defined in an outer enclosing function from within an inner nested function requires the `global` keyword.",
                "options": None,
                "correct_answer": "False",
                "explanation": "False. It requires the `nonlocal` keyword. The `global` keyword binds to the module's global scope, whereas `nonlocal` binds to the nearest enclosing lexical scope.",
                "source_reference": "Python Scoping Rules"
            },
            {
                "type": "true_false",
                "topic": "Python Dict Implementation & Insertion Order",
                "question": "True or False: Since Python 3.7, standard Python dictionaries are guaranteed by the language specification to maintain key insertion order.",
                "options": None,
                "correct_answer": "True",
                "explanation": "True. While dictionaries in Python 3.6 preserved insertion order as a CPython implementation detail, Python 3.7+ made insertion order preservation an official part of the Python language specification.",
                "source_reference": "Python Dictionaries"
            }
        ]

        python_descriptives = [
            {
                "type": "descriptive",
                "topic": "Python Async Architecture & High Concurrency",
                "question": "Architectural Scenario: You are designing a high-throughput webhook ingestion service in Python (FastAPI/Uvicorn) that receives 10,000 JSON payloads/second, validates schemas, and writes to a database. Explain how you would structure the async pipeline, prevent GIL bottlenecks, and manage database connection pooling.",
                "options": None,
                "key_points": [
                    "Non-blocking async I/O handlers with asyncpg/tortoise-orm and connection pooling",
                    "Gunicorn with multiple Uvicorn worker processes (1 per CPU core) to bypass the GIL",
                    "Offloading heavy schema validation or cryptographic hashing to ProcessPoolExecutor or background tasks (Celery/RabbitMQ)",
                    "Graceful backpressure and rate limiting (Redis token bucket)"
                ],
                "explanation": "High-throughput Python services use multiple Uvicorn worker processes across CPU cores to overcome the GIL, combined with async I/O database drivers and connection pools to maximize concurrency.",
                "source_reference": "Python High-Performance Architecture"
            }
        ]

        # ==========================================
        # C# & .NET CURATED BANK
        # ==========================================
        csharp_mcqs = [
            {
                "type": "mcq",
                "topic": "Garbage Collection & Memory Architecture",
                "question": "In the .NET Garbage Collector, what is the key behavioral difference between Generation 0, Generation 1, and Generation 2 collections?",
                "options": [
                    "A) Gen 0 collections are the most frequent and reclaim short-lived objects; surviving objects are promoted to Gen 1, then Gen 2, which also includes the Large Object Heap (LOH).",
                    "B) Gen 2 collections run on every function return, whereas Gen 0 only collects static singletons.",
                    "C) Generation 0 collects unmanaged memory, while Generation 2 collects managed stack frames.",
                    "D) All three generations run concurrently with identical pause times and identical heap sweeps."
                ],
                "correct_answer": "A) Gen 0 collections are the most frequent and reclaim short-lived objects; surviving objects are promoted to Gen 1, then Gen 2, which also includes the Large Object Heap (LOH).",
                "explanation": "In .NET generational GC, Gen 0 holds short-lived temporary objects (local variables). Surviving objects promote to Gen 1, and long-lived objects promote to Gen 2 (which also manages the LOH for objects >= 85,000 bytes). Gen 2 collections (Full GC) are the most expensive.",
                "source_reference": "120_dotnet_garbage_collection.md"
            },
            {
                "type": "mcq",
                "topic": "Dependency Injection Service Lifetimes",
                "question": "In ASP.NET Core, what critical issue occurs if a `Singleton` service directly injects a `Scoped` service (such as an Entity Framework `DbContext`) in its constructor?",
                "options": [
                    "A) Captive Dependency: The Scoped service is captured for the lifetime of the application, causing concurrency conflicts and memory leaks because DbContext is not thread-safe.",
                    "B) The compiler throws a CS0103 compile-time syntax error preventing compilation.",
                    "C) The runtime automatically converts the Singleton service into a Transient service per HTTP request.",
                    "D) The database connection string is cleared on every garbage collection cycle."
                ],
                "correct_answer": "A) Captive Dependency: The Scoped service is captured for the lifetime of the application, causing concurrency conflicts and memory leaks because DbContext is not thread-safe.",
                "explanation": "This is known as a Captive Dependency. Because the Singleton never dies, the Scoped DbContext is held open indefinitely across all concurrent HTTP requests. Since DbContext is not thread-safe, concurrent requests trigger InvalidOperationException.",
                "source_reference": "230_dotnet_core_service_lifetimes_middleware_hosting.md"
            }
        ]

        csharp_true_falses = [
            {
                "type": "true_false",
                "topic": "Value Types vs Reference Types",
                "question": "True or False: In C#, declaring a variable as a `struct` (Value Type) guarantees that it will always be allocated on the call stack under all runtime conditions.",
                "options": None,
                "correct_answer": "False",
                "explanation": "False. If a `struct` is declared as a field inside a `class` (Reference Type), or if it is boxed into an `object`/`interface`, or captured inside a closure, it is allocated on the managed Heap, not the stack.",
                "source_reference": "010_introduction_oops_and_basics.md"
            },
            {
                "type": "true_false",
                "topic": "Entity Framework Core Performance",
                "question": "True or False: In EF Core, executing read-only queries with `.AsNoTracking()` significantly improves performance and reduces memory consumption because the Change Tracker bypasses object tracking and snapshot creation.",
                "options": None,
                "correct_answer": "True",
                "explanation": "True. .AsNoTracking() tells EF Core not to track entities in the DbContext ChangeTracker, saving significant memory allocation and CPU cycles during entity materialization.",
                "source_reference": "170_ado_dotnet_and_entity_framework.md"
            },
            {
                "type": "true_false",
                "topic": "C# Concurrency & Async/Await",
                "question": "True or False: In modern .NET Core / .NET 8, calling `.ConfigureAwait(false)` inside ASP.NET Core controllers is strictly necessary to prevent synchronization context deadlocks.",
                "options": None,
                "correct_answer": "False",
                "explanation": "False. ASP.NET Core does NOT have a custom SynchronizationContext (unlike legacy ASP.NET Framework or WPF/WinForms). In ASP.NET Core web requests, continuations naturally run on any available ThreadPool thread.",
                "source_reference": "130_dotnet_threading_and_concurrency.md"
            }
        ]

        csharp_descriptives = [
            {
                "type": "descriptive",
                "topic": "Asynchronous Concurrency & Thread Pool Starvation",
                "question": "Explain how `async` and `await` prevent thread pool starvation in high-throughput ASP.NET Core web services. Contrast `Task.Run` vs I/O-bound completion ports and explain why `.Result` or `.Wait()` can cause production deadlocks.",
                "options": None,
                "key_points": [
                    "Async I/O releases the thread to the ThreadPool during network/disk wait (I/O completion ports)",
                    "Task.Run offloads CPU-bound work to a thread pool thread, providing no scalability benefit for pure I/O",
                    "Calling .Result or .Wait() synchronously blocks the calling thread, risking thread pool starvation and synchronization context deadlocks"
                ],
                "explanation": "True asynchronous I/O uses OS-level I/O Completion Ports (IOCP) without consuming any OS thread while waiting for the response. Blocking via .Result holds the thread, preventing it from serving other concurrent HTTP requests.",
                "source_reference": "130_dotnet_threading_and_concurrency.md"
            }
        ]

        # Select the appropriate bank according to focus_area
        if "python" in fa:
            active_mcqs = python_mcqs
            active_tfs = python_true_falses
            active_descs = python_descriptives
        elif "csharp" in fa or "c#" in fa or "oop" in fa:
            active_mcqs = csharp_mcqs
            active_tfs = csharp_true_falses
            active_descs = csharp_descriptives
        else:
            active_mcqs = csharp_mcqs + python_mcqs
            active_tfs = csharp_true_falses + python_true_falses
            active_descs = csharp_descriptives + python_descriptives

        questions = []
        mcq_idx = 0
        tf_idx = 0
        desc_idx = 0

        for i, target_type in enumerate(type_sequence, 1):
            if target_type == "true_false":
                item = dict(active_tfs[tf_idx % len(active_tfs)])
                tf_idx += 1
            elif target_type == "descriptive":
                item = dict(active_descs[desc_idx % len(active_descs)])
                desc_idx += 1
            else:
                item = dict(active_mcqs[mcq_idx % len(active_mcqs)])
                mcq_idx += 1

            item["id"] = i
            item["level"] = level
            questions.append(Question(**item))

        return questions
