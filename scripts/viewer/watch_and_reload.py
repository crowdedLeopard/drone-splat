"""
Auto-reload script for 3D Gaussian Splatting viewer.

Watches for new .ply files and automatically opens them in the viewer.

Usage:
    python scripts/viewer/watch_and_reload.py --output-dir ./output --mode web
    python scripts/viewer/watch_and_reload.py --output-dir ./output --mode blender
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from viewer import SplatFileWatcher, LocalWebViewer


def main():
    parser = argparse.ArgumentParser(description="Watch and reload 3D Gaussian Splat viewer")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output",
        help="Directory to watch for .ply files"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["web", "blender", "notify"],
        default="web",
        help="Viewer mode: web (browser), blender, or notify (just log)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for web viewer (if mode=web)"
    )
    parser.add_argument(
        "--no-auto-open",
        action="store_true",
        help="Don't auto-open browser/Blender"
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    
    print("=" * 60)
    print("🎨 3D Gaussian Splat Viewer - Auto-Reload")
    print("=" * 60)
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Viewer mode: {args.mode}")
    print("=" * 60)
    
    # Start web server if in web mode
    web_viewer = None
    if args.mode == "web":
        web_config = {
            "output_dir": output_dir,
            "port": args.port,
            "auto_open": not args.no_auto_open,
        }
        web_viewer = LocalWebViewer(web_config)
        web_viewer.start()
        print(f"\n✓ Web viewer ready at http://localhost:{args.port}/viewer.html\n")
    
    # Start file watcher
    watcher_config = {
        "output_dir": output_dir,
        "viewer_mode": args.mode,
        "auto_open": not args.no_auto_open,
    }
    
    watcher = SplatFileWatcher(watcher_config)
    
    print("👀 Watching for .ply files...")
    print("Press Ctrl+C to stop\n")
    
    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\n\n⏹ Stopping viewer...")
        watcher.stop()
        if web_viewer:
            web_viewer.stop()
        print("✓ Stopped")


if __name__ == "__main__":
    main()
