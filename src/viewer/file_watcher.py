"""
File watcher for 3D Gaussian Splatting .ply files.

Monitors output directory for new/updated .ply files and triggers viewer refresh.
"""

import time
import threading
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent


class SplatFileHandler(FileSystemEventHandler):
    """Handler for .ply file system events."""
    
    def __init__(self, callback: Callable[[Path], None]):
        self.callback = callback
        self.last_triggered = {}
        self.debounce_seconds = 2.0
    
    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and event.src_path.endswith('.ply'):
            self._trigger(event.src_path)
    
    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and event.src_path.endswith('.ply'):
            self._trigger(event.src_path)
    
    def _trigger(self, filepath: str):
        now = time.time()
        if filepath in self.last_triggered:
            if now - self.last_triggered[filepath] < self.debounce_seconds:
                return
        self.last_triggered[filepath] = now
        self.callback(Path(filepath))


class SplatFileWatcher:
    """
    Watches for new .ply files and triggers viewer refresh.
    
    Modes:
    - "web": Trigger web viewer refresh
    - "blender": Launch Blender with new file
    - "notify": Just log when files change
    """
    
    def __init__(self, config: dict):
        """
        Args:
            config: Configuration dict with keys:
                - output_dir: directory to watch for new .ply files
                - viewer_mode: "web" | "blender" | "notify"
                - auto_open: bool (auto-open browser/Blender)
                - callback: Optional[Callable] custom callback for file changes
        """
        self.output_dir = Path(config.get("output_dir", "./output"))
        self.viewer_mode = config.get("viewer_mode", "notify")
        self.auto_open = config.get("auto_open", True)
        self.custom_callback = config.get("callback")
        
        self.observer: Optional[Observer] = None
        self.latest_file: Optional[Path] = None
    
    def _on_file_change(self, filepath: Path):
        """Called when a .ply file is created or modified."""
        self.latest_file = filepath
        print(f"[Viewer] Detected new splat: {filepath.name}")
        
        if self.custom_callback:
            self.custom_callback(filepath)
        
        if self.viewer_mode == "web":
            self._trigger_web_reload(filepath)
        elif self.viewer_mode == "blender":
            self._launch_blender(filepath)
        elif self.viewer_mode == "notify":
            print(f"[Viewer] File ready for viewing: {filepath}")
    
    def _trigger_web_reload(self, filepath: Path):
        """Trigger web viewer to reload (implementation depends on web server)."""
        print(f"[Viewer] Web viewer should reload {filepath.name}")
    
    def _launch_blender(self, filepath: Path):
        """Launch Blender with the new .ply file."""
        import subprocess
        from pathlib import Path
        
        script_path = Path(__file__).parent.parent.parent / "scripts" / "viewer" / "load_splat.py"
        if not script_path.exists():
            print(f"[Viewer] Blender script not found: {script_path}")
            return
        
        try:
            cmd = ["blender", "--python", str(script_path), "--", str(filepath)]
            print(f"[Viewer] Launching Blender: {' '.join(cmd)}")
            subprocess.Popen(cmd)
        except FileNotFoundError:
            print("[Viewer] Blender not found in PATH. Install Blender or add to PATH.")
    
    def run(self, stop_event: Optional[threading.Event] = None):
        """
        Watch output_dir for new/updated .ply files.
        
        Args:
            stop_event: Optional threading.Event to signal stop
        """
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
            print(f"[Viewer] Created output directory: {self.output_dir}")
        
        handler = SplatFileHandler(self._on_file_change)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.output_dir), recursive=False)
        self.observer.start()
        
        print(f"[Viewer] Watching {self.output_dir} for .ply files (mode: {self.viewer_mode})")
        
        try:
            if stop_event:
                while not stop_event.is_set():
                    time.sleep(1)
            else:
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("[Viewer] Stopping file watcher...")
        finally:
            if self.observer:
                self.observer.stop()
                self.observer.join()
    
    def stop(self):
        """Stop the file watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
