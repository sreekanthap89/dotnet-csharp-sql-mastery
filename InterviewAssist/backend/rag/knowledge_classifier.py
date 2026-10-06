import re
from typing import List, Dict, Any, Set

class KnowledgeClassifier:
    """
    Dynamically analyzes documents and text chunks in vector memory
    to detect technology stacks, programming languages, and specialized domains.
    Strictly prevents cross-language false positives (e.g. C# documents mentioning Java or Docker).
    """

    # Direct mapping for all 45 workspace modules + README
    WORKSPACE_PREFIX_MAP = {
        # 010 to 130 + README: C# Core, OOP & Memory
        "010_": "csharp", "020_": "csharp", "030_": "csharp", "040_": "csharp",
        "050_": "csharp", "060_": "csharp", "070_": "csharp", "080_": "csharp",
        "090_": "csharp", "100_": "csharp", "110_": "csharp", "120_": "csharp", "130_": "csharp",
        "README.md": "csharp",
        # 140 to 170: SQL Server, Indexes & EF Core
        "140_": "sql", "150_": "sql", "160_": "sql", "170_": "sql",
        # 180 to 240: ASP.NET Core & Web API
        "180_": "aspnet", "190_": "aspnet", "200_": "aspnet", "210_": "aspnet",
        "220_": "aspnet", "230_": "aspnet", "240_": "aspnet",
        # 250 to 260: SOLID Principles & Design Patterns
        "250_": "patterns", "260_": "patterns",
        # 270 to 300: Microservices, Distributed Systems & System Design
        "270_": "system_design", "280_": "system_design", "290_": "system_design", "300_": "system_design",
        # 310 to 370: Cloud Platform, Azure Infrastructure & DevOps
        "310_": "azure", "320_": "azure", "330_": "azure", "340_": "azure",
        "350_": "azure", "360_": "azure", "370_": "azure",
        # 380 to 400: Generative AI, LLMs, RAG & Agents
        "380_": "ai", "390_": "ai", "400_": "ai",
        # 410 to 450: Coding Problems & Algorithmic Patterns
        "410_": "algorithms", "420_": "algorithms", "430_": "algorithms",
        "440_": "algorithms", "450_": "algorithms"
    }

    PREDEFINED_DOMAINS = [
        {
            "id": "csharp",
            "name": "C# Core, OOP & Memory Management",
            "icon": "⚡",
            "description": "Generics, Collections, GC, Concurrency, ThreadPool, LINQ",
            "extensions": [".cs", ".csproj", ".sln"],
            "title_regex": r"(?i)\b(c#|csharp|dotnet|\.net|clr|idisposable|linq|threadpool)\b",
            "body_regex": r"(?i)(\bnamespace\s+\w+|\busing\s+System\b|\bpublic\s+class\s+\w+.*\{)"
        },
        {
            "id": "sql",
            "name": "SQL Server, Indexes & EF Core",
            "icon": "🗄️",
            "description": "Joins, Clustered/Non-Clustered Indexes, Stored Procedures, EF Core",
            "extensions": [".sql"],
            "title_regex": r"(?i)\b(sql|database|ef\s*core|entity\s*framework|stored\s*procedure|indexes?)\b",
            "body_regex": r"(?i)(\bselect\s+.*\s+from\b|\bcreate\s+table\b|\binner\s+join\b|\bclustered\s+index\b)"
        },
        {
            "id": "aspnet",
            "name": "ASP.NET Core & Web API",
            "icon": "🚀",
            "description": "DI, Middleware, Service Lifetimes, Routing, JWT, CORS",
            "extensions": [],
            "title_regex": r"(?i)\b(asp\.?net|web\s*api|middleware|dependency\s*injection|jwt|cors)\b",
            "body_regex": r"(?i)(\baddscoped\b|\baddsingleton\b|\busemiddleware\b|\bactionresult\b)"
        },
        {
            "id": "azure",
            "name": "Azure Cloud, Serverless & Messaging",
            "icon": "☁️",
            "description": "Azure Functions, Event Grid, Entra ID, Key Vault, Storage, App Service",
            "extensions": [],
            "title_regex": r"(?i)\b(azure|entra\s*id|event\s*grid|key\s*vault|serverless|blob\s*storage|app\s*service)\b",
            "body_regex": r"(?i)(\bazure\s*function\b|\bfunctionname\b|\bdefaultazurecredential\b)"
        },
        {
            "id": "system_design",
            "name": "Distributed Systems & System Design",
            "icon": "🏗️",
            "description": "Scalability, CAP/PACELC, Caching, Sharding, Sagas, Outbox, YARP",
            "extensions": [],
            "title_regex": r"(?i)\b(system\s*design|distributed|microservices?|caching|rate\s*limiting|pacelc|yarp|outbox|saga)\b",
            "body_regex": r"(?i)(\bconsistent\s+hashing\b|\bcache\s+aside\b|\bcircuit\s+breaker\b|\btraceparent\b)"
        },
        {
            "id": "ai",
            "name": "AI Engineering, LLM & RAG in .NET",
            "icon": "🤖",
            "description": "Semantic Kernel, Microsoft.Extensions.AI, RAG, Vector Stores, MCP",
            "extensions": [],
            "title_regex": r"(?i)\b(ai|llm|rag|vector|semantic\s*kernel|embeddings?|mcp|prompt)\b",
            "body_regex": r"(?i)(\bsemantickernel\b|\bmicrosoft\.extensions\.ai\b|\bchatcompletion\b|\bvectorstore\b)"
        },
        {
            "id": "patterns",
            "name": "SOLID Principles & Design Patterns",
            "icon": "🏛️",
            "description": "Factory, Singleton, Repository, Clean Architecture, CQRS",
            "extensions": [],
            "title_regex": r"(?i)\b(solid|design\s*patterns?|clean\s*architecture|cqrs|repository\s*pattern)\b",
            "body_regex": r"(?i)(\bsingle\s+responsibility\b|\bopen\s*closed\b|\bliskov\b|\bdependency\s+inversion\b)"
        },
        {
            "id": "algorithms",
            "name": "Coding Problems & Algorithmic Patterns",
            "icon": "💻",
            "description": "Arrays, Strings, Frequency Maps, Two Pointers, Numbers",
            "extensions": [],
            "title_regex": r"(?i)\b(coding\s*problems?|two\s*pointers?|sliding\s*window|binary\s*search)\b",
            "body_regex": r"(?i)(\btwo\s+pointer\b|\bsliding\s+window\b|\bfrequency\s+map\b)"
        },
        {
            "id": "python",
            "name": "Python Engineering & Ecosystem",
            "icon": "🐍",
            "description": "Python, FastAPI, Django, Asyncio, Data Structures, Decorators",
            "extensions": [".py", ".ipynb"],
            "title_regex": r"(?i)\b(python|fastapi|django|flask|pydantic|asyncio|pytest|pandas|numpy)\b",
            "body_regex": r"(?i)(\bdef\s+[a-z_][a-z0-9_]*\s*\(|\bimport\s+(asyncio|fastapi|pydantic|numpy|pandas)\b|\bfrom\s+typing\s+import\b)"
        },
        {
            "id": "java",
            "name": "Java & Spring Architecture",
            "icon": "☕",
            "description": "Java Core, JVM, Spring Boot, Hibernate, Concurrency",
            "extensions": [".java", ".jar", ".class"],
            "title_regex": r"(?i)\b(java|spring\s*boot|springboot|hibernate|jvm|maven|gradle)\b",
            "body_regex": r"(?i)(\bpublic\s+static\s+void\s+main\b|\b@SpringBootApplication\b|\bpackage\s+[a-z0-9_.]+\s*;|\bimport\s+java\.)"
        },
        {
            "id": "golang",
            "name": "Go (Golang) Systems & Microservices",
            "icon": "🐹",
            "description": "Goroutines, Channels, Interfaces, Go Microservices",
            "extensions": [".go"],
            "title_regex": r"(?i)\b(golang|goroutine|go\s*mod)\b",
            "body_regex": r"(?i)(\bfunc\s+main\s*\(\)|\bpackage\s+main\b|\bchan\s+[a-z0-9_]+\b|\bgoroutine\b)"
        },
        {
            "id": "javascript",
            "name": "JavaScript, TypeScript & Web",
            "icon": "🟨",
            "description": "ES6+, TypeScript, React, Node.js, Next.js, Frontend Architecture",
            "extensions": [".js", ".ts", ".jsx", ".tsx"],
            "title_regex": r"(?i)\b(javascript|typescript|react|next\.?js|node\.?js|vue|angular)\b",
            "body_regex": r"(?i)(\bimport\s+React\b|\bconst\s+[a-z0-9_]+\s*=\s*\(\)\s*=>|\bconsole\.log\b)"
        },
        {
            "id": "devops",
            "name": "DevOps, Docker & Kubernetes",
            "icon": "🐳",
            "description": "Containers, Kubernetes, CI/CD Pipelines, Infrastructure as Code",
            "extensions": [".dockerfile", ".k8s"],
            "title_regex": r"(?i)\b(dockerfile|kubernetes|k8s|terraform|ansible|helm)\b",
            "body_regex": r"(?i)(\bapiVersion:\s*apps/v1\b|\bFROM\s+[a-z0-9_]+:\w+\b|\bcontainer_name\b)"
        }
    ]

    @classmethod
    def _is_workspace_doc(cls, filename: str) -> bool:
        if not filename:
            return False
        for prefix in cls.WORKSPACE_PREFIX_MAP.keys():
            if filename.startswith(prefix) or filename == prefix:
                return True
        return False

    @classmethod
    def _get_workspace_domain(cls, filename: str) -> str:
        for prefix, domain in cls.WORKSPACE_PREFIX_MAP.items():
            if filename.startswith(prefix) or filename == prefix:
                return domain
        return "csharp"

    @classmethod
    def discover_areas(cls, documents: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans all documents and chunks, mapping them strictly to their rightful domains.
        Returns ONLY domains that have at least 1 document.
        Workspace documents are NEVER falsely attributed to Java, Python, Go, JS, or DevOps.
        """
        if not documents:
            return [
                {
                    "id": "all",
                    "name": "All Materials & Mixed Topics",
                    "icon": "🌐",
                    "description": "Upload documents or scrape URLs to build your knowledge base",
                    "count": 0,
                    "chunk_count": 0,
                    "doc_ids": []
                }
            ]

        # 1. Start with All Materials
        areas = [
            {
                "id": "all",
                "name": "All Materials & Mixed Topics",
                "icon": "🌐",
                "description": f"Comprehensive questions synthesized from all {len(documents)} indexed documents",
                "count": len(documents),
                "chunk_count": len(chunks),
                "doc_ids": [d["id"] for d in documents]
            }
        ]

        # Map doc_id to combined chunk sample text (first 3000 chars)
        doc_texts: Dict[str, str] = {}
        for c in chunks:
            did = c.get("doc_id")
            if did:
                if did not in doc_texts:
                    doc_texts[did] = ""
                if len(doc_texts[did]) < 3000:
                    doc_texts[did] += " " + c.get("text", "")

        matched_doc_ids: Set[str] = set()
        domain_docs_map: Dict[str, List[str]] = {d["id"]: [] for d in cls.PREDEFINED_DOMAINS}

        # Step A: Classify workspace documents strictly
        for doc in documents:
            did = doc["id"]
            source = doc.get("source", "")
            title = doc.get("title", "")
            fname = source or title

            if cls._is_workspace_doc(fname):
                target_domain = cls._get_workspace_domain(fname)
                domain_docs_map[target_domain].append(did)
                matched_doc_ids.add(did)

        # Step B: Classify uploaded / external documents
        external_docs = [d for d in documents if d["id"] not in matched_doc_ids]
        for doc in external_docs:
            did = doc["id"]
            source = (doc.get("source") or "").lower()
            title = (doc.get("title") or "").lower()
            file_type = (doc.get("file_type") or "").lower()
            norm_name = re.sub(r"[_\-\.]+", " ", f"{title} {source}")
            text_sample = doc_texts.get(did, "")

            matched_domain = None
            for domain_def in cls.PREDEFINED_DOMAINS:
                d_id = domain_def["id"]

                # 1. File extension match
                if any(source.endswith(ext) or title.endswith(ext) for ext in domain_def.get("extensions", [])):
                    matched_domain = d_id
                    break

                # 2. Title regex match on normalized name
                title_regex = domain_def.get("title_regex")
                if title_regex and re.search(title_regex, norm_name):
                    matched_domain = d_id
                    break

                # 3. Body syntax regex match (requires strict language-specific constructs)
                body_regex = domain_def.get("body_regex")
                if body_regex and text_sample:
                    matches = re.findall(body_regex, text_sample)
                    if len(matches) >= 2:
                        matched_domain = d_id
                        break

            if matched_domain:
                domain_docs_map[matched_domain].append(did)
                matched_doc_ids.add(did)

        # Step C: Populate predefined domains that have at least 1 document
        for domain_def in cls.PREDEFINED_DOMAINS:
            d_id = domain_def["id"]
            docs_in_domain = domain_docs_map.get(d_id, [])
            if docs_in_domain:
                domain_chunks = sum(1 for c in chunks if c.get("doc_id") in docs_in_domain)
                areas.append({
                    "id": domain_def["id"],
                    "name": domain_def["name"],
                    "icon": domain_def["icon"],
                    "description": domain_def["description"],
                    "count": len(docs_in_domain),
                    "chunk_count": domain_chunks,
                    "doc_ids": docs_in_domain
                })

        # Step D: For any external document not matching predefined domains, create an individualized document card
        unmatched_docs = [d for d in documents if d["id"] not in matched_doc_ids]
        for doc in unmatched_docs:
            clean_title = re.sub(r"^\d+_", "", doc.get("title", ""))
            clean_title = re.sub(r"\.(md|pdf|docx|txt|py|java|go|js|ts)$", "", clean_title, flags=re.IGNORECASE)
            clean_title = clean_title.replace("_", " ").replace("-", " ").title()

            doc_chunks = sum(1 for c in chunks if c.get("doc_id") == doc["id"])
            areas.append({
                "id": f"doc_{doc['id']}",
                "name": f"{clean_title}",
                "icon": "📖",
                "description": f"Focused on {doc.get('title')} ({doc.get('file_type', 'file').upper()})",
                "count": 1,
                "chunk_count": doc_chunks,
                "doc_ids": [doc["id"]]
            })

        return areas
