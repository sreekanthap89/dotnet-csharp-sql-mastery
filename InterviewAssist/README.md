# Interview Assist 🚀
### RAG-Powered AI Interview Simulator & Mastery Platform

**Interview Assist** is an AI-driven learning and interview preparation platform that uses Retrieval-Augmented Generation (RAG) to ground realistic technical interviews directly in your study notes, textbooks, and online documentation.

It runs locally and natively across **macOS, Linux, and Windows** with zero platform-specific compilation hurdles.

---

## 🌟 Key Features

1. **Semantic RAG Knowledge Vault**:
   - **Multi-Format Ingestion**: Upload PDF, Markdown (`.md`), Plain Text (`.txt`), or Word (`.docx`) files.
   - **Live Web Scraper**: Enter any technical article or documentation URL (e.g. Microsoft Learn, MDN, blog posts) to automatically scrape, clean, chunk, and index the content into vector memory.
   - **Workspace Quick-Ingest**: Instant 1-click indexing of the 37+ C#/.NET and Azure learning modules located in this repository!
   - **Semantic Search Sandbox**: Test vector similarity retrieval and inspect top-k matching chunks in real time.

2. **Adaptive Technical Interview Arena**:
   - **Configurable Rounds**: Select question count (default 10, or customized between 3 and 50).
   - **Target Proficiency Levels**:
     - 🟢 **Beginner**: Core syntax, fundamental definitions, simple principles.
     - 🔵 **Intermediate**: Practical architecture, exception handling, data access, best practices.
     - 🟣 **Senior**: Concurrency, memory allocation, profiling, performance bottlenecks.
     - 👑 **Architect**: High availability, microservices, distributed consensus, resiliency, and trade-offs.
   - **Multi-Modal Question Formats**:
     - **Multiple Choice (MCQ)**: 4 interactive options with real-time selection and detailed rationale.
     - **True / False**: Binary toggle mode with misconception clarifications.
     - **Descriptive & Architectural Scenarios**: Rich code/markdown editor with key-points analysis, live word counter, and trade-off expectations.
   - **Interactive Interviewer Features**:
     - Conversational prompts and progress tracker.
     - "Clarification / Hint" button to probe for architectural considerations.
     - Real-time question navigation map and timer.

3. **Post-Interview AI Scorecard & Actionable Roadmap**:
   - **Radial Score & Verdict**: Granular percentage score and benchmark rating (e.g., *Exceptional Architect Mastery*, *Strong Senior Readiness*).
   - **Topic Mastery Breakdown**: Visual progress bars showing strengths and weaknesses across subjects.
   - **Question-by-Question Deep Dive**: Detailed breakdown comparing candidate responses against expected standards, with source citations linked to your uploaded files.
   - **"What to do, How to do, How to improve" Action Plan**: Actionable study roadmap recommending concrete projects, STAR framework delivery techniques, and source review.
   - **Exportable Markdown Report**: 1-click download of the complete interview assessment.

---

## ⚡ Quick Start

### On macOS / Linux:
> [!IMPORTANT]
> Make sure to prefix with `./` when running in the current directory:
```bash
cd InterviewAssist
./start.sh
```
*(Or run `bash start.sh`)*

### On Windows:
Double-click `InterviewAssist\start.bat` or run in PowerShell / Command Prompt:
```cmd
InterviewAssist\start.bat
```

The startup script will:
1. Ensure a Python 3 virtual environment (`venv`) exists.
2. Install all required dependencies from `requirements.txt`.
3. Auto-detect your local **Ollama** server and load your installed models (e.g. `VladimirGav/gemma4-26b-16GB-VRAM-Uncensored:latest` or `qwen3-coder:30b`).
4. Launch the FastAPI server at `http://localhost:8000`.
5. Automatically open your default web browser.

---

## 🦙 Ollama Local AI Engine

Interview Assist automatically integrates with your local **Ollama** instance (`http://127.0.0.1:11434`):
- **100% Local & GPU Accelerated**: Generates deep, authentic, senior & architect level interview questions directly from your RAG study files without sending data to the cloud.
- **Model Selection**: Click **Settings** in the top navigation bar to select any model installed on your machine (e.g. `VladimirGav/gemma4-26b...`, `qwen3-coder:30b`, etc.).
- **Smart Cleanup**: Automatically cleans reasoning/thinking tokens (`<think>...</think>`) emitted by thinking models.
