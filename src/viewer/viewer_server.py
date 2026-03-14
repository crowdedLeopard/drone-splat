"""
Web Viewer Server

Serves web-based Gaussian Splatting viewer with auto-refresh.
Uses antimatter15/splat viewer or similar WebGL-based viewer.

Owner: Bobbie
"""

import http.server
import socketserver
import threading
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ViewerServer:
    """Web server for Gaussian Splatting viewer"""
    
    def __init__(self, config: dict):
        self.config = config
        self.web_config = config.get('web', {})
        self.host = self.web_config.get('host', 'localhost')
        self.port = self.web_config.get('port', 8080)
        self.auto_refresh = self.web_config.get('auto_refresh_interval', 2000)
        self.output_dir = Path(config.get('output_dir', './output'))
        
        self.running = False
        self.server = None
        self.server_thread = None
        
        logger.info(f"Viewer Server initialized: {self.host}:{self.port}")
    
    def start(self):
        """Start the web viewer server"""
        self.running = True
        
        # Start HTTP server in separate thread
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        
        logger.info(f"Viewer server started at http://{self.host}:{self.port}")
        logger.info("Open this URL in your browser to view the 3D reconstruction")
    
    def _run_server(self):
        """Run HTTP server"""
        try:
            viewer_dir = Path(__file__).parent
            output_dir = self.output_dir
            
            class CustomHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(viewer_dir.parent.parent), **kwargs)
                
                def do_GET(self):
                    if self.path == "/" or self.path == "/viewer" or self.path == "/viewer/":
                        self.path = "/src/viewer/viewer.html"
                    elif self.path == "/api/latest":
                        self.send_latest_file_info()
                        return
                    super().do_GET()
                
                def send_latest_file_info(self):
                    """API endpoint to get latest .ply file info."""
                    ply_files = sorted(output_dir.glob("*.ply"), key=lambda f: f.stat().st_mtime, reverse=True)
                    
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
                    pass
            
            with socketserver.TCPServer((self.host, self.port), CustomHandler) as httpd:
                self.server = httpd
                logger.info(f"Serving viewer from {viewer_dir}")
                httpd.serve_forever()
                
        except Exception as e:
            logger.error(f"Viewer server error: {e}")
    
    def notify_update(self, output_file: Path):
        """Notify viewer that reconstruction has updated"""
        # TODO (Bobbie): Implement update notification
        # Could use WebSocket, Server-Sent Events, or polling
        logger.info(f"Viewer notified of update: {output_file}")
    
    def get_stats(self) -> dict:
        """Get viewer statistics"""
        return {
            'url': f"http://{self.host}:{self.port}",
            'running': self.running,
        }
    
    def is_healthy(self) -> bool:
        """Check if viewer is healthy"""
        return self.running and self.server_thread.is_alive()
    
    def stop(self, timeout: int = 30):
        """Stop the viewer server"""
        self.running = False
        
        if self.server:
            self.server.shutdown()
        
        logger.info("Viewer Server stopped")
