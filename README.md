# Asama.ai Assignment Submission: Engineering Architecture Guides

This repository contains the comprehensive engineering architecture, data specifications, security models, mathematical formulations, and implementation blueprints for both problems from the **Asama.ai Assignment Reference**:

---

## Table of Contents

1. [Problem 1: A Social Network for AI Agents](./PROBLEM_1_SOCIAL_NETWORK_FOR_AI_AGENTS.md)
   - **Executive Summary & B2B Ecosystem**
   - **Multi-Stage Semantic Relevance Routing Engine** (Stage 1 SQL Filters $\to$ Stage 2 pgvector HNSW ANN Search $\to$ Stage 3 Cross-Encoder Reranker)
   - **PostgreSQL + pgvector Schema & API Specifications**
   - **Webhook Delivery Engine with HMAC-SHA256 Signatures & Isolation**
   - **Dynamic Profile Learning & Gradient-Based Feedback Loops**
   - **Prompt Injection Defense & Zero-Trust Agent Security**
   - **$10,000+$ Agent Scalability & Latency Optimization**
   - **End-to-End Modular Python Reference Implementation**

2. [Problem 2: Local Linux Hardware Q&A Assistant](./PROBLEM_2_LINUX_HARDWARE_QA_ASSISTANT.md)
   - **Executive Summary & System Vision**
   - **Deterministic Tool-Calling Architecture & Allow-List Enforcement**
   - **Zero-Shell Execution (`execve` / `shell=False`) & Parameter Sanitization**
   - **Privilege Escalation Strategies** (Scoped Sudoers vs. Privilege Daemon vs. `/sys` & `/proc` Non-Root Fallbacks)
   - **Parsing & Normalization Engine** (`dmidecode`, `lscpu`, `lsblk`, `free`, `lspci`)
   - **Anti-Hallucination Guardrails & Dynamic Tool Registry**
   - **Local LLM Engine Optimization** (Ollama, llama.cpp, Qwen2.5 / Llama-3.2)
   - **Complete Python Safe-Execution & Assistant Engine**

---

## Quick Navigation

| Document | Focus Area | Tech Stack |
| :--- | :--- | :--- |
| [Problem 1 Guide](./PROBLEM_1_SOCIAL_NETWORK_FOR_AI_AGENTS.md) | Distributed Agent Social Graph & Multi-Stage Event Routing | FastAPI, PostgreSQL + pgvector, Redis Streams, Celery, Cross-Encoders, HMAC |
| [Problem 2 Guide](./PROBLEM_2_LINUX_HARDWARE_QA_ASSISTANT.md) | Secure Host Hardware Inspection & Deterministic Tool Agent | Python 3.11+, Typer/Textual, `execve`, Linux Sysfs/DMI, Local LLM (Ollama) |
