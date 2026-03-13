"""
Real-Time 3D Gaussian Splatting Pipeline Orchestrator

This is the main entry point for the reconstruction pipeline.
Coordinates RTMP ingestion, frame extraction, 3D reconstruction, and visualization.

Author: Holden (Lead Architect)
"""

import sys
import signal
import time
import threading
from pathlib import Path
from typing import Optional
import yaml
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import setup_logging
from ingestion.rtmp_listener import RTMPListener
from ingestion.frame_extractor import FrameExtractor
from reconstruction.slam_processor import SLAMProcessor
from viewer.viewer_server import ViewerServer


class PipelineOrchestrator:
    """Orchestrates the entire 3D reconstruction pipeline"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.running = False
        self.components = {}
        
        # Setup logging
        setup_logging(self.config.get('logging', {}))
        logger.info("Initializing Real-Time 3D Gaussian Splatting Pipeline")
        
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
            self.config['reconstruction']['model_weights_dir'],
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
            # RTMP Listener (Amos's domain)
            logger.info("Initializing RTMP listener...")
            self.components['rtmp'] = RTMPListener(self.config['rtmp'])
            
            # Frame Extractor (Amos's domain)
            logger.info("Initializing frame extractor...")
            self.components['extractor'] = FrameExtractor(self.config['ingestion'])
            
            # 3D Reconstruction (Naomi's domain)
            logger.info("Initializing 3D reconstruction processor...")
            self.components['reconstruction'] = SLAMProcessor(self.config['reconstruction'])
            
            # Viewer Server (Bobbie's domain)
            if self.config['viewer']['type'] == 'web':
                logger.info("Initializing web viewer...")
                self.components['viewer'] = ViewerServer(self.config['viewer'])
            
            # Azure Uploader (Alex's domain) - optional
            if self.config['azure']['enabled']:
                logger.info("Initializing Azure storage uploader...")
                from azure.storage_uploader import AzureUploader
                self.components['azure'] = AzureUploader(self.config['azure'])
            
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
            # Start viewer first (if enabled)
            if 'viewer' in self.components:
                logger.info("Starting viewer server...")
                self.components['viewer'].start()
            
            # Start RTMP listener
            logger.info("Starting RTMP listener...")
            logger.info(f"Waiting for RTMP stream at rtmp://<your-ip>:{self.config['rtmp']['port']}/{self.config['rtmp']['app']}/{self.config['rtmp']['stream_key']}")
            self.components['rtmp'].start()
            
            # Start frame extractor
            logger.info("Starting frame extractor...")
            self.components['extractor'].start(self.components['rtmp'])
            
            # Start reconstruction processor
            logger.info("Starting 3D reconstruction...")
            self.components['reconstruction'].start(self.components['extractor'])
            
            # Setup reconstruction completion callback
            self.components['reconstruction'].on_update(self._on_reconstruction_update)
            
            # Start monitoring thread
            monitor_thread = threading.Thread(target=self._monitor_pipeline, daemon=True)
            monitor_thread.start()
            
            logger.info("=" * 60)
            logger.info("Pipeline running. Press Ctrl+C to stop.")
            logger.info("=" * 60)
            
            # Main loop - keep running
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal (Ctrl+C)")
            self.stop()
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            self.stop()
            raise
    
    def _on_reconstruction_update(self, output_file: Path):
        """Called when reconstruction produces new output"""
        logger.info(f"Reconstruction updated: {output_file}")
        
        # Upload to Azure if enabled
        if 'azure' in self.components and self.config['azure']['upload_on_update']:
            try:
                self.components['azure'].upload(output_file)
                logger.info("Uploaded to Azure Blob Storage")
            except Exception as e:
                logger.error(f"Azure upload failed: {e}")
        
        # Notify viewer to refresh (if applicable)
        if 'viewer' in self.components:
            self.components['viewer'].notify_update(output_file)
    
    def _monitor_pipeline(self):
        """Monitor pipeline health and performance"""
        interval = self.config['pipeline'].get('health_check_interval', 10)
        report_interval = self.config['pipeline'].get('report_interval_sec', 60)
        last_report = time.time()
        
        while self.running:
            time.sleep(interval)
            
            # Check component health
            for name, component in self.components.items():
                if hasattr(component, 'is_healthy'):
                    if not component.is_healthy():
                        logger.warning(f"Component '{name}' is unhealthy")
            
            # Periodic performance report
            if self.config['pipeline'].get('monitor_performance', False):
                if time.time() - last_report > report_interval:
                    self._report_performance()
                    last_report = time.time()
    
    def _report_performance(self):
        """Report pipeline performance metrics"""
        logger.info("--- Pipeline Performance ---")
        
        for name, component in self.components.items():
            if hasattr(component, 'get_stats'):
                stats = component.get_stats()
                logger.info(f"{name}: {stats}")
    
    def stop(self):
        """Stop the pipeline gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping pipeline...")
        self.running = False
        
        timeout = self.config['pipeline'].get('shutdown_timeout', 30)
        
        # Stop components in reverse order
        components_to_stop = [
            ('reconstruction', 'reconstruction processor'),
            ('extractor', 'frame extractor'),
            ('rtmp', 'RTMP listener'),
            ('viewer', 'viewer'),
            ('azure', 'Azure uploader'),
        ]
        
        for comp_name, display_name in components_to_stop:
            if comp_name in self.components:
                try:
                    logger.info(f"Stopping {display_name}...")
                    component = self.components[comp_name]
                    
                    if hasattr(component, 'stop'):
                        component.stop(timeout=timeout)
                    
                    logger.info(f"{display_name} stopped")
                except Exception as e:
                    logger.error(f"Error stopping {display_name}: {e}")
        
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
