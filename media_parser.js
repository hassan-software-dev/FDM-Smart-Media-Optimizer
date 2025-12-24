var SPEED_PROFILE = "BALANCED"; // FASTEST | BALANCED | QUALITY

// List of supported sites (yt-dlp supported sites)
var SUPPORTED_DOMAINS = [
  "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "twitch.tv",
  "facebook.com", "fb.watch", "instagram.com", "twitter.com", "x.com",
  "tiktok.com", "reddit.com", "soundcloud.com", "bandcamp.com",
  "bilibili.com", "nicovideo.jp", "crunchyroll.com", "funimation.com"
  // Add more as needed
];

var msParser = {
  isSupportedSource: function (url) {
    // Only match known supported sites to avoid conflicts
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
    // Fallback check when isSupportedSource returns false
    // Check if content-type suggests media
    var ct = (obj.contentType || "").toLowerCase();
    return ct.indexOf("video") !== -1 || 
           ct.indexOf("audio") !== -1 ||
           ct.indexOf("mpegurl") !== -1;
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
      // Build cookies file if cookies exist
      var cookiesArg = "";
      var cookiesString = "";
      var tmpFile = null;
      
      if (obj.cookies && obj.cookies.length > 0) {
        try {
          tmpFile = qtJsTools.createTmpFile("cookies.txt");
          // Convert cookies to Netscape format for yt-dlp
          var cookieLines = ["# Netscape HTTP Cookie File"];
          var cookiePairs = [];
          
          obj.cookies.forEach(function (c) {
            var secure = c.isSecure ? "TRUE" : "FALSE";
            var expiry = Math.floor(c.expirationDate || 0).toString();
            var domain = c.domain || "";
            var subdomainFlag = domain.charAt(0) === "." ? "TRUE" : "FALSE";
            var path = c.path || "/";
            var line = [
              domain,
              subdomainFlag,
              path,
              secure,
              expiry,
              c.name,
              c.value
            ].join("\t");
            cookieLines.push(line);
            
            // Build cookie string for format headers (FDM format)
            var cookieEntry = c.name + "=" + c.value;
            if (domain) cookieEntry += "; Domain=" + domain;
            if (path) cookieEntry += "; Path=" + path;
            if (c.isSecure) cookieEntry += "; Secure";
            if (c.expirationDate) cookieEntry += "; Expires=" + Math.floor(c.expirationDate);
            cookiePairs.push(cookieEntry);
          });
          
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
      } catch (e) {
        console.warn("Failed to get proxy: " + e);
      }

      // Get user agent from browser or system default
      var userAgent = obj.userAgent || "";
      if (!userAgent) {
        try {
          userAgent = qtJsSystem.defaultUserAgent || "";
        } catch (e) {}
      }

      // Check if plugin is allowed to use browser cookies
      var canUseCookies = true;
      try {
        if (App && App.pluginsAllowWbCookies === false) {
          canUseCookies = false;
          cookiesArg = "";
          cookiesString = "";
        }
      } catch (e) {}

      launchPythonScript(
        obj.requestId,
        obj.interactive,
        "python/extractor.py",
        [
          obj.url,
          SPEED_PROFILE,
          cookiesArg,
          cookiesString,
          proxyUrl,
          userAgent
        ]
      ).then(function (res) {
        try {
          var result = JSON.parse(res.output);
          if (result.error) {
            reject({ error: result.error, isParseError: true });
          } else {
            resolve(result);
          }
        } catch (e) {
          reject({ error: "Invalid extractor output: " + e.message, isParseError: true });
        }
      }).catch(function (err) {
        reject({ error: err.error || "Extractor failed", isParseError: false });
      });
    });
  }
};

// Playlist parser - references msParser
var msBatchVideoParser = msParser;
