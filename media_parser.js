var SPEED_PROFILE = "BALANCED"; // FASTEST | BALANCED | QUALITY

// Security: Maximum URL length to prevent buffer overflow attacks
var MAX_URL_LENGTH = 4096;

// Large download support configuration
var LARGE_DOWNLOAD_CONFIG = {
  maxOutputSize: 50 * 1024 * 1024,      // 50MB output limit (for files with many fragments)
  extractionTimeout: 300,                // 5 minutes for extraction (large playlists)
  maxFormats: 50,                        // More format options for large files
  maxFragments: 10000,                   // Support up to 10k fragments (for long/large content)
  maxPlaylistEntries: 500,               // Support larger playlists
  chunkSize: 10 * 1024 * 1024            // 10MB chunk size hint for FDM
};

// Dependency state tracking
var ytdlpState = {
  checked: false,
  installed: false,
  installing: false,
  version: null,
  lastCheckTime: 0
};

// Cache duration for yt-dlp check (5 minutes)
var YTDLP_CHECK_CACHE_MS = 5 * 60 * 1000;

// List of supported sites (yt-dlp supported sites)
var SUPPORTED_DOMAINS = [
  "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "twitch.tv",
  "facebook.com", "fb.watch", "instagram.com", "twitter.com", "x.com",
  "tiktok.com", "reddit.com", "soundcloud.com", "bandcamp.com",
  "bilibili.com", "nicovideo.jp", "crunchyroll.com", "funimation.com"
];

// Security: Blocked patterns that could indicate malicious intent
var BLOCKED_URL_PATTERNS = [
  /javascript:/i,
  /data:/i,
  /file:/i,
  /ftp:/i,
  /[;\|&`$]/,           // Shell metacharacters
  /\$\(/,               // Command substitution
  /[\x00-\x1f\x7f]/,    // Control characters
  /\.\.\/|\.\.\\|%2e%2e/i  // Path traversal
];

// Security: Patterns indicating local/private network access attempts
var PRIVATE_NETWORK_PATTERNS = [
  /^https?:\/\/localhost/i,
  /^https?:\/\/127\./,
  /^https?:\/\/10\./,
  /^https?:\/\/192\.168\./,
  /^https?:\/\/172\.(1[6-9]|2[0-9]|3[01])\./,
  /^https?:\/\/0\.0\.0\.0/,
  /^https?:\/\/\[::1\]/
];

/**
 * Validate URL for security threats
 * @returns {object} {valid: boolean, error: string|null, warning: string|null}
 */
function validateUrlSecurity(url) {
  if (!url || typeof url !== "string") {
    return { valid: false, error: "URL is empty or invalid" };
  }

  if (url.length > MAX_URL_LENGTH) {
    return { valid: false, error: "URL exceeds maximum length (" + MAX_URL_LENGTH + " chars)" };
  }

  // Check for blocked patterns
  for (var i = 0; i < BLOCKED_URL_PATTERNS.length; i++) {
    if (BLOCKED_URL_PATTERNS[i].test(url)) {
      return { 
        valid: false, 
        error: "SECURITY WARNING: URL contains potentially dangerous characters that could execute malicious code. Pattern detected: " + BLOCKED_URL_PATTERNS[i].toString()
      };
    }
  }

  // Check for private network access
  for (var j = 0; j < PRIVATE_NETWORK_PATTERNS.length; j++) {
    if (PRIVATE_NETWORK_PATTERNS[j].test(url)) {
      return { 
        valid: false, 
        error: "SECURITY WARNING: URL attempts to access local/private network resources. This could be a Server-Side Request Forgery (SSRF) attack trying to access internal services."
      };
    }
  }

  // Ensure URL starts with http:// or https://
  if (!/^https?:\/\//i.test(url)) {
    return { valid: false, error: "Only HTTP/HTTPS URLs are supported" };
  }

  return { valid: true, error: null };
}

/**
 * Sanitize string to prevent injection
 */
function sanitizeString(str, maxLength) {
  if (!str || typeof str !== "string") return "";
  // Remove control characters
  var sanitized = str.replace(/[\x00-\x1f\x7f]/g, "");
  return sanitized.substring(0, maxLength || 1024);
}

/**
 * Check if yt-dlp is installed
 * @returns {Promise} Resolves with {installed: boolean, version: string|null}
 */
function checkYtdlpInstalled(requestId, interactive) {
  return new Promise(function(resolve, reject) {
    // Use cached result if recent enough
    var now = Date.now();
    if (ytdlpState.checked && (now - ytdlpState.lastCheckTime) < YTDLP_CHECK_CACHE_MS) {
      resolve({
        installed: ytdlpState.installed,
        version: ytdlpState.version,
        cached: true
      });
      return;
    }

    launchPythonScript(
      requestId || 0,
      interactive || false,
      "python/check_dependencies.py",
      ["check"]
    ).then(function(res) {
      try {
        var result = JSON.parse(res.output);
        ytdlpState.checked = true;
        ytdlpState.installed = result.installed === true;
        ytdlpState.version = result.version || null;
        ytdlpState.lastCheckTime = Date.now();
        resolve({
          installed: ytdlpState.installed,
          version: ytdlpState.version,
          cached: false
        });
      } catch (e) {
        reject({ error: "Failed to check yt-dlp status: " + e.message });
      }
    }).catch(function(err) {
      reject({ error: "Dependency check failed: " + (err.error || "Unknown error") });
    });
  });
}

/**
 * Install yt-dlp via pip
 * @returns {Promise} Resolves with installation result
 */
function installYtdlp(requestId, interactive, upgrade) {
  return new Promise(function(resolve, reject) {
    if (ytdlpState.installing) {
      reject({ error: "yt-dlp installation already in progress. Please wait..." });
      return;
    }

    ytdlpState.installing = true;
    console.log("Installing yt-dlp" + (upgrade ? " (upgrade)" : "") + "...");

    var args = ["install"];
    if (upgrade) {
      args.push("--upgrade");
    }

    launchPythonScript(
      requestId || 0,
      interactive || true,  // Installation should be interactive
      "python/check_dependencies.py",
      args
    ).then(function(res) {
      ytdlpState.installing = false;
      try {
        var result = JSON.parse(res.output);
        if (result.success) {
          ytdlpState.installed = true;
          ytdlpState.version = result.version;
          ytdlpState.lastCheckTime = Date.now();
          console.log("yt-dlp installed successfully: " + result.version);
        }
        resolve(result);
      } catch (e) {
        reject({ error: "Failed to parse installation result: " + e.message });
      }
    }).catch(function(err) {
      ytdlpState.installing = false;
      reject({ 
        error: "yt-dlp installation failed: " + (err.error || "Unknown error") + 
               "\n\nPlease install yt-dlp manually by running:\n  pip install yt-dlp"
      });
    });
  });
}

/**
 * Ensure yt-dlp is available, installing if necessary
 * @returns {Promise}
 */
function ensureYtdlpAvailable(requestId, interactive) {
  return new Promise(function(resolve, reject) {
    checkYtdlpInstalled(requestId, interactive).then(function(checkResult) {
      if (checkResult.installed) {
        resolve(checkResult);
        return;
      }

      // yt-dlp not installed, attempt installation
      console.log("yt-dlp not found. Attempting automatic installation...");
      
      installYtdlp(requestId, interactive, false).then(function(installResult) {
        if (installResult.success) {
          resolve({
            installed: true,
            version: installResult.version,
            justInstalled: true
          });
        } else {
          reject({
            error: "DEPENDENCY MISSING: yt-dlp is required but could not be installed automatically.\n\n" +
                   "Error: " + (installResult.error || installResult.message || "Unknown error") + "\n\n" +
                   "Please install yt-dlp manually:\n" +
                   "  1. Open a command prompt/terminal\n" +
                   "  2. Run: pip install yt-dlp\n" +
                   "  3. Restart FDM and try again",
            isParseError: false,
            isDependencyError: true
          });
        }
      }).catch(function(installErr) {
        reject({
          error: "DEPENDENCY MISSING: yt-dlp is required but could not be installed.\n\n" +
                 (installErr.error || "Installation failed") + "\n\n" +
                 "Please install yt-dlp manually:\n" +
                 "  1. Open a command prompt/terminal\n" +
                 "  2. Run: pip install yt-dlp\n" +
                 "  3. Restart FDM and try again",
          isParseError: false,
          isDependencyError: true
        });
      });
    }).catch(function(checkErr) {
      reject({
        error: "Failed to check dependencies: " + (checkErr.error || "Unknown error"),
        isParseError: false
      });
    });
  });
}

var msParser = {
  isSupportedSource: function (url) {
    // Security check first
    var validation = validateUrlSecurity(url);
    if (!validation.valid) {
      console.warn("Security: " + validation.error);
      return false;
    }

    try {
      var hostname = url.match(/^https?:\/\/([^\/]+)/i);
      if (!hostname) return false;
      var domain = hostname[1].toLowerCase();
      for (var i = 0; i < SUPPORTED_DOMAINS.length; i++) {
        if (domain.indexOf(SUPPORTED_DOMAINS[i]) !== -1) {
          return true;
        }
      }
      return false;
    } catch (e) {
      return false;
    }
  },

  supportedSourceCheckPriority: function () {
    // Lower priority so site-specific plugins take precedence
    return 100;
  },

  isPossiblySupportedSource: function (obj) {
    // Security validation
    if (!validateUrlSecurity(obj.url).valid) {
      return false;
    }
    
    var ct = (obj.contentType || "").toLowerCase();
    // Include more content types for large downloads (games, archives)
    return ct.indexOf("video") !== -1 || 
           ct.indexOf("audio") !== -1 ||
           ct.indexOf("mpegurl") !== -1 ||
           ct.indexOf("application/octet-stream") !== -1 ||
           ct.indexOf("application/zip") !== -1 ||
           ct.indexOf("application/x-rar") !== -1;
  },

  minIntevalBetweenQueryInfoDownloads: function () {
    // 500ms minimum between requests to avoid rate limiting
    return 500;
  },

  overrideUrlPolicy: function (url) {
    // Allow all URLs this plugin handles
    return false;
  },

  parse: function (obj) {
    return new Promise(function (resolve, reject) {
      // Security: Validate URL before processing
      var validation = validateUrlSecurity(obj.url);
      if (!validation.valid) {
        reject({ 
          error: validation.error, 
          isParseError: true 
        });
        return;
      }

      // First ensure yt-dlp is available
      ensureYtdlpAvailable(obj.requestId, obj.interactive).then(function(ytdlpStatus) {
        if (ytdlpStatus.justInstalled) {
          console.log("yt-dlp was just installed (version " + ytdlpStatus.version + "). Proceeding with extraction...");
        }

        // Build cookies file if cookies exist
        var cookiesArg = "";
        var cookiesString = "";
        var tmpFile = null;
        
        // Check if plugin is allowed to use browser cookies
        var canUseCookies = true;
        try {
          if (typeof App !== "undefined" && App && App.pluginsAllowWbCookies === false) {
            canUseCookies = false;
          }
        } catch (e) {}

        if (canUseCookies && obj.cookies && obj.cookies.length > 0) {
          try {
            tmpFile = qtJsTools.createTmpFile("cookies.txt");
            var cookieLines = ["# Netscape HTTP Cookie File"];
            var cookiePairs = [];
            
            // Security: Limit number of cookies to prevent DoS
            var maxCookies = Math.min(obj.cookies.length, 100);
            
            for (var i = 0; i < maxCookies; i++) {
              var c = obj.cookies[i];
              // Sanitize cookie values
              var cookieName = sanitizeString(c.name, 256);
              var cookieValue = sanitizeString(c.value, 4096);
              var cookieDomain = sanitizeString(c.domain, 256);
              var cookiePath = sanitizeString(c.path, 256) || "/";
              
              if (!cookieName) continue;
              
              var secure = c.isSecure ? "TRUE" : "FALSE";
              var expiry = Math.floor(c.expirationDate || 0).toString();
              var subdomainFlag = cookieDomain.charAt(0) === "." ? "TRUE" : "FALSE";
              
              var line = [
                cookieDomain,
                subdomainFlag,
                cookiePath,
                secure,
                expiry,
                cookieName,
                cookieValue
              ].join("\t");
              cookieLines.push(line);
              
              var cookieEntry = cookieName + "=" + cookieValue;
              if (cookieDomain) cookieEntry += "; Domain=" + cookieDomain;
              if (cookiePath) cookieEntry += "; Path=" + cookiePath;
              if (c.isSecure) cookieEntry += "; Secure";
              if (c.expirationDate) cookieEntry += "; Expires=" + Math.floor(c.expirationDate);
              cookiePairs.push(cookieEntry);
            }
            
            tmpFile.writeText(cookieLines.join("\n"));
            cookiesArg = tmpFile.path();
            cookiesString = cookiePairs.join("; ");
          } catch (e) {
            console.warn("Failed to create cookies file: " + e);
          }
        }

        // Get proxy settings for the URL
        var proxyUrl = "";
        try {
          proxyUrl = qtJsNetworkProxyMgr.proxyForUrl(obj.url) || "";
          // Sanitize proxy URL
          proxyUrl = sanitizeString(proxyUrl, 512);
        } catch (e) {
          console.warn("Failed to get proxy: " + e);
        }

        // Get user agent from browser or system default
        var userAgent = sanitizeString(obj.userAgent, 512) || "";
        if (!userAgent) {
          try {
            userAgent = sanitizeString(qtJsSystem.defaultUserAgent, 512) || "";
          } catch (e) {}
        }

        // Prepare sanitized arguments with large download config
        var args = [
          obj.url,  // Already validated
          SPEED_PROFILE,
          cookiesArg,
          cookiesString,
          proxyUrl,
          userAgent,
          // Pass large download configuration as JSON
          JSON.stringify(LARGE_DOWNLOAD_CONFIG)
        ];

        launchPythonScript(
          obj.requestId,
          obj.interactive,
          "python/extractor.py",
          args
        ).then(function (res) {
          try {
            // Security: Check output size before parsing (increased for large downloads)
            if (res.output && res.output.length > LARGE_DOWNLOAD_CONFIG.maxOutputSize) {
              reject({ 
                error: "SECURITY WARNING: Response too large. Possible malicious response from server.", 
                isParseError: true 
              });
              return;
            }

            var result = JSON.parse(res.output);
            
            if (result.error) {
              // Check if error contains security warning
              var errorMsg = result.error;
              if (errorMsg.indexOf("Security:") === 0 || errorMsg.indexOf("WARNING:") !== -1) {
                reject({ error: errorMsg, isParseError: true });
              } else {
                reject({ error: result.error, isParseError: true });
              }
            } else {
              // Validate result structure
              if (result.formats && !Array.isArray(result.formats)) {
                reject({ error: "Invalid response structure", isParseError: true });
                return;
              }
              if (result._type === "playlist" && result.entries && !Array.isArray(result.entries)) {
                reject({ error: "Invalid playlist structure", isParseError: true });
                return;
              }
              
              // Add large download hints to formats
              if (result.formats) {
                result.formats = addLargeDownloadHints(result.formats);
              }
              
              resolve(result);
            }
          } catch (e) {
            reject({ error: "Invalid extractor output: " + e.message, isParseError: true });
          }
        }).catch(function (err) {
          reject({ error: err.error || "Extractor failed", isParseError: false });
        });
      }).catch(function(depErr) {
        // Dependency check/install failed
        reject({
          error: depErr.error || "Failed to ensure dependencies are available",
          isParseError: false,
          isDependencyError: depErr.isDependencyError || false
        });
      });
    });
  }
};

/**
 * Add hints for large download handling
 * Adds range request support and chunking hints for FDM
 */
function addLargeDownloadHints(formats) {
  for (var i = 0; i < formats.length; i++) {
    var fmt = formats[i];
    var filesize = fmt.filesize || 0;
    
    // For large files (>1GB), add hints
    if (filesize > 1024 * 1024 * 1024) {
      // Ensure HTTP headers support range requests
      if (!fmt.httpHeaders) {
        fmt.httpHeaders = {};
      }
      
      // Add Accept-Ranges hint if not present
      if (!fmt.httpHeaders["Accept-Ranges"]) {
        fmt.httpHeaders["Accept-Ranges"] = "bytes";
      }
      
      // Mark as large download for FDM optimization
      fmt._largeDownload = true;
      fmt._suggestedChunkSize = LARGE_DOWNLOAD_CONFIG.chunkSize;
    }
    
    // For files with many fragments, ensure proper handling
    if (fmt.fragments && fmt.fragments.length > 100) {
      fmt._multiFragment = true;
      fmt._fragmentCount = fmt.fragments.length;
    }
  }
  return formats;
}

// Playlist parser - references msParser
var msBatchVideoParser = msParser;
