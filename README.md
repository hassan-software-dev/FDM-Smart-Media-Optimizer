# FDM Smart Media Optimizer

[![FDM Plugin](https://img.shields.io/badge/FDM-Plugin-blue)](https://www.freedownloadmanager.org/)
[![API Version](https://img.shields.io/badge/API-v9-green)](https://www.freedownloadmanager.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-yellow)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/hassan-software-dev/fdm-smart-media-optimizer?style=social)](https://github.com/hassan-software-dev/fdm-smart-media-optimizer)

A powerful Free Download Manager plugin that enables smart media extraction from popular video and audio platforms using yt-dlp. Optimized for large downloads (20GB+) with resume capability.

---

## 📋 Table of Contents

- [Features](#-features)
- [Supported Platforms](#-supported-platforms)
- [Requirements](#-requirements)
- [Installation](#-installation)
  - [Method 1: Install from FDA File](#method-1-install-from-fda-file-recommended)
  - [Method 2: Manual Installation](#method-2-manual-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Security](#-security)
- [For Developers](#-for-developers)
- [FAQ](#-faq)
- [Changelog](#-changelog)
- [License](#-license)

---

## ✨ Features

### Core Features
- **Multi-Platform Support**: Download from 18+ popular platforms including YouTube, Vimeo, Twitter/X, TikTok, and more
- **Smart Format Selection**: Automatically selects the best format based on your preference (Quality, Balanced, or Fastest)
- **Playlist Support**: Download entire playlists, channels, and albums with a single click
- **Large File Support**: Optimized for files up to 20GB+ with chunked downloading
- **Resume Capability**: Resume interrupted downloads seamlessly

### Quality Options
- **QUALITY Mode**: Prioritizes highest resolution and bitrate
- **BALANCED Mode**: Best compromise between quality and download speed (default)
- **FASTEST Mode**: Prioritizes combined audio+video formats for quick downloads

### Additional Features
- 🔐 **Secure**: Comprehensive input validation and SSRF protection
- 🍪 **Cookie Support**: Use browser cookies for authenticated downloads
- 🌐 **Proxy Support**: Works with your system proxy settings
- 📝 **Subtitles**: Automatic subtitle extraction (VTT, SRT)
- 🖼️ **Thumbnails**: Extracts video thumbnails
- 🔄 **Auto-Install**: Automatically installs yt-dlp if not present

---

## 🌐 Supported Platforms

| Platform | Single Videos | Playlists | Notes |
|----------|:-------------:|:---------:|-------|
| YouTube | ✅ | ✅ | Channels, playlists, single videos |
| Vimeo | ✅ | ✅ | |
| Dailymotion | ✅ | ✅ | |
| Twitch | ✅ | ✅ | VODs and clips |
| Facebook | ✅ | ✅ | Public videos |
| Instagram | ✅ | ❌ | Reels, posts |
| Twitter/X | ✅ | ❌ | |
| TikTok | ✅ | ❌ | |
| Reddit | ✅ | ❌ | Video posts |
| SoundCloud | ✅ | ✅ | Sets/playlists |
| Bandcamp | ✅ | ✅ | Albums |
| Bilibili | ✅ | ✅ | |
| Niconico | ✅ | ✅ | |
| Crunchyroll | ✅ | ✅ | May require login |
| Funimation | ✅ | ✅ | May require login |

> **Note**: Some platforms may require authentication via browser cookies for certain content.

---

## 📦 Requirements

### System Requirements
- **Free Download Manager**: Version 6.16 or higher
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux
- **Python**: Version 3.8 or higher (FDM can install this automatically)
- **Internet Connection**: Required for downloading and yt-dlp installation

### Automatic Dependencies
The plugin will automatically install the following if not present:
- **yt-dlp**: Latest version via pip

---

## 📥 Installation

### Method 1: Install from FDA File (Recommended)

1. **Download the Plugin**
   - Download the latest `fdm-smart-media-optimizer.fda` file from the [Releases](https://github.com/hassan-software-dev/fdm-smart-media-optimizer/releases) page

2. **Install in FDM**
   - Open Free Download Manager
   - Go to **Menu** → **Add-ons** (or press `Ctrl+Shift+A`)
   - Click **Install add-on from file...**
   - Select the downloaded `.fda` file
   - Click **Install**

3. **Grant Permissions**
   - When prompted, allow the plugin to run Python scripts
   - This is required for yt-dlp to function

4. **Verify Installation**
   - The plugin should appear in your add-ons list
   - Try downloading a YouTube video to confirm it works

### Method 2: Manual Installation

1. **Clone or Download the Repository**
   ```bash
   git clone https://github.com/hassan-software-dev/fdm-smart-media-optimizer.git
   ```

2. **Locate FDM Plugins Folder**
   - **Windows**: `%APPDATA%\FDM\plugins\`
   - **macOS**: `~/Library/Application Support/FDM/plugins/`
   - **Linux**: `~/.fdm/plugins/`

3. **Copy Plugin Files**
   - Create a folder named `fdm-smart-media-optimizer` in the plugins directory
   - Copy all files from the repository into this folder

4. **Restart FDM**
   - Close and reopen Free Download Manager
   - The plugin should now be active

---

## 🚀 Usage

### Downloading a Single Video

1. **Copy the Video URL**
   - Copy any supported video URL from your browser

2. **Paste in FDM**
   - Open FDM and press `Ctrl+V` or click **+** → **Add Download**
   - Paste the URL

3. **Select Format**
   - FDM will show available formats (quality options)
   - Select your preferred quality
   - Click **Download**

### Downloading a Playlist

1. **Copy the Playlist URL**
   - For YouTube: Copy the URL containing `list=`
   - For other platforms: Copy the playlist/album page URL

2. **Add to FDM**
   - Paste the URL in FDM
   - FDM will detect it as a playlist

3. **Select Videos**
   - Choose which videos to download
   - Select quality for each or use batch settings
   - Click **Download All**

### Using Browser Cookies (For Authenticated Content)

Some content requires you to be logged in. To download such content:

1. **Enable Cookie Sharing in FDM**
   - Go to FDM **Settings** → **Integration** → **Web browsers**
   - Ensure your browser integration is enabled

2. **Log in to the Website**
   - Log in to the platform in your browser

3. **Download**
   - The plugin will automatically use your browser's cookies

---

## ⚙️ Configuration

### Speed Profiles

Edit `media_parser.js` to change the default profile:

```javascript
var SPEED_PROFILE = "BALANCED"; // Options: "FASTEST" | "BALANCED" | "QUALITY"
```

| Profile | Best For | Behavior |
|---------|----------|----------|
| `FASTEST` | Quick downloads | Prefers combined formats, smaller files |
| `BALANCED` | General use | Good quality with reasonable speed |
| `QUALITY` | Best quality | Highest resolution and bitrate |

### Large Download Settings

For users frequently downloading large files (10GB+), you can adjust these settings in `media_parser.js`:

```javascript
var LARGE_DOWNLOAD_CONFIG = {
  maxOutputSize: 50 * 1024 * 1024,    // Max metadata size (50MB)
  extractionTimeout: 300,              // Extraction timeout in seconds (5 min)
  maxFormats: 50,                      // Maximum format options shown
  maxFragments: 10000,                 // Max fragments for segmented media
  maxPlaylistEntries: 500,             // Max videos per playlist
  chunkSize: 10 * 1024 * 1024          // Download chunk size (10MB)
};
```

---

## 🔧 Troubleshooting

### Common Issues

#### "yt-dlp not found" Error

**Solution**: The plugin should auto-install yt-dlp, but if it fails:

1. Open Command Prompt/Terminal
2. Run:
   ```bash
   pip install yt-dlp
   ```
3. Restart FDM

#### "Python not found" Error

**Solution**: 
1. Go to FDM **Settings** → **Add-ons**
2. Click on this plugin → **Install Python**
3. Or manually install Python 3.8+ from [python.org](https://www.python.org/downloads/)

#### Downloads Stuck at 0%

**Possible Causes**:
- Video might be geo-restricted
- Content might require authentication
- Platform might have changed their API

**Solutions**:
1. Try using browser cookies (see [Usage](#using-browser-cookies-for-authenticated-content))
2. Update yt-dlp: `pip install --upgrade yt-dlp`
3. Check if the video plays in your browser

#### "Extraction timed out" Error

**Solution**: 
- For large playlists, try downloading smaller batches
- Check your internet connection
- Increase timeout in `LARGE_DOWNLOAD_CONFIG.extractionTimeout`

#### Plugin Not Appearing in FDM

**Solutions**:
1. Verify FDM version is 6.16 or higher
2. Check that all files are in the correct location
3. Ensure `manifest.json` is valid JSON
4. Restart FDM completely

### Debug Mode

To enable detailed logging:

1. Open FDM
2. Go to **Help** → **Show Debug Log**
3. Try downloading again
4. Check the log for errors

---

## 🔒 Security

This plugin implements multiple security measures:

### Input Validation
- ✅ URL length limits (max 4096 characters)
- ✅ Protocol validation (HTTP/HTTPS only)
- ✅ Shell metacharacter blocking
- ✅ Path traversal prevention
- ✅ Control character filtering

### Network Security
- ✅ SSRF protection (blocks localhost, private IPs)
- ✅ No shell execution (`shell=False` in subprocess)
- ✅ Proxy URL validation
- ✅ Cookie sanitization

### Resource Limits
- ✅ Maximum output size limits
- ✅ Extraction timeouts
- ✅ Fragment count limits
- ✅ Cookie count limits

### What This Plugin Does NOT Do
- ❌ Execute arbitrary code from URLs
- ❌ Access local/private network resources
- ❌ Store or transmit your cookies externally
- ❌ Modify system files outside temp directory

---

## 👨‍💻 For Developers

### Project Structure

```
fdm-smart-media-optimizer/
├── manifest.json           # Plugin metadata and configuration
├── media_parser.js         # Main JavaScript plugin logic
├── icon.png               # Plugin icon
├── README.md              # This file
├── python/
│   ├── check_dependencies.py   # yt-dlp installation manager
│   └── extractor.py           # Media extraction logic
└── signature.dat          # Plugin signature (for signed releases)
```

### API Compliance

This plugin is built for **FDM Plugin API v9** with:
- `minApiVersion`: 8
- `minFeaturesLevel`: 2
- `targetApiVersion`: 9

### Building from Source

1. **Clone the repository**
   ```bash
   git clone https://github.com/hassan-software-dev/fdm-smart-media-optimizer.git
   cd fdm-smart-media-optimizer
   ```

2. **Create FDA package**
   ```bash
   # On Windows (PowerShell)
   Compress-Archive -Path * -DestinationPath fdm-smart-media-optimizer.zip
   Rename-Item fdm-smart-media-optimizer.zip fdm-smart-media-optimizer.fda
   
   # On Linux/macOS
   zip -r fdm-smart-media-optimizer.fda . -x "*.git*"
   ```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- JavaScript: ES5 compatible (for Qt JavaScript engine)
- Python: Python 3.8+ with type hints where helpful
- Use descriptive variable names
- Add comments for complex logic

---

## ❓ FAQ

### Q: Is this plugin safe to use?
**A**: Yes. The plugin includes comprehensive security measures and only processes URLs you explicitly provide. It doesn't execute arbitrary code or access local network resources.

### Q: Will this plugin work with any website?
**A**: The plugin supports websites that yt-dlp supports. Check the [yt-dlp supported sites list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) for full compatibility.

### Q: Does this bypass DRM or paywalls?
**A**: No. This plugin respects DRM protection and filters out DRM-protected formats. It cannot download paid/premium content you don't have access to.

### Q: My antivirus flags this plugin. Why?
**A**: Some antivirus software may flag plugins that execute Python scripts. This is a false positive. The plugin only runs yt-dlp for media extraction.

### Q: How do I update yt-dlp?
**A**: Run this command in your terminal:
```bash
pip install --upgrade yt-dlp
```

### Q: Can I download private/unlisted videos?
**A**: Yes, if you have access to them. Use browser cookies (see [Usage](#using-browser-cookies-for-authenticated-content)) to authenticate.

---

## 📝 Changelog

### Version 1.1.1 (Current)
- Added comprehensive security validation
- Improved large download support (20GB+)
- Added fragment path validation
- Better temporary file cleanup
- Fallback cleanup timeout for cancelled downloads

### Version 1.1.0
- Added automatic yt-dlp installation
- Playlist support improvements
- Cookie handling enhancements
- Proxy support

### Version 1.0.0
- Initial release
- Basic media extraction
- Multi-platform support

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Free Download Manager](https://www.freedownloadmanager.org/) - For the excellent download manager and plugin API
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - For the powerful media extraction library
- The open-source community for testing and feedback

---

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/hassan-software-dev/fdm-smart-media-optimizer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/hassan-software-dev/fdm-smart-media-optimizer/discussions)
- **FDM Forum**: [FDM Community Forum](https://www.freedownloadmanager.org/board/)

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/hassan-software-dev">Hassan Shahid</a> for the FDM Community
</p>
