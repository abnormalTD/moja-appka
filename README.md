# YouTube MP3 Downloader

A small personal Android app (built with [Kivy](https://kivy.org/) and [buildozer](https://buildozer.readthedocs.io/)) that downloads audio from YouTube as MP3 files, using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and ffmpeg.

## Features

- Download a single video or a full playlist as MP3
- Optional custom destination folder
- Download/conversion progress shown in the UI
- Checks GitHub Releases for newer versions

## Disclaimer

This app is a personal hobby project intended **for private, personal use only**.

Downloading content from YouTube may conflict with YouTube's Terms of Service, and copyright law regarding downloaded content varies by country. By using this app, you are responsible for ensuring your use complies with YouTube's Terms of Service and the copyright laws applicable to you. Only download content you have the right to download (e.g. your own uploads, public domain works, or content you otherwise have permission to save).

This project is not affiliated with, endorsed by, or sponsored by YouTube or Google.

## Building

```
buildozer android debug
```

The resulting APK will be placed in the `bin/` directory.
