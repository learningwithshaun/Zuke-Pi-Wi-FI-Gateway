import abc
import datetime
import logging
import subprocess
from typing import Dict, Optional
from flask import current_app

logger = logging.getLogger(__name__)


class GatewayService(abc.ABC):
    """Abstract base class for gateway network authorization."""

    @abc.abstractmethod
    def authorize_device(self, ip_address: str, duration_seconds: int = 28800) -> bool:
        pass

    @abc.abstractmethod
    def revoke_device(self, ip_address: str) -> bool:
        pass

    @abc.abstractmethod
    def is_authorized(self, ip_address: str) -> bool:
        pass

    @abc.abstractmethod
    def get_authorized_devices(self) -> Dict[str, datetime.datetime]:
        pass


class MockGatewayService(GatewayService):
    """
    Mock implementation for development and tests.
    Does not touch any system network interfaces or firewalls.
    """

    def __init__(self):
        self._authorized_ips: Dict[str, datetime.datetime] = {}
        logger.info("[MockGatewayService] Initialized in development mode.")

    def authorize_device(self, ip_address: str, duration_seconds: int = 28800) -> bool:
        if not ip_address:
            return False
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=duration_seconds)
        self._authorized_ips[ip_address] = expires_at
        logger.info("[MockGatewayService] Device %s authorized until %s", ip_address, expires_at.isoformat())
        return True

    def revoke_device(self, ip_address: str) -> bool:
        if ip_address in self._authorized_ips:
            del self._authorized_ips[ip_address]
            logger.info("[MockGatewayService] Device %s access revoked", ip_address)
            return True
        return False

    def is_authorized(self, ip_address: str) -> bool:
        if not ip_address:
            return False
        expires_at = self._authorized_ips.get(ip_address)
        if not expires_at:
            return False
        now = datetime.datetime.now(datetime.timezone.utc)
        if now > expires_at:
            del self._authorized_ips[ip_address]
            logger.info("[MockGatewayService] Device %s authorization expired", ip_address)
            return False
        return True

    def get_authorized_devices(self) -> Dict[str, datetime.datetime]:
        now = datetime.datetime.now(datetime.timezone.utc)
        expired = [ip for ip, exp in self._authorized_ips.items() if now > exp]
        for ip in expired:
            del self._authorized_ips[ip]
        return dict(self._authorized_ips)

    def clear_all(self):
        self._authorized_ips.clear()


class NftablesGatewayService(GatewayService):
    """
    Production implementation for Linux / Raspberry Pi using nftables set.
    """

    def __init__(self, table_name: str = "zuke", set_name: str = "authenticated_ips"):
        self.table_name = table_name
        self.set_name = set_name
        logger.info("[NftablesGatewayService] Initialized table=%s set=%s", table_name, set_name)

    def authorize_device(self, ip_address: str, duration_seconds: int = 28800) -> bool:
        if not ip_address:
            return False
        cmd = [
            "nft", "add", "element", "inet", self.table_name, self.set_name,
            f"{{ {ip_address} timeout {duration_seconds}s }}"
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("[NftablesGatewayService] Authorized IP %s (%ds)", ip_address, duration_seconds)
            return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error("[NftablesGatewayService] Error adding IP %s: %s", ip_address, e)
            return False

    def revoke_device(self, ip_address: str) -> bool:
        if not ip_address:
            return False
        cmd = ["nft", "delete", "element", "inet", self.table_name, self.set_name, f"{{ {ip_address} }}"]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("[NftablesGatewayService] Removed IP %s", ip_address)
            return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error("[NftablesGatewayService] Error removing IP %s: %s", ip_address, e)
            return False

    def is_authorized(self, ip_address: str) -> bool:
        if not ip_address:
            return False
        cmd = ["nft", "get", "element", "inet", self.table_name, self.set_name, f"{{ {ip_address} }}"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            return res.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_authorized_devices(self) -> Dict[str, datetime.datetime]:
        return {}


_gateway_instance: Optional[GatewayService] = None


def get_gateway_service(app=None) -> GatewayService:
    global _gateway_instance
    if _gateway_instance is not None:
        return _gateway_instance

    gateway_type = 'mock'
    if app is not None:
        gateway_type = app.config.get('GATEWAY_TYPE', 'mock')
    elif current_app:
        gateway_type = current_app.config.get('GATEWAY_TYPE', 'mock')

    if gateway_type == 'nftables':
        _gateway_instance = NftablesGatewayService()
    else:
        _gateway_instance = MockGatewayService()

    return _gateway_instance


def reset_gateway_service_instance():
    global _gateway_instance
    _gateway_instance = None
