"""
Local web server for viewing 3D Gaussian Splatting .ply files.

Serves a simple web viewer with auto-reload capability.
"""

import webbrowser
import threading
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Optional
import json


class SplatHTTPHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for serving splat files and viewer."""
    
    def __init__(self, *args, output_dir: Path, **kwargs):
        self.output_dir = output_dir
        super().__init__(*args, directory=str(output_dir.parent), **kwargs)
    
    def do_GET(self):
        if self.path == "/api/latest":
            self.send_latest_file_info()
        else:
            super().do_GET()
    
    def send_latest_file_info(self):
        """API endpoint to get latest .ply file info."""
        ply_files = sorted(self.output_dir.glob("*.ply"), key=lambda f: f.stat().st_mtime, reverse=True)
        
        if ply_files:
            latest = ply_files[0]
            info = {
                "filename": latest.name,
                "path": f"/output/{latest.name}",
                "size": latest.stat().st_size,
                "modified": latest.stat().st_mtime,
                "count": len(ply_files)
            }
        else:
            info = {"filename": None, "path": None, "size": 0, "modified": 0, "count": 0}
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(info).encode())
    
    def log_message(self, format, *args):
        # Suppress logging for cleaner output
        pass


class LocalWebViewer:
    """
    Local web server for viewing 3D Gaussian Splatting files.
    
    Serves the viewer HTML and provides API for latest file info.
    """
    
    def __init__(self, config: dict):
        """
        Args:
            config: Configuration dict with keys:
                - output_dir: directory containing .ply files
                - port: HTTP server port (default 8080)
                - auto_open: bool (auto-open browser on start)
                - viewer_html: path to viewer HTML file
        """
        self.output_dir = Path(config.get("output_dir", "./output"))
        self.port = config.get("port", 8080)
        self.auto_open = config.get("auto_open", True)
        self.viewer_html = Path(config.get("viewer_html", "./src/viewer/viewer.html"))
        
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start HTTP server and optionally open browser."""
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        def handler(*args, **kwargs):
            return SplatHTTPHandler(*args, output_dir=self.output_dir, **kwargs)
        
        self.server = HTTPServer(("localhost", self.port), handler)
        
        def serve():
            print(f"[WebViewer] Server running at http://localhost:{self.port}")
            self.server.serve_forever()
        
        self.server_thread = threading.Thread(target=serve, daemon=True)
        self.server_thread.start()
        
        time.sleep(0.5)
        
        if self.auto_open:
            url = f"http://localhost:{self.port}/viewer.html"
            print(f"[WebViewer] Opening browser: {url}")
            webbrowser.open(url)
        
        return self
    
    def stop(self):
        """Stop the HTTP server."""
        if self.server:
            print("[WebViewer] Stopping server...")
            self.server.shutdown()
            if self.server_thread:
                self.server_thread.join()
    
    def wait(self):
        """Wait for server thread to finish (blocking)."""
        if self.server_thread:
            try:
                self.server_thread.join()
            except KeyboardInterrupt:
                self.stop()
