import os
import socket
import tempfile
import random

class Config:
    def __init__(self):
        self.device_id = f"AuraShare_{socket.gethostname()}_{random.randint(100,999)}"
        self.transfer_port = 5001 
        self.service_type = "_aurashare._tcp.local."
        
        base_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'AuraShare')
        self.save_dir = base_path
        self.staging_dir = os.path.join(tempfile.gettempdir(), "AuraShare_Staging")
        self.latest_received = None
        
        for directory in [self.save_dir, self.staging_dir]:
            os.makedirs(directory, exist_ok=True)