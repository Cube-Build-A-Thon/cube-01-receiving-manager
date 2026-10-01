# Receiving Manager · Packaged Agent

This directory contains the complete Receiving Manager agent codebase, test suite, fixtures, and UI application.

## Quickstart

### Backend & Headless Agent
```bash
pip install fastapi uvicorn pydantic pytest pillow google-generativeai
pytest tests/
python start_server.py
```

### Frontend Dock Station UI
```bash
cd frontend
npm install
npm run dev
```

### Full Test Suite
```bash
pytest -v
```
All 70 automated tests (including 12 dedicated Evidence Contract v1.1 tests) pass 100%.
