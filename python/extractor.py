import sys, json, subprocess, os

url = sys.argv[1]
profile = sys.argv[2]  # FASTEST | BALANCED | QUALITY
cookies_file = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
cookies_string = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else ""
proxy_url = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
user_agent = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else None

cmd = [
    "yt-dlp",
    "-J",
    "--no-warnings",
    "--yes-playlist",
    "--socket-timeout", "30",
    "--extractor-retries", "3",
    "--ignore-errors",
    url
]

# Add cookie support for authenticated downloads
if cookies_file and os.path.isfile(cookies_file):
    cmd.insert(1, "--cookies")
    cmd.insert(2, cookies_file)

# Add proxy support
if proxy_url:
    cmd.insert(1, "--proxy")
    cmd.insert(2, proxy_url)

# Add user agent if provided
if user_agent:
    cmd.insert(1, "--user-agent")
    cmd.insert(2, user_agent)

try:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
except subprocess.TimeoutExpired:
    print(json.dumps({"error": "Extraction timed out after 120 seconds"}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"error": f"Failed to run yt-dlp: {e}"}))
    sys.exit(1)

if proc.returncode != 0:
    print(json.dumps({"error": proc.stderr}))
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
    """Build FDM-compatible format object."""
    proto = get_protocol(f)
    ext = f.get("ext", "mp4")
    vcodec = f.get("vcodec") or "none"
    acodec = f.get("acodec") or "none"
    has_video = vcodec != "none"
    has_audio = acodec != "none"

    # Build HTTP headers
    http_headers = {
        "User-Agent": user_agent or entry_info.get("http_headers", {}).get("User-Agent", ""),
        "Referer": entry_info.get("webpage_url", ""),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-us,en;q=0.5"
    }
    
    # Merge any format-specific headers
    fmt_headers = f.get("http_headers") or {}
    http_headers.update(fmt_headers)

    fmt = {
        "url": f["url"],
        "protocol": proto,
        "ext": ext,
        "quality": f.get("height") or f.get("abr") or 0,
        "tbr": f.get("tbr"),
        "filesize": f.get("filesize") or f.get("filesize_approx"),
        "vcodec": vcodec,
        "acodec": acodec,
        "fps": f.get("fps"),
        "height": f.get("height"),
        "width": f.get("width"),
        "abr": f.get("abr"),
        "httpHeaders": http_headers,
        "preference": f.get("preference") or (100 - format_index),  # FDM preference field
    }

    # Add language fields for audio
    if has_audio:
        lang = f.get("language")
        if lang:
            fmt["language"] = lang
            fmt["languagePreference"] = get_language_preference(f)

    # Add cookies string if available
    if cookies_string:
        fmt["cookies"] = cookies_string

    # Mandatory fields per FDM spec
    if has_video:
        fmt["video_ext"] = ext
    if has_audio and not has_video:
        fmt["audio_ext"] = ext

    # Container is mandatory for DASH
    container = get_container(f, proto, ext)
    if container:
        fmt["container"] = container

    # HLS needs manifestUrl
    if proto == "m3u8_native":
        fmt["manifestUrl"] = f.get("manifest_url") or f["url"]

    # Handle fragments
    if f.get("fragments"):
        base_url = f.get("fragment_base_url", "")
        fragments = []
        for frag in f["fragments"]:
            frag_url = frag.get("url", "")
            frag_path = frag.get("path", "")
            # If fragment has full URL, extract path relative to base
            if frag_url and base_url and frag_url.startswith(base_url):
                frag_path = frag_url[len(base_url):]
            elif frag_url and not frag_path:
                frag_path = frag_url
            fragments.append({"path": frag_path})
        
        if base_url:
            fmt["fragment_base_url"] = base_url
        fmt["fragments"] = fragments

    # Remove None values to keep output clean
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
    formats = formats[:12]

    fdm_formats = [build_format(f, entry, i) for i, f in enumerate(formats)]

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
        for i, af in enumerate(audio_formats[:3]):
            audio_fmt = build_format(af, entry, len(fdm_formats) + i)
            if not any(f["url"] == audio_fmt["url"] for f in fdm_formats):
                fdm_formats.append(audio_fmt)

    result = {
        "id": entry.get("id"),
        "title": entry.get("title", "Media"),
        "webpage_url": entry.get("webpage_url"),
        "duration": entry.get("duration"),
        "upload_date": entry.get("upload_date"),
        "formats": fdm_formats
    }

    # Subtitles - FDM format: {lang: [{name, url, ext, protocol?}]}
    subs = entry.get("subtitles") or entry.get("automatic_captions") or {}
    if subs:
        result["subtitles"] = {}
        for lang, arr in subs.items():
            if not arr:
                continue
            # Prefer vtt/srt over other formats
            sorted_subs = sorted(arr, key=lambda s: (
                2 if s.get("ext") == "vtt" else (1 if s.get("ext") == "srt" else 0)
            ), reverse=True)
            sub = sorted_subs[0]
            if sub.get("url"):
                sub_entry = {
                    "name": sub.get("name") or lang.upper(),
                    "url": sub["url"],
                    "ext": sub.get("ext", "vtt")
                }
                # API 8+: Add protocol for M3U8 subtitles
                sub_proto = sub.get("protocol", "")
                if sub_proto.startswith("m3u8"):
                    sub_entry["protocol"] = "m3u8_native"
                result["subtitles"][lang] = [sub_entry]

    # Thumbnails - sorted by quality (best last for preference)
    thumbs = entry.get("thumbnails") or []
    if thumbs:
        # Sort by resolution
        sorted_thumbs = sorted(thumbs, key=lambda t: (t.get("height") or 0) * (t.get("width") or 0))
        result["thumbnails"] = [{
            "url": t["url"],
            "height": t.get("height"),
            "width": t.get("width"),
            "preference": i
        } for i, t in enumerate(sorted_thumbs) if t.get("url")]

    return result


# Handle playlists vs single videos - FDM spec format
if info.get("_type") == "playlist" and info.get("entries"):
    entries = [e for e in info["entries"] if e]
    output = {
        "_type": "playlist",
        "id": info.get("id"),
        "title": info.get("title", "Playlist"),
        "webpage_url": info.get("webpage_url"),
        "entries": [{
            "_type": "url",
            "url": e.get("webpage_url") or e.get("url"),
            "title": e.get("title", "Media"),
            "duration": e.get("duration")
        } for e in entries[:50] if e.get("webpage_url") or e.get("url")]
    }
    # Add playlist thumbnails
    thumbs = info.get("thumbnails") or []
    if thumbs:
        sorted_thumbs = sorted(thumbs, key=lambda t: (t.get("height") or 0) * (t.get("width") or 0))
        output["thumbnails"] = [{
            "url": t["url"],
            "height": t.get("height"),
            "width": t.get("width"),
            "preference": i
        } for i, t in enumerate(sorted_thumbs) if t.get("url")]
else:
    output = process_single_entry(info)

print(json.dumps(output))
