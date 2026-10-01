import uvicorn
import os
import sys

if __name__ == "__main__":
    print("===============================================================")
    print(" Starting Cube 01 · Receiving Manager Backend (Port 8000)")
    print(" Tenancy RLS: ENABLED AND FORCED")
    print(" Single-Pass Batch Vision Model: ACTIVE")
    print("===============================================================")
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
