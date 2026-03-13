"""
Test RTMP Stream Generator

Generates a test RTMP stream to MediaMTX server for testing the pipeline
without requiring a real DJI drone.

Usage:
    python scripts/test_stream.py [video_file]

If no video file provided, generates synthetic test pattern.
"""

import sys
import subprocess
import time
from pathlib import Path


def stream_test_pattern(rtmp_url: str = "rtmp://localhost:1935/live/drone"):
    """
    Stream a synthetic test pattern to RTMP server
    
    Args:
        rtmp_url: RTMP destination URL
    """
    print(f"Streaming test pattern to {rtmp_url}")
    print("Press Ctrl+C to stop")
    
    # FFmpeg command to generate test pattern
    # testsrc: Synthetic test pattern (color bars, moving square)
    # drawtext: Adds frame counter
    cmd = [
        'ffmpeg',
        '-re',  # Read input at native frame rate
        '-f', 'lavfi',
        '-i', 'testsrc=size=1280x720:rate=30',  # 720p test pattern at 30fps
        '-vf', 'drawtext=fontfile=/Windows/Fonts/arial.ttf:text=%{frame_num}:start_number=0:x=(w-tw)/2:y=h-th-10:fontcolor=white:fontsize=48:box=1:boxcolor=black@0.5',
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-tune', 'zerolatency',
        '-b:v', '2M',
        '-maxrate', '2M',
        '-bufsize', '4M',
        '-g', '60',  # Keyframe every 2 seconds
        '-f', 'flv',
        rtmp_url
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        return False
    except KeyboardInterrupt:
        print("\nStream stopped")
        return True


def stream_video_file(video_path: Path, rtmp_url: str = "rtmp://localhost:1935/live/drone", loop: bool = True):
    """
    Stream a video file to RTMP server
    
    Args:
        video_path: Path to video file
        rtmp_url: RTMP destination URL
        loop: Loop video indefinitely
    """
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        return False
    
    print(f"Streaming {video_path} to {rtmp_url}")
    if loop:
        print("Looping enabled - press Ctrl+C to stop")
    
    # FFmpeg command to stream video file
    cmd = [
        'ffmpeg',
        '-re',  # Read input at native frame rate
    ]
    
    if loop:
        cmd.extend(['-stream_loop', '-1'])  # Loop indefinitely
    
    cmd.extend([
        '-i', str(video_path),
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-tune', 'zerolatency',
        '-b:v', '2M',
        '-maxrate', '2M',
        '-bufsize', '4M',
        '-g', '60',
        '-f', 'flv',
        rtmp_url
    ])
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        return False
    except KeyboardInterrupt:
        print("\nStream stopped")
        return True


def main():
    print("=" * 60)
    print("RTMP Test Stream Generator")
    print("=" * 60)
    print()
    
    # Check if FFmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: FFmpeg not found. Please install FFmpeg and add to PATH.")
        print("Download from: https://ffmpeg.org/download.html")
        return 1
    
    # Get RTMP URL from config or use default
    rtmp_url = "rtmp://localhost:1935/live/drone"
    
    print("RTMP Destination:", rtmp_url)
    print()
    print("Make sure MediaMTX is running:")
    print("  .\\mediamtx.exe")
    print()
    
    # Check if video file provided
    if len(sys.argv) > 1:
        video_path = Path(sys.argv[1])
        success = stream_video_file(video_path, rtmp_url, loop=True)
    else:
        print("No video file provided. Generating synthetic test pattern...")
        print()
        success = stream_test_pattern(rtmp_url)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
