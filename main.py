from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import uvicorn
from datetime import datetime

app = FastAPI()

# CORS Configuration
app.add_middleware(
  CORSMiddleware,
  allow_origins = ["*"],
  allow_methods = ["*"],
  allow_headers = ["*"],
)

class URLRequest(BaseModel):
url: str

@app.post("/api/metadata")
async def get_metadata(request: URLRequest):
ydl_opts = {
  'quiet': True,
  'no_warnings': True,
  'extract_flat': False,
  'check_formats': 'selected',
  'extractor_args': {
    'youtube': {
      'player_client': ['web']}},
}

try:
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
info = ydl.extract_info(request.url, download = False)

# Extract metadata
metadata = {
  'title': info.get('title', 'No title'),
  'thumbnail': max(
    [t for t in info.get('thumbnails', []) if t.get('url')],
    key = lambda x: x.get('width', 0),
    default = {}
  ).get('url', ''),
  'duration': info.get('duration', 0),
  'uploader': info.get('uploader', 'Unknown'),
  'view_count': info.get('view_count', 0),
  'upload_date': datetime.strptime(
    info.get('upload_date') or '19700101',
    '%Y%m%d'
  ).strftime('%d-%m-%Y') if info.get('upload_date') else None,
}

# Get only merged formats (video+audio)
formats = []
for f in info.get('formats', []):
if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
formats.append({
  'id': f['format_id'],
  'ext': f['ext'],
  'resolution': f.get('resolution') or
f' {
    f.get("width", 0)}x {
    f.get("height", 0)}',
  'fps': f.get('fps', 0),
  'size': f.get('filesize', 0),
  'quality': f.get('quality', 0),
  'note': f.get('format_note', ''),
})

return {
  'success': True,
  'metadata': metadata,
  'formats': sorted(
    formats,
    key = lambda x: (
      -int(x['resolution'].split('x')[0] if 'x' in x['resolution'] else 0),
      -x['fps'],
      -x['quality']
    )
  )
}
except Exception as e:
raise HTTPException(
  status_code = 400,
  detail = {
    'success': False,
    'error': str(e),
    'ytdlp_version': yt_dlp.version.__version__
  }
)

@app.get("/api/download")
async def download_video(url: str, format_id: str):
ydl_opts = {
  'format': f' {
    format_id
  }+bestaudio/best',
  'quiet': True,
  'no_warnings': True,
  'merge_output_format': 'mp4',
  'outtmpl': '%(title)s.%(ext)s',
  'concurrent_fragment_downloads': 5,
  'http_chunk_size': 10485760,
}

try:
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
info = ydl.extract_info(url, download = False)
format_info = next(
  (f for f in info['formats'] if f['format_id'] == format_id),
  None
)

if not format_info:
raise HTTPException(status_code = 404, detail = "Format not found")

return {
  'success': True,
  'url': format_info['url'],
  'filename': f" {
    info['title']}.mp4",
  'direct': True
}
except Exception as e:
raise HTTPException(
  status_code = 400,
  detail = {
    'success': False,
    'error': str(e),
    'ytdlp_version': yt_dlp.version.__version__
  }
)

if __name__ == "__main__":
uvicorn.run(app, host = "0.0.0.0", port = 8000)