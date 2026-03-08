# mara_host/core/settings.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from ..config.pin_config import ENC0_A, ENC0_B

if TYPE_CHECKING:
    import yaml


def _load_yaml():
    """Lazy-load yaml module for startup time optimization."""
    import yaml
    return yaml


@dataclass
class TransportSettings:
    type: str = "tcp"          # "tcp" | "serial" | "ble" | "mqtt"
    host: Optional[str] = None
    port: Optional[int] = None
    serial_port: Optional[str] = None
    baudrate: int = 115200
    ble_name: Optional[str] = None


@dataclass
class MQTTSettings:
    """MQTT transport configuration."""
    enabled: bool = False
    broker_host: str = "localhost"
    broker_port: int = 1883
    fallback_broker: Optional[str] = None
    fallback_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    node_id: str = "node0"
    heartbeat_timeout_s: float = 5.0


@dataclass
class FeatureSettings:
    telemetry: bool = True
    encoder: bool = False
    motion: bool = False
    modes: bool = True
    camera: bool = False
    # easy to extend later:
    # gpio: bool = False
    # pwm: bool = False
    # servo: bool = False
    # stepper: bool = False
    # dc_motor: bool = False


@dataclass
class EncoderDefaults:
    encoder_id: int = 0
    # 👇 these were `pin_a: int(ENC0_A)` which *calls* int() instead of type-hinting
    pin_a: int = ENC0_A
    pin_b: int = ENC0_B


@dataclass
class HostSettings:
    transport: TransportSettings
    features: FeatureSettings
    encoder_defaults: EncoderDefaults
    mqtt: MQTTSettings

    @classmethod
    def load(cls, profile: str = "default") -> "HostSettings":
        base = Path(__file__).resolve().parent.parent
        cfg_path = base / "config" / f"robot_profile_{profile}.yaml"

        yaml = _load_yaml()
        data = yaml.safe_load(cfg_path.read_text())

        transport = TransportSettings(**data["transport"])
        features = FeatureSettings(**data["features"])
        encoder_defaults = EncoderDefaults(
            **data.get("encoder_defaults", {})
        )
        mqtt = MQTTSettings(**data.get("mqtt", {}))

        return cls(
            transport=transport,
            features=features,
            encoder_defaults=encoder_defaults,
            mqtt=mqtt,
        )
