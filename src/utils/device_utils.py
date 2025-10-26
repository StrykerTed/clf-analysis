"""
GPU/CPU Device Detection Utility
Provides automatic device selection with graceful CPU fallback
"""
import logging

logger = logging.getLogger(__name__)

def get_device():
    """
    Detect and return the best available compute device.
    
    Returns:
        tuple: (device, device_name, is_gpu)
            - device: torch.device or str "cpu"
            - device_name: Human-readable device name
            - is_gpu: Boolean indicating if GPU is available
    """
    try:
        import torch
        
        if torch.cuda.is_available():
            device = torch.device("cuda:0")
            device_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # Convert to GB
            logger.info(f"GPU detected: {device_name} with {gpu_memory:.2f} GB memory")
            logger.info("Using GPU acceleration for processing")
            return device, device_name, True
        else:
            logger.info("No GPU detected, using CPU for processing")
            return "cpu", "CPU", False
            
    except ImportError:
        logger.warning("PyTorch not available, using CPU-only mode")
        return "cpu", "CPU", False
    except Exception as e:
        logger.error(f"Error detecting device: {e}. Falling back to CPU")
        return "cpu", "CPU", False


def get_cupy_device():
    """
    Check if CuPy (GPU-accelerated NumPy) is available.
    
    Returns:
        tuple: (module, is_gpu)
            - module: cupy or numpy module
            - is_gpu: Boolean indicating if CuPy/GPU is available
    """
    try:
        import cupy as cp
        
        # Test if CUDA is actually available
        try:
            cp.cuda.runtime.getDeviceCount()
            logger.info("CuPy GPU acceleration enabled")
            return cp, True
        except Exception:
            import numpy as np
            logger.info("CuPy installed but no GPU available, using NumPy")
            return np, False
            
    except ImportError:
        import numpy as np
        logger.info("CuPy not available, using NumPy (CPU)")
        return np, False


def log_device_info():
    """
    Log comprehensive device information for debugging.
    """
    logger.info("=" * 50)
    logger.info("Device Configuration")
    logger.info("=" * 50)
    
    # PyTorch device info
    device, device_name, is_gpu = get_device()
    logger.info(f"PyTorch Device: {device_name} ({'GPU' if is_gpu else 'CPU'})")
    
    # Additional GPU info
    if is_gpu:
        try:
            import torch
            logger.info(f"CUDA Version: {torch.version.cuda}")
            logger.info(f"PyTorch Version: {torch.__version__}")
        except:
            pass
    
    logger.info("=" * 50)


# Initialize and log device info when module is imported
if __name__ != "__main__":
    log_device_info()
