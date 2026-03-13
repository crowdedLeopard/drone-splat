"""
Web Viewer Server

Serves web-based Gaussian Splatting viewer with auto-refresh.
Uses antimatter15/splat viewer or similar WebGL-based viewer.

Owner: Bobbie
"""

import http.server
import socketserver
import threading
from pathlib import Path
from loguru import logger


class ViewerServer:
    """Web server for Gaussian Splatting viewer"""
    
    def __init__(self, config: dict):
        self.config = config
        self.web_config = config['web']
        self.host = self.web_config['host']
        self.port = self.web_config['port']
        self.auto_refresh = self.web_config['auto_refresh_interval']
        
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
            handler = http.server.SimpleHTTPRequestHandler
            
            # Change to viewer directory
            viewer_dir = Path(__file__).parent
            
            class CustomHandler(handler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(viewer_dir), **kwargs)
            
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
