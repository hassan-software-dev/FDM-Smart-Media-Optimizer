"""
Dependency checker and installer for FDM Smart Media Optimizer.
This script handles yt-dlp installation and verification.
"""

import sys
import json
import subprocess
import os

# Consistent timeout values
TIMEOUT_VERSION_CHECK = 15
TIMEOUT_INSTALL = 300  # 5 minutes, matching extractor.py

# Minimum recommended yt-dlp version (YYYY.MM.DD format)
MIN_RECOMMENDED_VERSION = "2024.01.01"


def parse_version(version_str):
    """Parse yt-dlp version string to comparable tuple."""
    try:
        # yt-dlp uses YYYY.MM.DD format
        parts = version_str.strip().split('.')
        return tuple(int(p) for p in parts[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def is_version_adequate(version_str):
    """Check if version meets minimum recommendation."""
    if not version_str:
        return False
    current = parse_version(version_str)
    minimum = parse_version(MIN_RECOMMENDED_VERSION)
    return current >= minimum


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
            timeout=TIMEOUT_VERSION_CHECK,
            shell=False
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return {
                "installed": True,
                "version": version,
                "versionAdequate": is_version_adequate(version),
                "minRecommended": MIN_RECOMMENDED_VERSION,
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
            timeout=TIMEOUT_INSTALL,
            shell=False
        )
        
        if result.returncode == 0:
            # Verify installation
            check = check_ytdlp()
            return {
                "success": True,
                "message": "yt-dlp installed successfully",
                "version": check.get("version"),
                "versionAdequate": check.get("versionAdequate", False),
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
            "error": f"The installation took longer than {TIMEOUT_INSTALL} seconds. Please check your internet connection."
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
