#!/usr/bin/env python3
"""
Local launcher script for AI Job Search & Application Intelligence Platform.
Starts both backend (FastAPI) and frontend (Next.js) in development mode.
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

def check_prerequisites():
    """Check if required tools are installed."""
    # Check Python
    if sys.version_info < (3, 11):
        print("Error: Python 3.11+ required")
        sys.exit(1)

    # Check if we're in the right directory
    backend_path = Path(__file__).parent / "backend"
    frontend_path = Path(__file__).parent / "frontend"

    if not backend_path.exists():
        print("Error: Backend directory not found. Run from project root.")
        sys.exit(1)

    # Check for .env file
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        example_path = Path(__file__).parent / ".env.example"
        if example_path.exists():
            print("Warning: .env not found. Copying from .env.example")
            import shutil
            shutil.copy(example_path, env_path)
            print("Please edit .env with your configuration (especially ANTHROPIC_API_KEY)")
        else:
            print("Error: Neither .env nor .env.example found")
            sys.exit(1)

    return backend_path, frontend_path

def start_backend(backend_path):
    """Start the FastAPI backend server."""
    print("Starting backend server...")
    os.chdir(backend_path)

    # Activate virtual environment if it exists
    venv_path = backend_path / "venv"
    if venv_path.exists():
        if os.name == 'nt':  # Windows
            activate_script = venv_path / "Scripts" / "activate.bat"
        else:  # Unix/Linux/Mac
            activate_script = venv_path / "bin" / "activate"

        if activate_script.exists():
            print(f"Activating virtual environment: {activate_script}")

    # Start uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8765",
        "--reload"
    ]

    print(f"Running: {' '.join(cmd)}")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def start_frontend(frontend_path):
    """Start the Next.js frontend development server."""
    print("Starting frontend server...")
    os.chdir(frontend_path)

    # Check if node_modules exists, if not install
    node_modules = frontend_path / "node_modules"
    if not node_modules.exists():
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], check=True)

    # Start Next.js dev server
    cmd = ["npm", "run", "dev"]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def main():
    """Main launcher function."""
    print("=" * 60)
    print("AI Job Search & Application Intelligence Platform")
    print("=" * 60)

    try:
        backend_path, frontend_path = check_prerequisites()

        # Start backend
        backend_proc = start_backend(backend_path)
        time.sleep(3)  # Give backend time to start

        # Check if backend started successfully
        if backend_proc.poll() is not None:
            stdout, _ = backend_proc.communicate()
            print(f"Backend failed to start:\n{stdout}")
            sys.exit(1)

        print("✓ Backend started on http://127.0.0.1:8765")

        # Try to start frontend (optional for now since it's not built yet)
        frontend_proc = None
        try:
            if frontend_path.exists():
                frontend_proc = start_frontend(frontend_path)
                time.sleep(3)
                if frontend_proc.poll() is None:
                    print("✓ Frontend started on http://localhost:3000")
                else:
                    stdout, _ = frontend_proc.communicate()
                    print(f"Frontend failed to start (may not be implemented yet):\n{stdout}")
                    frontend_proc = None
            else:
                print("ℹ Frontend directory not found - skipping frontend startup")
                print("  Run 'mkdir frontend' and build your Next.js app when ready")
        except Exception as e:
            print(f"ℹ Frontend startup skipped: {e}")
            frontend_proc = None

        print("\n" + "=" * 60)
        print("Platform is running!")
        print("Backend API: http://127.0.0.1:8765")
        print("API Docs: http://127.0.0.1:8765/docs")
        if frontend_proc:
            print("Frontend: http://localhost:3000")
        print("=" * 60)
        print("Press Ctrl+C to stop all servers")
        print("=" * 60)

        # Wait for processes
        try:
            while True:
                time.sleep(1)
                # Check if processes are still alive
                if backend_proc.poll() is not None:
                    stdout, _ = backend_proc.communicate()
                    print(f"Backend stopped unexpectedly:\n{stdout}")
                    break
                if frontend_proc and frontend_proc.poll() is not None:
                    stdout, _ = frontend_proc.communicate()
                    print(f"Frontend stopped unexpectedly:\n{stdout}")
                    break
        except KeyboardInterrupt:
            print("\nShutting down...")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        print("Stopping servers...")
        if 'backend_proc' in locals() and backend_proc:
            backend_proc.terminate()
            backend_proc.wait(timeout=5)
        if 'frontend_proc' in locals() and frontend_proc:
            frontend_proc.terminate()
            frontend_proc.wait(timeout=5)
        print("Goodbye!")

if __name__ == "__main__":
    main()