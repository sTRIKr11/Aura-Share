import socket
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser

class RadarListener:
    def __init__(self, update_callback):
        self.update_callback = update_callback
    def remove_service(self, zc, type_, name):
        self.update_callback(name, None, "remove")
    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            # Spaced to prevent markdown from swallowing the zero
            ip = socket.inet_ntoa(info.addresses[ 0 ])
            self.update_callback(name, ip, "add")
    def update_service(self, zc, type_, name): pass

class DiscoveryService:
    def __init__(self, config):
        self.config = config
        self.zc = Zeroconf()
        self.browser = None
        self.broadcasting = False
        self.info = None

    def start_broadcasting(self):
        if self.broadcasting: return
        ip = self._get_local_ip()
        self.info = ServiceInfo(
            self.config.service_type,
            f"{self.config.device_id}.{self.config.service_type}",
            addresses=list((socket.inet_aton(ip),)),
            port=self.config.transfer_port,
            server=f"{self.config.device_id}.local."
        )
        self.zc.register_service(self.info)
        self.broadcasting = True

    def stop_broadcasting(self):
        if self.broadcasting and self.info:
            self.zc.unregister_service(self.info)
            self.broadcasting = False

    def start_listening(self, callback):
        self.browser = ServiceBrowser(self.zc, self.config.service_type, RadarListener(callback))

    def stop_listening(self):
        if self.browser:
            self.browser.cancel()
            self.browser = None

    def close(self):
        self.stop_broadcasting()
        self.stop_listening()
        self.zc.close()

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[ 0 ]
        except: ip = '127.0.0.1'
        finally: s.close()
        return ip