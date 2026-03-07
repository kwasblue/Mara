# ml_preprocess.py
"""
Optimized ML preprocessing for camera frames.

Features:
- Fast interpolation (INTER_LINEAR vs INTER_AREA)
- Pre-allocated buffer caching
- GPU acceleration (OpenCV CUDA or PyTorch)
- Batch preprocessing support
- Configurable normalization stats
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
import threading

# Default normalization stats
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Check for GPU availability
_GPU_AVAILABLE = False
_GPU_BACKEND = None

try:
    if cv2.cuda.getCudaEnabledDeviceCount() > 0:
        _GPU_AVAILABLE = True
        _GPU_BACKEND = "cuda"
except Exception:
    pass

if not _GPU_AVAILABLE:
    try:
        import torch
        if torch.cuda.is_available():
            _GPU_AVAILABLE = True
            _GPU_BACKEND = "torch"
    except ImportError:
        pass


@dataclass
class NormalizationStats:
    """Normalization statistics for preprocessing."""
    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def imagenet(cls) -> "NormalizationStats":
        return cls(mean=IMAGENET_MEAN.copy(), std=IMAGENET_STD.copy())

    @classmethod
    def none(cls) -> "NormalizationStats":
        """No normalization (just scale to 0-1)."""
        return cls(
            mean=np.array([0.0, 0.0, 0.0], dtype=np.float32),
            std=np.array([1.0, 1.0, 1.0], dtype=np.float32),
        )


class PreprocessorCache:
    """
    Thread-safe cache for pre-allocated preprocessing buffers.
    Reduces memory allocation overhead in hot loops.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._buffers: dict = {}

    def get_buffer(
        self,
        key: str,
        shape: Tuple[int, ...],
        dtype: np.dtype = np.float32,
    ) -> np.ndarray:
        """Get or create a pre-allocated buffer."""
        cache_key = (key, shape, dtype)

        with self._lock:
            if cache_key not in self._buffers:
                self._buffers[cache_key] = np.empty(shape, dtype=dtype)
            return self._buffers[cache_key]

    def clear(self) -> None:
        """Clear all cached buffers."""
        with self._lock:
            self._buffers.clear()


# Global cache instance
_cache = PreprocessorCache()


def preprocess_for_ml(
    frame_bgr: np.ndarray,
    target_size: Tuple[int, int] = (224, 224),
    normalize: bool = True,
    to_chw: bool = True,
    mean: Optional[np.ndarray] = None,
    std: Optional[np.ndarray] = None,
    use_fast_resize: bool = True,
    use_cache: bool = False,
) -> np.ndarray:
    """
    Convert raw OpenCV BGR frame into an ML-ready array.

    Steps:
      - BGR -> RGB
      - Resize to target_size
      - Scale to [0, 1]
      - Optional mean/std normalize
      - Optional CHW (C, H, W)

    Args:
        frame_bgr: Input BGR image from OpenCV
        target_size: Output (width, height)
        normalize: Apply mean/std normalization
        to_chw: Transpose to CHW format
        mean: Custom mean values (default: ImageNet)
        std: Custom std values (default: ImageNet)
        use_fast_resize: Use INTER_LINEAR (fast) vs INTER_AREA (quality)
        use_cache: Use pre-allocated buffers (slight speedup, not thread-safe per-buffer)

    Returns:
        Preprocessed float32 array
    """
    # BGR -> RGB
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    # Resize with fast interpolation
    interpolation = cv2.INTER_LINEAR if use_fast_resize else cv2.INTER_AREA
    frame_rgb = cv2.resize(frame_rgb, target_size, interpolation=interpolation)

    # Scale to [0, 1]
    img = frame_rgb.astype(np.float32) * (1.0 / 255.0)

    # Normalize
    if normalize:
        m = mean if mean is not None else IMAGENET_MEAN
        s = std if std is not None else IMAGENET_STD
        img = (img - m) / s

    # HWC -> CHW
    if to_chw:
        img = np.transpose(img, (2, 0, 1))

    return img


def preprocess_for_ml_gpu(
    frame_bgr: np.ndarray,
    target_size: Tuple[int, int] = (224, 224),
    normalize: bool = True,
    to_chw: bool = True,
    mean: Optional[np.ndarray] = None,
    std: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    GPU-accelerated preprocessing using OpenCV CUDA or PyTorch.

    Falls back to CPU if GPU not available.
    """
    if not _GPU_AVAILABLE:
        return preprocess_for_ml(
            frame_bgr, target_size, normalize, to_chw, mean, std
        )

    if _GPU_BACKEND == "torch":
        return _preprocess_torch(frame_bgr, target_size, normalize, to_chw, mean, std)
    elif _GPU_BACKEND == "cuda":
        return _preprocess_cuda(frame_bgr, target_size, normalize, to_chw, mean, std)

    # Fallback
    return preprocess_for_ml(frame_bgr, target_size, normalize, to_chw, mean, std)


def _preprocess_torch(
    frame_bgr: np.ndarray,
    target_size: Tuple[int, int],
    normalize: bool,
    to_chw: bool,
    mean: Optional[np.ndarray],
    std: Optional[np.ndarray],
) -> np.ndarray:
    """PyTorch GPU preprocessing."""
    import torch
    import torch.nn.functional as F

    # BGR -> RGB and to tensor
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(frame_rgb).cuda().float() / 255.0

    # HWC -> CHW for resize
    tensor = tensor.permute(2, 0, 1).unsqueeze(0)

    # Resize
    tensor = F.interpolate(
        tensor,
        size=(target_size[1], target_size[0]),  # (H, W)
        mode="bilinear",
        align_corners=False,
    )

    tensor = tensor.squeeze(0)

    # Normalize
    if normalize:
        m = torch.tensor(mean if mean is not None else IMAGENET_MEAN).cuda().view(3, 1, 1)
        s = torch.tensor(std if std is not None else IMAGENET_STD).cuda().view(3, 1, 1)
        tensor = (tensor - m) / s

    # CHW -> HWC if needed
    if not to_chw:
        tensor = tensor.permute(1, 2, 0)

    return tensor.cpu().numpy()


def _preprocess_cuda(
    frame_bgr: np.ndarray,
    target_size: Tuple[int, int],
    normalize: bool,
    to_chw: bool,
    mean: Optional[np.ndarray],
    std: Optional[np.ndarray],
) -> np.ndarray:
    """OpenCV CUDA preprocessing."""
    # Upload to GPU
    gpu_frame = cv2.cuda_GpuMat()
    gpu_frame.upload(frame_bgr)

    # BGR -> RGB
    gpu_rgb = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2RGB)

    # Resize
    gpu_resized = cv2.cuda.resize(gpu_rgb, target_size, interpolation=cv2.INTER_LINEAR)

    # Download and continue on CPU (CUDA doesn't have convenient normalize)
    frame_rgb = gpu_resized.download()

    # Scale to [0, 1]
    img = frame_rgb.astype(np.float32) * (1.0 / 255.0)

    # Normalize
    if normalize:
        m = mean if mean is not None else IMAGENET_MEAN
        s = std if std is not None else IMAGENET_STD
        img = (img - m) / s

    # HWC -> CHW
    if to_chw:
        img = np.transpose(img, (2, 0, 1))

    return img


def preprocess_batch(
    frames_bgr: List[np.ndarray],
    target_size: Tuple[int, int] = (224, 224),
    normalize: bool = True,
    mean: Optional[np.ndarray] = None,
    std: Optional[np.ndarray] = None,
    use_gpu: bool = False,
) -> np.ndarray:
    """
    Batch preprocess multiple frames.

    Args:
        frames_bgr: List of BGR images
        target_size: Output (width, height)
        normalize: Apply normalization
        mean: Custom mean values
        std: Custom std values
        use_gpu: Use GPU acceleration if available

    Returns:
        Batch array of shape (N, C, H, W)
    """
    if not frames_bgr:
        return np.array([])

    if use_gpu and _GPU_AVAILABLE and _GPU_BACKEND == "torch":
        return _preprocess_batch_torch(frames_bgr, target_size, normalize, mean, std)

    # CPU batch processing
    batch = []
    for frame in frames_bgr:
        processed = preprocess_for_ml(
            frame,
            target_size=target_size,
            normalize=normalize,
            to_chw=True,
            mean=mean,
            std=std,
            use_fast_resize=True,
        )
        batch.append(processed)

    return np.stack(batch, axis=0)


def _preprocess_batch_torch(
    frames_bgr: List[np.ndarray],
    target_size: Tuple[int, int],
    normalize: bool,
    mean: Optional[np.ndarray],
    std: Optional[np.ndarray],
) -> np.ndarray:
    """PyTorch batch preprocessing on GPU."""
    import torch
    import torch.nn.functional as F

    # Convert all frames to RGB tensors
    tensors = []
    for frame in frames_bgr:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(frame_rgb).float() / 255.0
        tensor = tensor.permute(2, 0, 1)  # HWC -> CHW
        tensors.append(tensor)

    # Stack and move to GPU
    batch = torch.stack(tensors, dim=0).cuda()

    # Resize batch
    batch = F.interpolate(
        batch,
        size=(target_size[1], target_size[0]),
        mode="bilinear",
        align_corners=False,
    )

    # Normalize
    if normalize:
        m = torch.tensor(mean if mean is not None else IMAGENET_MEAN).cuda().view(1, 3, 1, 1)
        s = torch.tensor(std if std is not None else IMAGENET_STD).cuda().view(1, 3, 1, 1)
        batch = (batch - m) / s

    return batch.cpu().numpy()


def is_gpu_available() -> bool:
    """Check if GPU preprocessing is available."""
    return _GPU_AVAILABLE


def get_gpu_backend() -> Optional[str]:
    """Get the GPU backend being used ('cuda', 'torch', or None)."""
    return _GPU_BACKEND


def clear_cache() -> None:
    """Clear the preprocessor buffer cache."""
    _cache.clear()
