"""
Dependency checker and installer for FDM Smart Media Optimizer.
This script handles yt-dlp installation and verification.
"""

import sys
import json
import subprocess
import os

def get_python_info():
    """Get Python interpreter information."""
    return {
        "version": sys.version,
        "executable": sys.executable,
        "path": sys.path
    }


def check_ytdlp():
    """Check if yt-dlp is installed and get version."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False
        )
        if result.returncode == 0:
            return {
                "installed": True,
                "version": result.stdout.strip(),
                "error": None
            }
        return {
            "installed": False,
            "version": None,
            "error": result.stderr.strip() if result.stderr else "Unknown error"
        }
    except FileNotFoundError:
        return {
            "installed": False,
            "version": None,
            "error": "yt-dlp executable not found in PATH"
        }
    except subprocess.TimeoutExpired:
        return {
            "installed": False,
            "version": None,
            "error": "Version check timed out"
        }
    except Exception as e:
        return {
            "installed": False,
            "version": None,
            "error": str(e)[:200]
        }


def install_ytdlp(upgrade=False):
    """Install or upgrade yt-dlp via pip."""
    try:
        cmd = [sys.executable, "-m", "pip", "install"]
        if upgrade:
            cmd.append("--upgrade")
        cmd.append("yt-dlp")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minutes for slow connections
            shell=False
        )
        
        if result.returncode == 0:
            # Verify installation
            check = check_ytdlp()
            return {
                "success": True,
                "message": "yt-dlp installed successfully",
                "version": check.get("version"),
                "output": result.stdout[-500:] if result.stdout else None
            }
        else:
            return {
                "success": False,
                "message": "Installation failed",
                "version": None,
                "error": result.stderr[:500] if result.stderr else "Unknown error"
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Installation timed out",
            "version": None,
            "error": "The installation took too long. Please check your internet connection."
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Installation error",
            "version": None,
            "error": str(e)[:200]
        }


def check_pip():
    """Check if pip is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False
        )
        if result.returncode == 0:
            return {
                "available": True,
                "version": result.stdout.strip()
            }
        return {
            "available": False,
            "error": result.stderr.strip() if result.stderr else "pip not available"
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)[:100]
        }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command provided. Use: check, install, or status"}))
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "check":
        result = check_ytdlp()
        print(json.dumps(result))
        sys.exit(0 if result["installed"] else 1)
    
    elif command == "install":
        upgrade = "--upgrade" in sys.argv
        
        # First check pip
        pip_check = check_pip()
        if not pip_check.get("available"):
            print(json.dumps({
                "success": False,
                "message": "pip is not available",
                "error": pip_check.get("error", "Cannot install packages without pip")
            }))
            sys.exit(1)
        
        result = install_ytdlp(upgrade=upgrade)
        print(json.dumps(result))
        sys.exit(0 if result["success"] else 1)
    
    elif command == "status":
        result = {
            "python": get_python_info(),
            "pip": check_pip(),
            "ytdlp": check_ytdlp()
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)
    
    else:
        print(json.dumps({"error": f"Unknown command: {command}. Use: check, install, or status"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
