from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import uvicorn
from datetime import datetime

app = FastAPI()

# Configure CORS
app.add_middleware(
  CORSMiddleware,
  allow_origins = ["https://yt-next-eight.vercel.app"], # For production, specify your frontend URL
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
}

try:
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
info = ydl.extract_info(request.url, download = False)

metadata = {
  'title': info.get('title', 'No title'),
  'thumbnail': info.get('thumbnail', ''),
  'duration': info.get('duration', 0),
  'uploader': info.get('uploader', 'Unknown'),
  'view_count': info.get('view_count', 0),
  'upload_date': datetime.strptime(
    info.get('upload_date') or '19700101',
    '%Y%m%d'
  ).strftime('%Y-%m-%d') if info.get('upload_date') else None,
}

formats = []
for f in info.get('formats', []):
if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
formats.append({
  'id': f['format_id'],
  'ext': f['ext'],
  'resolution': f.get('resolution', 'unknown'),
  'fps': f.get('fps', 0),
  'size': f.get('filesize', 0),
  'note': f.get('format_note', ''),
})

return {
  'metadata': metadata,
  'formats': sorted(
    formats,
    key = lambda x: (
      -int(x['resolution'].split('x')[0]) if 'x' in x['resolution'] else 0,
      -x['fps'],
      -x.get('quality', 0)
    )
  )
}
except Exception as e:
raise HTTPException(status_code = 400, detail = str(e))

@app.get("/api/download")
async def download_video(url: str, format_id: str):
ydl_opts = {
  'format': f' {
    format_id
  }+bestaudio/best',
  'quiet': True,
  'no_warnings': True,
  'merge_output_format': 'mp4',
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
  'url': format_info['url'],
  'filename': f" {
    info['title']}.mp4",
}
except Exception as e:
raise HTTPException(status_code = 400, detail = str(e))

if __name__ == "__main__":
uvicorn.run(app, host = "0.0.0.0", port = 8000)