# DevMaster Assistant Prompt

Copy and paste this prompt at the start of each new chat session to ensure continuity:

---

## 🚀 DevMaster Project Continuation

I'm working on the DevMaster project - an AI-powered full-stack development platform. Please help me continue development.

**First, read these two critical documents to understand the current state:**

1. **Current State Overview**: `/Users/adityachaudhary/Documents/devmaster/docs/CURRENT_STATE.md`
   - This shows what's currently working and the immediate focus

2. **Detailed Progress Report**: `/Users/adityachaudhary/Documents/devmaster/docs/project_progress_report.md`
   - This contains the full history, decisions made, and next tasks

**Project Location**: `/Users/adityachaudhary/Documents/devmaster`

**After reading both documents, please:**
1. Briefly summarize the current project phase and status
2. Identify the next task(s) to be completed according to the progress report
3. Ask any clarifying questions before starting work
4. Begin working on the identified next task

**Important Context:**
- We're following the Tech Bible, Blueprint, and Implementation Plan documents
- Always update the progress report after significant changes
- The project uses Python 3.11+, FastAPI, React, PostgreSQL, and LangGraph
- We're currently in Phase 2 (Platform Primitives) starting with Week 5
- Git commits should be made after each major milestone

**GitHub Repository**: https://github.com/Adityaxd/devmaster

Please read the documents now and let's continue building DevMaster!

---

## 📌 Quick Reference Paths

```bash
# Key Documents
/Users/adityachaudhary/Documents/devmaster/docs/CURRENT_STATE.md
/Users/adityachaudhary/Documents/devmaster/docs/project_progress_report.md
/Users/adityachaudhary/Documents/devmaster/docs/blueprint.pdf
/Users/adityachaudhary/Documents/devmaster/docs/tech_bible.pdf
/Users/adityachaudhary/Documents/devmaster/docs/implementation_plan.pdf
/Users/adityachaudhary/Documents/devmaster/docs/KnowledgeBase.md
/Users/adityachaudhary/Documents/devmaster/docs/ExtraKnowledgeBase.pdf

# Project Root
/Users/adityachaudhary/Documents/devmaster

# Backend
/Users/adityachaudhary/Documents/devmaster/backend

# Run the server
cd /Users/adityachaudhary/Documents/devmaster/backend
python3 -m uvicorn app.main:app --reload --port 8003
```
