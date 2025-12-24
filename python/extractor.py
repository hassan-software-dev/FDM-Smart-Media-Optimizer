import sys, json, subprocess, os, re
from urllib.parse import urlparse

# === LARGE DOWNLOAD CONFIGURATION ===

# Default configuration for large downloads (can be overridden by JS)
DEFAULT_LARGE_CONFIG = {
    "maxOutputSize": 50 * 1024 * 1024,    # 50MB
    "extractionTimeout": 300,              # 5 minutes
    "maxFormats": 50,
    "maxFragments": 10000,
    "maxPlaylistEntries": 500,
    "chunkSize": 10 * 1024 * 1024
}

# Will be updated from command line args if provided
LARGE_CONFIG = DEFAULT_LARGE_CONFIG.copy()


# === YT-DLP AVAILABILITY CHECK ===

def check_ytdlp_installed():
    """Check if yt-dlp is installed and accessible."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, None
    except FileNotFoundError:
        return False, None
    except subprocess.TimeoutExpired:
        return False, None
    except Exception:
        return False, None


def install_ytdlp():
    """Attempt to install yt-dlp via pip."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=120,
            shell=False
        )
        if result.returncode == 0:
            return True, "yt-dlp installed successfully"
        return False, f"pip install failed: {result.stderr[:500]}"
    except subprocess.TimeoutExpired:
        return False, "Installation timed out after 120 seconds"
    except Exception as e:
        return False, f"Installation failed: {str(e)[:200]}"


# Check for special commands
if len(sys.argv) >= 2:
    if sys.argv[1] == "--check-ytdlp":
        installed, version = check_ytdlp_installed()
        print(json.dumps({
            "installed": installed,
            "version": version
        }))
        sys.exit(0)
    
    if sys.argv[1] == "--install-ytdlp":
        # First check if already installed
        installed, version = check_ytdlp_installed()
        if installed:
            print(json.dumps({
                "success": True,
                "message": f"yt-dlp is already installed (version {version})",
                "version": version
            }))
            sys.exit(0)
        
        # Attempt installation
        success, message = install_ytdlp()
        if success:
            # Verify installation
            installed, version = check_ytdlp_installed()
            print(json.dumps({
                "success": installed,
                "message": message,
                "version": version
            }))
        else:
            print(json.dumps({
                "success": False,
                "message": message,
                "version": None
            }))
        sys.exit(0 if success else 1)


# === SECURITY VALIDATION ===

def is_safe_url(url):
    """Validate URL to prevent command injection and malicious schemes."""
    if not url or not isinstance(url, str):
        return False, "URL is empty or invalid type"
    
    # Length limit to prevent buffer overflow attacks
    if len(url) > 4096:
        return False, "URL exceeds maximum length (4096 characters)"
    
    # Reject dangerous characters that could enable command injection
    dangerous_patterns = [
        r'[;\|&`$]',           # Shell metacharacters
        r'\$\(',               # Command substitution
        r'`',                  # Backtick execution
        r'\.\.',               # Path traversal
        r'[\x00-\x1f\x7f]',    # Control characters
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, url):
            return False, f"URL contains potentially dangerous characters (pattern: {pattern})"
    
    try:
        parsed = urlparse(url)
        # Only allow http/https schemes
        if parsed.scheme not in ('http', 'https'):
            return False, f"Unsupported URL scheme: {parsed.scheme}. Only http/https allowed"
        
        # Must have a valid hostname
        if not parsed.netloc or len(parsed.netloc) < 3:
            return False, "URL must have a valid hostname"
        
        # Reject local/private addresses
        hostname = parsed.netloc.split(':')[0].lower()
        private_patterns = [
            r'^localhost$',
            r'^127\.',
            r'^10\.',
            r'^192\.168\.',
            r'^172\.(1[6-9]|2[0-9]|3[01])\.',
            r'^0\.0\.0\.0$',
            r'^\[::1\]$',
            r'^file://',
        ]
        for pattern in private_patterns:
            if re.match(pattern, hostname):
                return False, "WARNING: URL points to local/private network. This could be a security risk attempting to access internal resources."
        
        return True, None
    except Exception as e:
        return False, f"URL parsing failed: {e}"


def sanitize_string_arg(arg, name, max_length=2048):
    """Sanitize string arguments to prevent injection attacks."""
    if arg is None:
        return None
    if not isinstance(arg, str):
        raise ValueError(f"{name} must be a string")
    if len(arg) > max_length:
        raise ValueError(f"{name} exceeds maximum length ({max_length})")
    # Remove null bytes and control characters
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', arg)
    return sanitized if sanitized else None


def validate_profile(profile):
    """Ensure profile is one of the allowed values."""
    allowed = {"FASTEST", "BALANCED", "QUALITY"}
    if profile not in allowed:
        return "BALANCED"  # Safe default
    return profile


def validate_file_path(path, must_exist=True):
    """Validate file path to prevent path traversal attacks."""
    if not path:
        return None
    
    # Check for path traversal attempts
    if '..' in path or path.startswith('/') or path.startswith('\\'):
        raise ValueError(f"Invalid file path: potential path traversal detected")
    
    # Normalize and validate
    abs_path = os.path.abspath(path)
    
    if must_exist and not os.path.isfile(abs_path):
        return None
    
    return abs_path


def is_safe_fragment_path(path, base_url=None):
    """Validate fragment path to prevent path traversal and injection."""
    if not path or not isinstance(path, str):
        return False, "Fragment path is empty or invalid"
    
    # Length limit
    if len(path) > 4096:
        return False, "Fragment path too long"
    
    # Check for path traversal
    if '..' in path:
        return False, "Path traversal detected in fragment"
    
    # Check for dangerous characters
    dangerous_patterns = [
        r'[;\|&`$]',           # Shell metacharacters
        r'[\x00-\x1f\x7f]',    # Control characters
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, path):
            return False, f"Fragment path contains dangerous characters"
    
    # If it's a full URL, validate it
    if path.startswith('http://') or path.startswith('https://'):
        return is_safe_url(path)
    
    # If base_url is provided, validate the combined URL
    if base_url:
        full_url = base_url.rstrip('/') + '/' + path.lstrip('/')
        return is_safe_url(full_url)
    
    return True, None


# === MAIN EXECUTION ===

if len(sys.argv) < 2:
    print(json.dumps({"error": "No URL provided"}))
    sys.exit(1)

# Validate and sanitize all inputs
try:
    url = sys.argv[1]
    url_valid, url_error = is_safe_url(url)
    if not url_valid:
        print(json.dumps({"error": f"Security: {url_error}"}))
        sys.exit(1)
    
    profile = validate_profile(sys.argv[2] if len(sys.argv) > 2 else "BALANCED")
    cookies_file = sanitize_string_arg(sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None, "cookies_file", 1024)
    cookies_string = sanitize_string_arg(sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else "", "cookies_string", 8192)
    proxy_url = sanitize_string_arg(sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None, "proxy_url", 512)
    user_agent = sanitize_string_arg(sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else None, "user_agent", 512)
    
    # Parse large download configuration if provided
    if len(sys.argv) > 7 and sys.argv[7]:
        try:
            config_override = json.loads(sys.argv[7])
            LARGE_CONFIG.update(config_override)
        except json.JSONDecodeError:
            pass  # Use defaults if parsing fails
    
    # Validate proxy URL if provided
    if proxy_url:
        proxy_valid, proxy_error = is_safe_url(proxy_url.replace("socks5://", "http://").replace("socks4://", "http://"))
        if not proxy_valid and "scheme" not in (proxy_error or ""):
            print(json.dumps({"error": f"Security: Invalid proxy URL - {proxy_error}"}))
            sys.exit(1)

except ValueError as e:
    print(json.dumps({"error": f"Security: {e}"}))
    sys.exit(1)

# Extraction timeout from config
extraction_timeout = LARGE_CONFIG.get("extractionTimeout", 300)

# Check if this looks like a playlist URL
is_playlist_url = any(pattern in url.lower() for pattern in [
    'list=', '/playlist/', '/album/', '/channel/', '/user/', '/c/', '/sets/', '/@'
])

# Get playlist context from config
is_playlist_context = LARGE_CONFIG.get("isPlaylistContext", False)

cmd = [
    "yt-dlp",
    "-J",
    "--no-warnings",
    "--socket-timeout", "60",           # Increased for large files
    "--extractor-retries", "5",         # More retries for reliability
    "--ignore-errors",
    "--no-exec",           # Prevent execution of external commands
    "--no-batch-file",     # Prevent reading batch files
    "--no-download",       # Ensure we're only extracting info
]

# Only use --flat-playlist for actual playlist URLs to speed up extraction
# For single videos, we need full format info
if is_playlist_url or is_playlist_context:
    cmd.extend([
        "--yes-playlist",
        "--flat-playlist",              # Faster playlist extraction
    ])
else:
    cmd.extend([
        "--no-playlist",                # Extract single video only
    ])

cmd.extend([
    "--no-check-formats",               # Skip format availability check for speed
    url
])

# Add cookie support for authenticated downloads
if cookies_file:
    try:
        validated_cookies = validate_file_path(cookies_file, must_exist=True)
        if validated_cookies:
            cmd.insert(1, "--cookies")
            cmd.insert(2, validated_cookies)
    except ValueError as e:
        print(json.dumps({"error": f"Security: Cookies file - {e}"}))
        sys.exit(1)

# Add proxy support
if proxy_url:
    cmd.insert(1, "--proxy")
    cmd.insert(2, proxy_url)

# Add user agent if provided
if user_agent:
    cmd.insert(1, "--user-agent")
    cmd.insert(2, user_agent)

try:
    # Use explicit arguments to prevent shell injection
    # Increased timeout for large downloads
    proc = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        timeout=extraction_timeout,
        shell=False,  # CRITICAL: Never use shell=True
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}  # Controlled environment
    )
except subprocess.TimeoutExpired:
    print(json.dumps({"error": f"Extraction timed out after {extraction_timeout} seconds. Try a more specific URL."}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"error": f"Failed to run yt-dlp: {e}"}))
    sys.exit(1)

if proc.returncode != 0:
    # Sanitize error output before returning
    stderr = proc.stderr[:2000] if proc.stderr else "Unknown error"
    stderr = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', stderr)  # Remove control chars
    print(json.dumps({"error": stderr}))
    sys.exit(1)

# Limit output size to prevent memory exhaustion (configurable)
MAX_OUTPUT_SIZE = LARGE_CONFIG.get("maxOutputSize", 50 * 1024 * 1024)
if len(proc.stdout) > MAX_OUTPUT_SIZE:
    print(json.dumps({"error": "Output too large - possible malicious response"}))
    sys.exit(1)

try:
    info = json.loads(proc.stdout)
except json.JSONDecodeError as e:
    print(json.dumps({"error": f"Failed to parse yt-dlp output: {e}"}))
    sys.exit(1)


# Language preference mapping (higher = better for user)
LANGUAGE_PREFERENCE = {
    "en": 100, "en-US": 100, "en-GB": 95,
    "es": 80, "fr": 75, "de": 70, "it": 65,
    "pt": 60, "ru": 55, "ja": 50, "ko": 45, "zh": 40
}


def sanitize_url_output(url_str):
    """Sanitize URLs in output to prevent XSS/injection when displayed."""
    if not url_str or not isinstance(url_str, str):
        return None
    # Only allow http/https URLs
    if not url_str.startswith(('http://', 'https://')):
        return None
    # Remove any javascript: or data: attempts
    if 'javascript:' in url_str.lower() or 'data:' in url_str.lower():
        return None
    return url_str[:8192]  # Increased limit for long URLs with tokens


def sanitize_text_output(text, max_length=1024):
    """Sanitize text output to prevent injection."""
    if not text or not isinstance(text, str):
        return text
    # Remove control characters except newlines/tabs
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return sanitized[:max_length]


def is_format_usable(f):
    """Filter out unusable formats."""
    # Skip DRM-protected
    if f.get("has_drm"):
        return False
    # Skip premium/subscriber-only
    if f.get("is_premium") or "premium" in f.get("format_note", "").lower():
        return False
    # Skip storyboard/images
    if f.get("vcodec") == "none" and f.get("acodec") == "none":
        return False
    # Skip formats without URL
    if not f.get("url"):
        return False
    # Security: Validate format URL
    if not sanitize_url_output(f.get("url")):
        return False
    return True


def get_codec_preference(f):
    """Prefer widely compatible codecs."""
    vcodec = (f.get("vcodec") or "").lower()
    acodec = (f.get("acodec") or "").lower()
    
    score = 0
    # H.264 > VP9 > AV1 (compatibility order)
    if "avc" in vcodec or "h264" in vcodec:
        score += 50
    elif "vp9" in vcodec or "vp09" in vcodec:
        score += 30
    elif "av01" in vcodec or "av1" in vcodec:
        score += 10
    
    # AAC > Opus > Vorbis
    if "mp4a" in acodec or "aac" in acodec:
        score += 20
    elif "opus" in acodec:
        score += 15
    elif "vorbis" in acodec:
        score += 10
    
    return score


def get_language_preference(f):
    """Get language preference score."""
    lang = f.get("language") or ""
    return LANGUAGE_PREFERENCE.get(lang, LANGUAGE_PREFERENCE.get(lang.split("-")[0], 0))


def get_protocol(f):
    """Determine FDM-compatible protocol string."""
    proto = f.get("protocol", "https")
    if proto.startswith("m3u8"):
        return "m3u8_native"
    if proto.startswith("http_dash") or f.get("fragments"):
        return "http_dash_segments"
    if proto == "http":
        return "http"
    return "https"


def get_container(f, proto, ext):
    """Determine container format for DASH/segmented streams."""
    if proto == "http_dash_segments":
        container = f.get("container")
        if container:
            return container
        # Infer from extension
        if ext in ("mp4", "m4v", "m4a"):
            return f"{ext}_dash"
        if ext in ("webm", "weba"):
            return f"{ext}_dash"
        return f"{ext}_dash"
    return None


def format_filesize(size_bytes):
    """Format file size for display."""
    if not size_bytes:
        return None
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes} bytes"


def score_format(f):
    """Higher score = better choice."""
    tbr = f.get("tbr") or 0
    height = f.get("height") or 0
    filesize = f.get("filesize") or f.get("filesize_approx") or 0
    proto = f.get("protocol", "")
    is_dash = proto.startswith("http_dash") or f.get("fragments")
    is_hls = proto.startswith("m3u8")
    has_video = f.get("vcodec", "none") != "none"
    has_audio = f.get("acodec", "none") != "none"
    codec_pref = get_codec_preference(f)
    lang_pref = get_language_preference(f)
    preference = f.get("preference") or 0

    score = preference * 10  # Use yt-dlp's preference as base

    if profile == "FASTEST":
        score += 1000 if (has_video and has_audio) else 0
        score += tbr * 2
        score += codec_pref * 2
        score += lang_pref
        score -= filesize / 1_000_000 if filesize else 0
        score -= 500 if (is_dash or is_hls) else 0
        # Prefer direct HTTP downloads
        score += 200 if proto in ("http", "https") else 0

    elif profile == "BALANCED":
        score += 500 if (has_video and has_audio) else 0
        score += tbr
        score += height * 0.5
        score += codec_pref
        score += lang_pref * 0.5
        score -= 300 if is_hls else 0

    elif profile == "QUALITY":
        score += height * 3
        score += tbr
        score += codec_pref * 0.5
        score += lang_pref * 0.3
        score += 200 if (has_video and has_audio) else 0
        # For quality, DASH is acceptable
        score -= 100 if is_hls else 0

    return score


def build_format(f, entry_info, format_index):
    """Build FDM-compatible format object with security sanitization."""
    proto = get_protocol(f)
    ext = f.get("ext", "mp4")
    vcodec = f.get("vcodec") or "none"
    acodec = f.get("acodec") or "none"
    has_video = vcodec != "none"
    has_audio = acodec != "none"

    # Sanitize URL
    format_url = sanitize_url_output(f["url"])
    if not format_url:
        return None

    # Build HTTP headers with sanitization
    http_headers = {
        "User-Agent": sanitize_text_output(user_agent or entry_info.get("http_headers", {}).get("User-Agent", ""), 512),
        "Referer": sanitize_url_output(entry_info.get("webpage_url", "")) or "",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-us,en;q=0.5"
    }
    
    # Merge any format-specific headers (sanitized)
    fmt_headers = f.get("http_headers") or {}
    for k, v in fmt_headers.items():
        if isinstance(k, str) and isinstance(v, str):
            http_headers[sanitize_text_output(k, 64)] = sanitize_text_output(v, 512)

    filesize = f.get("filesize") or f.get("filesize_approx")
    
    fmt = {
        "url": format_url,
        "protocol": proto,
        "ext": sanitize_text_output(ext, 16),
        "quality": f.get("height") or f.get("abr") or 0,
        "tbr": f.get("tbr"),
        "filesize": filesize,
        "vcodec": sanitize_text_output(vcodec, 64),
        "acodec": sanitize_text_output(acodec, 64),
        "fps": f.get("fps"),
        "height": f.get("height"),
        "width": f.get("width"),
        "abr": f.get("abr"),
        "httpHeaders": http_headers,
        "preference": f.get("preference") or (100 - format_index),
    }

    # Add large download hints
    if filesize and filesize > 1024 * 1024 * 1024:  # > 1GB
        fmt["_largeDownload"] = True
        fmt["_filesizeFormatted"] = format_filesize(filesize)
        fmt["_suggestedChunkSize"] = LARGE_CONFIG.get("chunkSize", 10 * 1024 * 1024)
        # Hint for resumable downloads
        http_headers["Accept-Ranges"] = "bytes"

    if has_audio:
        lang = f.get("language")
        if lang:
            fmt["language"] = sanitize_text_output(lang, 16)
            fmt["languagePreference"] = get_language_preference(f)

    if cookies_string:
        fmt["cookies"] = sanitize_text_output(cookies_string, 8192)

    if has_video:
        fmt["video_ext"] = sanitize_text_output(ext, 16)
    if has_audio and not has_video:
        fmt["audio_ext"] = sanitize_text_output(ext, 16)

    container = get_container(f, proto, ext)
    if container:
        fmt["container"] = sanitize_text_output(container, 32)

    if proto == "m3u8_native":
        manifest = sanitize_url_output(f.get("manifest_url") or f["url"])
        if manifest:
            fmt["manifestUrl"] = manifest

    # Handle fragments with increased limit for large downloads
    max_fragments = LARGE_CONFIG.get("maxFragments", 10000)
    if f.get("fragments"):
        base_url = sanitize_url_output(f.get("fragment_base_url", "")) or ""
        fragments = []
        total_fragments = len(f["fragments"])
        skipped_fragments = 0
        
        for frag in f["fragments"][:max_fragments]:
            frag_url = frag.get("url", "")
            frag_path = frag.get("path", "")
            if frag_url and base_url and frag_url.startswith(base_url):
                frag_path = frag_url[len(base_url):]
            elif frag_url and not frag_path:
                frag_path = frag_url
            
            if frag_path:
                # Validate fragment path
                path_valid, path_error = is_safe_fragment_path(frag_path, base_url)
                if not path_valid:
                    skipped_fragments += 1
                    continue
                
                frag_entry = {"path": sanitize_text_output(frag_path, 2048)}
                # Include fragment duration if available (helps with large files)
                if frag.get("duration"):
                    frag_entry["duration"] = frag["duration"]
                fragments.append(frag_entry)
        
        if base_url:
            fmt["fragment_base_url"] = base_url
        if fragments:
            fmt["fragments"] = fragments
            fmt["_fragmentCount"] = total_fragments
            fmt["_fragmentsSkipped"] = skipped_fragments
            fmt["_multiFragment"] = total_fragments > 100

    return {k: v for k, v in fmt.items() if v is not None}


def process_single_entry(entry):
    """Process a single video entry."""
    formats = []
    for f in entry.get("formats", []):
        if not is_format_usable(f):
            continue
        f["_score"] = score_format(f)
        formats.append(f)

    formats.sort(key=lambda x: x["_score"], reverse=True)
    
    # Use configurable max formats
    max_formats = LARGE_CONFIG.get("maxFormats", 50)
    formats = formats[:max_formats]

    fdm_formats = []
    for i, f in enumerate(formats):
        built = build_format(f, entry, i)
        if built:
            fdm_formats.append(built)

    # Include best audio-only tracks
    audio_formats = [f for f in entry.get("formats", []) 
                     if is_format_usable(f)
                     and f.get("acodec", "none") != "none" 
                     and f.get("vcodec", "none") == "none"]
    if audio_formats:
        audio_formats.sort(
            key=lambda x: (x.get("abr") or 0) + get_codec_preference(x) + get_language_preference(x), 
            reverse=True
        )
        for i, af in enumerate(audio_formats[:5]):  # Increased audio options
            audio_fmt = build_format(af, entry, len(fdm_formats) + i)
            if audio_fmt and not any(f["url"] == audio_fmt["url"] for f in fdm_formats):
                fdm_formats.append(audio_fmt)

    result = {
        "id": sanitize_text_output(entry.get("id"), 128),
        "title": sanitize_text_output(entry.get("title", "Media"), 512),
        "webpage_url": sanitize_url_output(entry.get("webpage_url")),
        "duration": entry.get("duration"),
        "upload_date": sanitize_text_output(entry.get("upload_date"), 32),
        "formats": fdm_formats
    }

    # Subtitles (increased limit)
    subs = entry.get("subtitles") or entry.get("automatic_captions") or {}
    if subs:
        result["subtitles"] = {}
        for lang, arr in list(subs.items())[:100]:  # Increased limit
            if not arr:
                continue
            sorted_subs = sorted(arr, key=lambda s: (
                2 if s.get("ext") == "vtt" else (1 if s.get("ext") == "srt" else 0)
            ), reverse=True)
            sub = sorted_subs[0]
            sub_url = sanitize_url_output(sub.get("url"))
            if sub_url:
                sub_entry = {
                    "name": sanitize_text_output(sub.get("name") or lang.upper(), 64),
                    "url": sub_url,
                    "ext": sanitize_text_output(sub.get("ext", "vtt"), 16)
                }
                sub_proto = sub.get("protocol", "")
                if sub_proto.startswith("m3u8"):
                    sub_entry["protocol"] = "m3u8_native"
                result["subtitles"][sanitize_text_output(lang, 16)] = [sub_entry]

    # Thumbnails
    thumbs = entry.get("thumbnails") or []
    if thumbs:
        sorted_thumbs = sorted(thumbs, key=lambda t: (t.get("height") or 0) * (t.get("width") or 0))
        result["thumbnails"] = []
        for i, t in enumerate(sorted_thumbs[:20]):
            thumb_url = sanitize_url_output(t.get("url"))
            if thumb_url:
                result["thumbnails"].append({
                    "url": thumb_url,
                    "height": t.get("height"),
                    "width": t.get("width"),
                    "preference": i
                })

    return result


# Handle playlists vs single videos
max_playlist_entries = LARGE_CONFIG.get("maxPlaylistEntries", 500)

if info.get("_type") == "playlist" and info.get("entries"):
    entries = [e for e in info["entries"] if e][:max_playlist_entries]
    output = {
        "_type": "playlist",
        "id": sanitize_text_output(info.get("id"), 128),
        "title": sanitize_text_output(info.get("title", "Playlist"), 512),
        "webpage_url": sanitize_url_output(info.get("webpage_url")),
        "entries": [],
        "_totalEntries": len(info["entries"]),  # Track total for large playlists
        "_entriesIncluded": len(entries)
    }
    
    for e in entries:
        entry_url = sanitize_url_output(e.get("webpage_url") or e.get("url"))
        if entry_url:
            entry_data = {
                "_type": "url",
                "url": entry_url,
                "title": sanitize_text_output(e.get("title", "Media"), 512),
                "duration": e.get("duration")
            }
            # Include filesize hint if available
            if e.get("filesize"):
                entry_data["_filesize"] = e["filesize"]
                entry_data["_filesizeFormatted"] = format_filesize(e["filesize"])
            output["entries"].append(entry_data)
    
    thumbs = info.get("thumbnails") or []
    if thumbs:
        sorted_thumbs = sorted(thumbs, key=lambda t: (t.get("height") or 0) * (t.get("width") or 0))
        output["thumbnails"] = []
        for i, t in enumerate(sorted_thumbs[:10]):
            thumb_url = sanitize_url_output(t.get("url"))
            if thumb_url:
                output["thumbnails"].append({
                    "url": thumb_url,
                    "height": t.get("height"),
                    "width": t.get("width"),
                    "preference": i
                })
else:
    output = process_single_entry(info)

print(json.dumps(output))
