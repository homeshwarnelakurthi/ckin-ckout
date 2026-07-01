"""Dev-server launcher that ensures cwd is this directory (so relative
paths like the SQLite file and .env resolve correctly) regardless of where
the process was invoked from."""
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
