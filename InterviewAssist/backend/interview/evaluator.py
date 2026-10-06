import re
import json
from typing import List, Dict, Any, Optional
import httpx
from interview.session import InterviewSession, QuestionEvaluation, Scorecard
from interview.ollama_client import OllamaClient
from interview.llm_manager import LLMManager

class InterviewEvaluator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        ollama_model: Optional[str] = None,
        llm_manager: Optional[LLMManager] = None
    ):
        self.api_key = api_key
        self.llm_manager = llm_manager
        self.ollama = OllamaClient(default_model=ollama_model or "qwen3-coder:30b")

    def set_ollama_model(self, model: str):
        self.ollama.default_model = model

    async def evaluate_session(self, session: InterviewSession) -> Scorecard:
        evaluations: List[QuestionEvaluation] = []
        
        total_points = 0.0
        max_possible_points = len(session.questions) * 10.0
        correct_count = 0
        partial_count = 0
        incorrect_count = 0

        topic_stats: Dict[str, Dict[str, Any]] = {}
        type_stats: Dict[str, Dict[str, Any]] = {
            "mcq": {"total": 0, "correct": 0, "points": 0.0},
            "true_false": {"total": 0, "correct": 0, "points": 0.0},
            "descriptive": {"total": 0, "correct": 0, "points": 0.0}
        }

        for q in session.questions:
            cand_ans = session.answers.get(q.id)
            user_text = cand_ans.user_answer.strip() if cand_ans else ""
            
            if q.topic not in topic_stats:
                topic_stats[q.topic] = {"total": 0, "earned": 0.0, "max": 0.0}
            topic_stats[q.topic]["total"] += 1
            topic_stats[q.topic]["max"] += 10.0

            q_eval = await self._evaluate_question(q, user_text)
            evaluations.append(q_eval)

            total_points += q_eval.score
            topic_stats[q.topic]["earned"] += q_eval.score

            type_stats[q.type]["total"] += 1
            type_stats[q.type]["points"] += q_eval.score

            if q_eval.score >= 8.5:
                correct_count += 1
                type_stats[q.type]["correct"] += 1
            elif q_eval.score >= 4.0:
                partial_count += 1
            else:
                incorrect_count += 1

        overall_score = round((total_points / max(max_possible_points, 1.0)) * 100.0, 1)

        verdict = self._compute_verdict(overall_score, session.level)
        summary = self._compute_summary(overall_score, session.level, correct_count, len(session.questions))
        roadmap = self._generate_improvement_roadmap(evaluations, session.level, overall_score)

        scorecard = Scorecard(
            session_id=session.session_id,
            overall_score=overall_score,
            level=session.level,
            verdict=verdict,
            summary=summary,
            total_questions=len(session.questions),
            correct_count=correct_count,
            partial_count=partial_count,
            incorrect_count=incorrect_count,
            topic_breakdown=topic_stats,
            type_breakdown=type_stats,
            evaluations=evaluations,
            actionable_roadmap=roadmap
        )
        session.scorecard = scorecard
        session.status = "completed"
        return scorecard

    async def _evaluate_question(self, q, user_text: str) -> QuestionEvaluation:
        if q.type == "mcq":
            return self._evaluate_mcq(q, user_text)
        elif q.type == "true_false":
            return self._evaluate_tf(q, user_text)
        else:
            return await self._evaluate_descriptive(q, user_text)

    def _evaluate_mcq(self, q, user_text: str) -> QuestionEvaluation:
        if not user_text:
            return QuestionEvaluation(
                question_id=q.id,
                question=q.question,
                type=q.type,
                level=q.level,
                topic=q.topic,
                user_answer="[No answer provided]",
                correct_answer=q.correct_answer,
                is_correct=False,
                score=0.0,
                feedback="No answer was selected for this multiple-choice question.",
                what_to_learn=f"Core concepts of {q.topic}",
                how_to_learn=f"Review official documentation for {q.topic} and understand common pitfalls.",
                source_reference=q.source_reference
            )

        # Normalize both strings
        norm_user = re.sub(r"^[A-D]\)\s*", "", user_text.strip(), flags=re.IGNORECASE).lower()
        norm_correct = re.sub(r"^[A-D]\)\s*", "", (q.correct_answer or "").strip(), flags=re.IGNORECASE).lower()

        # Check exact prefix match (e.g. "A)" vs "A)")
        prefix_user = user_text.strip()[:2].upper()
        prefix_correct = (q.correct_answer or "").strip()[:2].upper()

        is_match = (norm_user == norm_correct) or (prefix_user == prefix_correct and len(prefix_user) == 2 and prefix_user[1] == ')')

        score = 10.0 if is_match else 0.0
        feedback = (
            f"Correct! Well done on identifying the right technical choice."
            if is_match
            else f"Incorrect. You selected '{user_text}', but the correct answer is '{q.correct_answer}'."
        )

        return QuestionEvaluation(
            question_id=q.id,
            question=q.question,
            type=q.type,
            level=q.level,
            topic=q.topic,
            user_answer=user_text,
            correct_answer=q.correct_answer,
            is_correct=is_match,
            score=score,
            feedback=feedback,
            what_to_learn=f"Internal mechanics of {q.topic}" if not is_match else f"Advanced edge cases in {q.topic}",
            how_to_learn=f"Study: {q.explanation}. Practice hands-on code examples in {q.source_reference or 'the relevant workspace file'}.",
            source_reference=q.source_reference
        )

    def _evaluate_tf(self, q, user_text: str) -> QuestionEvaluation:
        if not user_text:
            return QuestionEvaluation(
                question_id=q.id,
                question=q.question,
                type=q.type,
                level=q.level,
                topic=q.topic,
                user_answer="[No answer provided]",
                correct_answer=q.correct_answer,
                is_correct=False,
                score=0.0,
                feedback="No answer provided.",
                what_to_learn=f"Fundamentals of {q.topic}",
                how_to_learn=f"Read {q.source_reference or 'the course module'} regarding this statement.",
                source_reference=q.source_reference
            )

        u = user_text.strip().lower()
        c = (q.correct_answer or "").strip().lower()

        user_bool = "true" in u
        correct_bool = "true" in c

        is_match = (user_bool == correct_bool)
        score = 10.0 if is_match else 0.0

        feedback = (
            f"Correct! Your evaluation is accurate. {q.explanation}"
            if is_match
            else f"Incorrect. The statement is {q.correct_answer}. {q.explanation}"
        )

        return QuestionEvaluation(
            question_id=q.id,
            question=q.question,
            type=q.type,
            level=q.level,
            topic=q.topic,
            user_answer=user_text,
            correct_answer=q.correct_answer,
            is_correct=is_match,
            score=score,
            feedback=feedback,
            what_to_learn=f"Nuances and edge cases in {q.topic}" if not is_match else f"Deep architecture of {q.topic}",
            how_to_learn=f"Refer to {q.source_reference or 'architecture documentation'}. {q.explanation}",
            source_reference=q.source_reference
        )

    async def _evaluate_descriptive(self, q, user_text: str) -> QuestionEvaluation:
        if not user_text or len(user_text.strip()) < 10:
            return QuestionEvaluation(
                question_id=q.id,
                question=q.question,
                type=q.type,
                level=q.level,
                topic=q.topic,
                user_answer=user_text or "[Empty response]",
                correct_answer=", ".join(q.key_points or []) or q.explanation,
                is_correct=False,
                score=1.0 if user_text else 0.0,
                feedback="Response was too brief or empty. In architectural interviews, articulate the problem, design patterns, trade-offs, and failure recovery.",
                strengths="None detected due to minimal answer length.",
                improvements="Provide a structured answer covering architectural approach, concurrency, and trade-offs.",
                what_to_learn=f"Core architectural principles for {q.topic}.",
                how_to_learn=f"Study {q.source_reference or 'course notes'} and practice structuring answers using STAR or Architecture-Trade-off format.",
                source_reference=q.source_reference
            )

        # 1. Try LLM Evaluation via LLMManager (Ollama, LM Studio, Gemini, Claude, OpenRouter)
        if self.llm_manager:
            llm_eval = await self._evaluate_descriptive_llm(q, user_text)
            if llm_eval:
                return llm_eval

        # 2. Try Ollama Evaluation fallback
        if await self.ollama.is_available():
            ollama_eval = await self._evaluate_descriptive_ollama(q, user_text)
            if ollama_eval:
                return ollama_eval

        # 3. Try Gemini Evaluation
        if self.api_key:
            gemini_eval = await self._evaluate_descriptive_gemini(q, user_text)
            if gemini_eval:
                return gemini_eval

        # 4. Local Rubric Evaluation
        return self._evaluate_descriptive_local(q, user_text)

    async def _evaluate_descriptive_llm(self, q, user_text: str) -> Optional[QuestionEvaluation]:
        try:
            prompt = f"""You are a Principal Software Architect evaluating a candidate's answer in a technical interview.

QUESTION: {q.question}
LEVEL: {q.level}
TOPIC: {q.topic}
EXPECTED KEY ARCHITECTURAL POINTS: {json.dumps(q.key_points or [])}
IDEAL REFERENCE CONTEXT: {q.explanation}

CANDIDATE'S SUBMITTED ANSWER:
\"\"\"{user_text}\"\"\"

Evaluate the answer thoroughly against production engineering criteria.
Output strictly a JSON object:
{{
  "score": float between 0.0 and 10.0,
  "is_correct": boolean,
  "feedback": "2-3 sentences of constructive technical feedback",
  "strengths": "key points the candidate articulated well",
  "improvements": "what was missing or how to elevate this to senior/architect depth"
}}"""
            res = await self.llm_manager.generate_json(
                prompt=prompt,
                system_prompt="You are a Principal Software Architect. Output strictly valid JSON objects.",
                timeout=45.0
            )
            if isinstance(res, dict) and "score" in res:
                return QuestionEvaluation(
                    question_id=q.id,
                    question=q.question,
                    type=q.type,
                    level=q.level,
                    topic=q.topic,
                    user_answer=user_text,
                    correct_answer=", ".join(q.key_points or []),
                    is_correct=bool(res.get("is_correct", res.get("score", 0) >= 6.0)),
                    score=min(max(float(res.get("score", 5.0)), 0.0), 10.0),
                    feedback=res.get("feedback", "Good technical effort."),
                    what_to_learn=f"System trade-offs, concurrency models, and failure recovery for {q.topic}.",
                    how_to_learn=f"Study {q.source_reference or 'architectural notes'}. Prototype a proof-of-concept handling resilience, timeouts, and distributed retries.",
                    source_reference=q.source_reference
                )
            return None
        except Exception as e:
            print(f"[InterviewEvaluator] LLM Manager evaluation failed: {e}")
            return None

    async def _evaluate_descriptive_ollama(self, q, user_text: str) -> Optional[QuestionEvaluation]:
        try:
            prompt = f"""You are a Principal Software Architect evaluating a candidate's answer in a technical interview.

QUESTION: {q.question}
LEVEL: {q.level}
TOPIC: {q.topic}
EXPECTED KEY ARCHITECTURAL POINTS: {json.dumps(q.key_points or [])}
IDEAL REFERENCE CONTEXT: {q.explanation}

CANDIDATE'S SUBMITTED ANSWER:
\"\"\"{user_text}\"\"\"

Evaluate the answer thoroughly against production engineering criteria.
Output strictly a JSON object:
{{
  "score": float between 0.0 and 10.0,
  "is_correct": boolean,
  "feedback": "2-3 sentences of constructive technical feedback",
  "strengths": "key points the candidate articulated well",
  "improvements": "what was missing or how to elevate this to senior/architect depth"
}}"""
            res = await self.ollama.generate_json(prompt, timeout=60.0)
            if isinstance(res, dict) and "score" in res:
                return QuestionEvaluation(
                    question_id=q.id,
                    question=q.question,
                    type=q.type,
                    level=q.level,
                    topic=q.topic,
                    user_answer=user_text,
                    correct_answer=", ".join(q.key_points or []),
                    is_correct=bool(res.get("is_correct", res.get("score", 0) >= 6.0)),
                    score=min(max(float(res.get("score", 5.0)), 0.0), 10.0),
                    feedback=res.get("feedback", "Good technical effort."),
                    what_to_learn=f"System trade-offs, concurrency models, and failure recovery for {q.topic}.",
                    how_to_learn=f"Study {q.source_reference or 'architectural notes'}. Prototype a proof-of-concept handling resilience, timeouts, and distributed retries.",
                    strengths=res.get("strengths", "Covered general principles."),
                    improvements=res.get("improvements", "Elaborate more on failure modes and trade-offs."),
                    source_reference=q.source_reference
                )
        except Exception as e:
            print(f"[InterviewEvaluator] Ollama evaluation fallback: {e}")
            return None

    async def _evaluate_descriptive_gemini(self, q, user_text: str) -> Optional[QuestionEvaluation]:
        try:
            prompt = f"""Evaluate candidate interview answer for {q.level} level.
Question: {q.question}
Key Points: {json.dumps(q.key_points or [])}
Answer: {user_text}

Output strictly JSON:
{{"score": 8.0, "is_correct": true, "feedback": "...", "strengths": "...", "improvements": "..."}}"""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
                if resp.status_code == 200:
                    raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw = re.sub(r"^```json\s*", "", raw)
                    raw = re.sub(r"^```\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                    parsed = json.loads(raw)
                    return QuestionEvaluation(
                        question_id=q.id,
                        question=q.question,
                        type=q.type,
                        level=q.level,
                        topic=q.topic,
                        user_answer=user_text,
                        correct_answer=", ".join(q.key_points or []),
                        is_correct=bool(parsed.get("is_correct", False)),
                        score=float(parsed.get("score", 5.0)),
                        feedback=parsed.get("feedback", ""),
                        strengths=parsed.get("strengths", ""),
                        improvements=parsed.get("improvements", ""),
                        source_reference=q.source_reference
                    )
        except Exception:
            return None

    def _evaluate_descriptive_local(self, q, user_text: str) -> QuestionEvaluation:
        key_points = q.key_points or ["architecture", "concurrency", "trade-offs", "scalability", "resilience"]
        covered = []
        missing = []
        user_lower = user_text.lower()

        for kp in key_points:
            words = [w.lower() for w in re.findall(r'\w+', kp) if len(w) > 3]
            if any(w in user_lower for w in words):
                covered.append(kp)
            else:
                missing.append(kp)

        word_count = len(user_text.split())
        coverage_ratio = len(covered) / max(len(key_points), 1)
        base_score = coverage_ratio * 7.0

        if word_count > 60:
            base_score += 2.0
        elif word_count > 30:
            base_score += 1.0

        final_score = min(round(base_score, 1), 10.0)
        is_correct = final_score >= 6.0

        strengths = f"Addressed core considerations: {', '.join(covered)}." if covered else "Clear articulation of high-level intent."
        improvements = f"Enhance by detailing: {', '.join(missing)} with concrete edge cases." if missing else "Solid coverage. Elaborate more on monitoring and resilience metrics."
        feedback = f"Candidate demonstrated {int(coverage_ratio*100)}% coverage of expected technical points. Depth is well-suited for {q.level} discussions."

        return QuestionEvaluation(
            question_id=q.id,
            question=q.question,
            type=q.type,
            level=q.level,
            topic=q.topic,
            user_answer=user_text,
            correct_answer=", ".join(key_points),
            is_correct=is_correct,
            score=final_score,
            feedback=feedback,
            what_to_learn=f"In-depth architecture & implementation of {q.topic}.",
            how_to_learn=f"Review {q.source_reference or 'study files'}. Practice the 'Trade-off First' technique: contrast alternatives before detailing decisions.",
            strengths=strengths,
            improvements=improvements,
            source_reference=q.source_reference
        )

    def _compute_verdict(self, score: float, level: str) -> str:
        if score >= 90:
            return f"Exceptional {level.title()} Mastery"
        elif score >= 75:
            return f"Strong {level.title()} Readiness"
        elif score >= 60:
            return f"Competent {level.title()} with Growth Potential"
        elif score >= 40:
            return f"Developing - Solidify Core Foundations"
        else:
            return f"Requires Dedicated Preparation"

    def _compute_summary(self, score: float, level: str, correct: int, total: int) -> str:
        return f"Achieved a score of {score}% ({correct}/{total} questions mastered) at the {level.title()} level. Evaluated against real-world enterprise engineering standards."

    def _generate_improvement_roadmap(
        self,
        evaluations: List[QuestionEvaluation],
        level: str,
        overall_score: float
    ) -> List[Dict[str, str]]:
        roadmap = []
        low_scoring = [e for e in evaluations if e.score < 7.0]

        if low_scoring:
            for item in low_scoring[:3]:
                roadmap.append({
                    "area": item.topic,
                    "what_to_do": f"Deep dive into {item.topic} internals and architectural patterns.",
                    "how_to_do": f"Review {item.source_reference or 'study files'}. Write hands-on code simulating edge cases, thread safety, and failover scenarios.",
                    "how_to_improve": f"In interviews, structure your response using the STAR/CAR framework: State the challenge, explain the architectural decision, discuss trade-offs, and cite production metrics."
                })
        else:
            roadmap.append({
                "area": "System Resilience & Distributed Consensus",
                "what_to_do": "Advance to high-scale distributed system patterns (CAP theorem, saga pattern, outbox pattern).",
                "how_to_do": "Prototype distributed tracing with OpenTelemetry and multi-region database replication.",
                "how_to_improve": "Lead system design discussions proactively by defining SLAs/SLOs before choosing database or messaging topologies."
            })

        roadmap.append({
            "area": "Interview Delivery & Architecture Communication",
            "what_to_do": "Master the 'Trade-off First' delivery technique.",
            "how_to_do": "Whenever asked why you chose a pattern (e.g., CQRS vs CRUD), always explicitly contrast 2 alternatives and give the concrete reason for your choice.",
            "how_to_improve": "Practice aloud summarizing complex architectures in 60-second executive summaries before diving into technical weeds."
        })

        return roadmap
