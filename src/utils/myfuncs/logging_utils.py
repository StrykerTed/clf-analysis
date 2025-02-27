import os
import logging
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Manager
from datetime import datetime

def setup_logging(top_level_folder):
    """Configure logging for multiprocessing with timestamped filename in a logging subfolder."""
    # Create the logging subfolder in top_level_folder
    logging_dir = os.path.join(top_level_folder, "logging")
    os.makedirs(logging_dir, exist_ok=True)  # Create directory if it doesn't exist
    
    # Generate timestamp for the filename (e.g., 20250224_153022)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"shapely_abp_path_processing_{timestamp}.log"
    log_file = os.path.join(logging_dir, log_filename)
    
    # Set up manager for multiprocessing
    manager = Manager()
    log_queue = manager.Queue()
    
    # File handler: logs everything to the timestamped file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(processName)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler: only WARNING and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Set up the root logger for the main process
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
    
    # Start the queue listener
    listener = QueueListener(log_queue, file_handler, console_handler)
    listener.start()
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger, log_queue, listener