# robot_host/module/camera/presets.py
"""
Predefined camera configuration presets.

All presets are optimized for stable streaming on ESP32-CAM.
Max resolution is SVGA (800x600) for reliable operation.
For single high-res captures, use set_resolution directly.
"""

from .models import CameraConfig, FrameSize


PRESETS: dict[str, CameraConfig] = {
    "default": CameraConfig(
        # Balanced default settings
        frame_size=FrameSize.VGA,  # 640x480
        quality=10,
        brightness=0,
        contrast=0,
        saturation=0,
        sharpness=0,
        awb_enabled=True,
        awb_mode=0,
        aec_enabled=True,
        aec_value=300,
        agc_enabled=True,
        agc_gain=0,
        gain_ceiling=2,
    ),

    "streaming": CameraConfig(
        # Optimized for smooth video streaming - smaller files
        frame_size=FrameSize.VGA,  # 640x480
        quality=12,
        brightness=0,
        contrast=0,
        saturation=0,
        sharpness=0,
        awb_enabled=True,
        awb_mode=0,
        aec_enabled=True,
        aec_value=300,
        agc_enabled=True,
        agc_gain=0,
        gain_ceiling=2,
    ),

    "high_quality": CameraConfig(
        # Best quality at stable resolution
        frame_size=FrameSize.SVGA,  # 800x600 (stable, not SXGA)
        quality=8,  # High quality JPEG
        brightness=0,
        contrast=0,
        saturation=0,
        sharpness=1,  # Slight sharpening
        awb_enabled=True,
        awb_mode=0,
        aec_enabled=True,
        aec_value=300,
        agc_enabled=True,
        agc_gain=0,
        gain_ceiling=1,  # Lower gain = less noise
    ),

    "fast": CameraConfig(
        # Maximum frame rate
        frame_size=FrameSize.QVGA,  # 320x240
        quality=15,
        brightness=0,
        contrast=0,
        saturation=0,
        sharpness=0,
        awb_enabled=True,
        awb_mode=0,
        aec_enabled=True,
        aec_value=300,
        agc_enabled=True,
        agc_gain=0,
        gain_ceiling=2,
    ),

    "night": CameraConfig(
        # Low-light optimization
        frame_size=FrameSize.VGA,  # 640x480
        quality=10,
        brightness=1,
        contrast=1,
        saturation=0,
        sharpness=0,
        awb_enabled=True,
        awb_mode=0,
        aec_enabled=True,
        aec_value=800,  # Longer exposure
        agc_enabled=True,
        agc_gain=20,  # Higher gain for low light
        gain_ceiling=4,
    ),

    "ml_inference": CameraConfig(
        # Optimized for ML models (224x224 input)
        frame_size=FrameSize.QVGA,  # 320x240
        quality=10,
        brightness=0,
        contrast=0,
        saturation=0,
        sharpness=0,
        awb_enabled=True,
        awb_mode=0,
        aec_enabled=True,
        aec_value=300,
        agc_enabled=True,
        agc_gain=0,
        gain_ceiling=2,
    ),

    "surveillance": CameraConfig(
        # Security camera - balanced for recording
        frame_size=FrameSize.SVGA,  # 800x600
        quality=10,
        brightness=0,
        contrast=1,
        saturation=0,
        sharpness=1,
        awb_enabled=True,
        awb_mode=0,
        aec_enabled=True,
        aec_value=300,
        agc_enabled=True,
        agc_gain=0,
        gain_ceiling=3,
    ),

    "timelapse": CameraConfig(
        # High quality for timelapse stills
        frame_size=FrameSize.SVGA,  # 800x600
        quality=8,
        brightness=0,
        contrast=0,
        saturation=0,
        sharpness=0,
        awb_enabled=True,
        awb_mode=0,
        aec_enabled=True,
        aec_value=300,
        agc_enabled=True,
        agc_gain=0,
        gain_ceiling=1,
    ),

    "bright": CameraConfig(
        # Bright/outdoor conditions
        frame_size=FrameSize.VGA,  # 640x480
        quality=10,
        brightness=-1,  # Reduce brightness for bright scenes
        contrast=1,
        saturation=1,
        sharpness=1,
        awb_enabled=True,
        awb_mode=1,  # Sunny
        aec_enabled=True,
        aec_value=200,  # Shorter exposure
        agc_enabled=True,
        agc_gain=0,
        gain_ceiling=0,  # Minimum gain
    ),
}


def get_preset(name: str) -> CameraConfig:
    """Get a preset configuration by name."""
    if name not in PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(PRESETS.keys())}")
    # Return a copy to avoid mutation
    preset = PRESETS[name]
    return CameraConfig(
        frame_size=preset.frame_size,
        quality=preset.quality,
        brightness=preset.brightness,
        contrast=preset.contrast,
        saturation=preset.saturation,
        sharpness=preset.sharpness,
        hmirror=preset.hmirror,
        vflip=preset.vflip,
        awb_enabled=preset.awb_enabled,
        awb_mode=preset.awb_mode,
        aec_enabled=preset.aec_enabled,
        aec_value=preset.aec_value,
        agc_enabled=preset.agc_enabled,
        agc_gain=preset.agc_gain,
        gain_ceiling=preset.gain_ceiling,
    )


def list_presets() -> list[str]:
    """List available preset names."""
    return list(PRESETS.keys())
