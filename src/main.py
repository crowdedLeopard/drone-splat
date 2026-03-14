"""
Real-Time 3D Gaussian Splatting Pipeline - Main Entry Point

Coordinates the working Path B architecture:
RTMPIngestor → GaussianReconstructor → ViewerServer + AzureUploader

Author: Holden (Lead Architect)
Architecture Decision: Path B Unification (2026-03-13)
"""

import sys
import signal
import time
import threading
import queue
import logging
from pathlib import Path
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.rtmp_ingestor import RTMPIngestor
from reconstruction.reconstructor import GaussianReconstructor
from viewer.viewer_server import ViewerServer
from utils.azure_uploader import AzureUploader

# Setup standard logging (not loguru - may not be installed)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the 3D reconstruction pipeline using Path B components"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        
        # Thread-safe communication
        self.frame_queue = queue.Queue(maxsize=100)
        self.stop_event = threading.Event()
        
        # Components
        self.rtmp_ingestor = None
        self.reconstructor = None
        self.viewer = None
        self.azure_uploader = None
        
        # Threads
        self.ingestor_thread = None
        
        logger.info("Initializing Real-Time 3D Gaussian Splatting Pipeline (Path B)")
        
        # Initialize directories
        self._initialize_directories()
        
        # Initialize components
        self._initialize_components()
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def _initialize_directories(self):
        """Create necessary directories if they don't exist"""
        dirs = [
            self.config['ingestion']['frames_dir'],
            self.config['reconstruction']['output_dir'],
        ]
        
        if self.config['logging']['file']['enabled']:
            log_path = Path(self.config['logging']['file']['path'])
            dirs.append(str(log_path.parent))
        
        if self.config['debug']['save_intermediate']:
            dirs.append(self.config['debug']['intermediate_dir'])
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {dir_path}")
    
    def _initialize_components(self):
        """Initialize pipeline components"""
        try:
            # Build RTMP URL from config
            rtmp_url = (
                f"rtmp://{self.config['rtmp']['host']}:{self.config['rtmp']['port']}/"
                f"{self.config['rtmp']['app']}/{self.config['rtmp']['stream_key']}"
            )
            
            # RTMPIngestor config
            ingestor_config = {
                'rtmp_url': rtmp_url,
                'frame_rate': self.config['ingestion']['frame_rate'],
                'width': 1920,
                'height': 1080,
            }
            
            logger.info("Initializing RTMP ingestor...")
            self.rtmp_ingestor = RTMPIngestor(ingestor_config)
            
            # GaussianReconstructor config
            reconstructor_config = {
                'output_dir': self.config['reconstruction']['output_dir'],
                'output_format': self.config['reconstruction']['output_format'],
                'reconstruction_interval': self.config['reconstruction'].get('update_interval_sec', 5.0),
                'min_keyframes': self.config['reconstruction'].get('window_size', 10),
                'frame_selector': {},
                'pose_estimator': {},
                'gaussian_trainer': {
                    'num_iterations': 300,
                    'device': self.config['reconstruction']['device']
                },
            }
            
            logger.info("Initializing Gaussian reconstructor...")
            self.reconstructor = GaussianReconstructor(reconstructor_config)
            
            # Viewer Server
            if self.config['viewer']['type'] == 'web':
                logger.info("Initializing web viewer...")
                self.viewer = ViewerServer(self.config['viewer'])
            
            # Azure Uploader (optional)
            if self.config['azure']['enabled']:
                logger.info("Initializing Azure storage uploader...")
                azure_config = {
                    'enabled': True,
                    'connection_string': self.config['azure']['storage'].get('connection_string', ''),
                    'container_name': self.config['azure']['storage']['container_name'],
                }
                self.azure_uploader = AzureUploader(azure_config)
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def start(self):
        """Start the pipeline"""
        logger.info("=" * 60)
        logger.info("Starting Real-Time 3D Gaussian Splatting Pipeline")
        logger.info("=" * 60)
        
        self.running = True
        
        try:
            # 1. Start viewer first
            if self.viewer:
                logger.info("Starting viewer server...")
                self.viewer.start()
                logger.info(f"View reconstruction at http://localhost:{self.config['viewer']['web']['port']}")
            
            # 2. Start RTMP ingestor in background thread
            logger.info("Starting RTMP ingestor...")
            rtmp_url = (
                f"rtmp://<your-ip>:{self.config['rtmp']['port']}/"
                f"{self.config['rtmp']['app']}/{self.config['rtmp']['stream_key']}"
            )
            logger.info(f"Waiting for RTMP stream at {rtmp_url}")
            
            self.ingestor_thread = threading.Thread(
                target=self.rtmp_ingestor.run,
                args=(self.frame_queue, self.stop_event),
                daemon=True
            )
            self.ingestor_thread.start()
            
            logger.info("=" * 60)
            logger.info("Pipeline running. Press Ctrl+C to stop.")
            logger.info("=" * 60)
            
            # 3. Main loop: consume frames from queue, feed to reconstructor
            frame_count = 0
            while self.running:
                try:
                    # Get frame from queue with timeout
                    frame_data = self.frame_queue.get(timeout=1.0)
                    
                    frame = frame_data['frame']
                    timestamp = frame_data['timestamp']
                    
                    # Feed to reconstructor
                    updated = self.reconstructor.add_frame(frame, timestamp)
                    
                    if updated:
                        # Reconstruction was updated - trigger callbacks
                        output_path = self.reconstructor.get_output_path()
                        if output_path:
                            self._on_reconstruction_update(output_path)
                    
                    frame_count += 1
                    if frame_count % 10 == 0:
                        logger.debug(f"Processed {frame_count} frames")
                    
                    self.frame_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing frame: {e}", exc_info=True)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal (Ctrl+C)")
            self.stop()
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            self.stop()
            raise
    
    def _on_reconstruction_update(self, output_path: str):
        """Called when reconstruction produces new output"""
        logger.info(f"Reconstruction updated: {output_path}")
        
        # Notify viewer to refresh
        if self.viewer:
            self.viewer.notify_update(Path(output_path))
        
        # Upload to Azure if enabled
        if self.azure_uploader and self.config['azure']['storage'].get('upload_on_update', True):
            try:
                url = self.azure_uploader.upload_if_enabled(output_path)
                if url:
                    logger.info(f"Uploaded to Azure: {url}")
            except Exception as e:
                logger.error(f"Azure upload failed: {e}")
    
    def stop(self):
        """Stop the pipeline gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping pipeline...")
        self.running = False
        self.stop_event.set()
        
        # Stop ingestor thread
        if self.ingestor_thread and self.ingestor_thread.is_alive():
            logger.info("Stopping RTMP ingestor...")
            self.ingestor_thread.join(timeout=5)
        
        # Stop viewer
        if self.viewer:
            logger.info("Stopping viewer...")
            self.viewer.stop()
        
        logger.info("Pipeline stopped")


def main():
    """Main entry point"""
    # Check for config file path argument
    config_path = "config/config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Create and start pipeline
    pipeline = PipelineOrchestrator(config_path)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received termination signal")
        pipeline.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start pipeline
    pipeline.start()


if __name__ == "__main__":
    main()
