import socket
import threading
import struct
import os
import time
import json
import shutil

class TransferServer:
    def __init__(self, config_obj):
        self.config = config_obj
        self.running = False
        self.server_socket = None
        self.armed_files = list()
        self.is_armed = False
        self.cancel_flag = False
        self.active_connections = list()
        self.stats = {"status": "IDLE", "progress": 0.0, "speed_bps": 0.0, "current_file": ""}

    def arm_payload(self, paths, is_folder=False):
        self.armed_files = list()
        self.cancel_flag = False
        self.stats["status"] = "PREPARING PAYLOAD..."
        if is_folder:
            folder_path = paths[ 0 ]
            zip_name = os.path.join(self.config.staging_dir, os.path.basename(folder_path))
            shutil.make_archive(zip_name, 'zip', folder_path)
            self.armed_files.append(zip_name + ".zip")
        else:
            self.armed_files = list(paths)
            
        self.stats.update({"status": "ARMED (READY TO HOST)", "progress": 0.0, "current_file": f"{len(self.armed_files)} items ready"})
        self.start_hosting()

    def start_hosting(self):
        if len(self.armed_files) == 0: return
        self.is_armed = True
        self.cancel_flag = False
        self.stats["status"] = "HOSTING... WAITING FOR GRAB"
        
        if not self.running:
            self.running = True
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(('0.0.0.0', self.config.transfer_port))
                self.server_socket.listen(10)
                threading.Thread(target=self._host_loop, daemon=True).start()
            except Exception as e:
                self.stats["status"] = "ERROR: PORT IN USE"
                self.running = False

    def _host_loop(self):
        while self.running:
            try:
                client, addr = self.server_socket.accept()
                threading.Thread(target=self._serve_client, args=(client,), daemon=True).start()
            except: break

    def _recvall(self, sock, n):
        data = bytearray()
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
                if not packet: return None
                data.extend(packet)
            except: return None
        return data

    def _serve_client(self, client):
        self.active_connections.append(client)
        try:
            command_bytes = self._recvall(client, 12)
            if not command_bytes: return
            command = command_bytes.decode('utf-8').strip('\x00')
            
            if "PULL_REQUEST" in command and self.is_armed:
                client.sendall(b"ACCEPTED")
                time.sleep(0.2) 
                metadata = [{"name": os.path.basename(f), "size": os.path.getsize(f)} for f in self.armed_files]
                meta_bytes = json.dumps(metadata).encode('utf-8')
                client.sendall(struct.pack('!I', len(meta_bytes)))
                client.sendall(meta_bytes)
                
                total_bytes = sum(f["size"] for f in metadata)
                sent_bytes = 0
                start_time = time.time()

                for file_path in self.armed_files:
                    if self.cancel_flag: break
                    self.stats["current_file"] = f"Sending to Receiver..."
                    with open(file_path, 'rb') as f:
                        while True:
                            chunk = f.read(1048576)
                            if not chunk: break
                            if self.cancel_flag: break
                            client.sendall(chunk)
                            sent_bytes += len(chunk)
                            elapsed = time.time() - start_time
                            self.stats["progress"] = (sent_bytes / total_bytes) if total_bytes > 0 else 1
                            self.stats["speed_bps"] = sent_bytes / elapsed if elapsed > 0 else 0
                if not self.cancel_flag: self.stats["status"] = "HOSTING (DELIVERED TO RECEIVER)"
            else:
                client.sendall(b"DENIED  ")
        except: pass
        finally:
            try: client.close()
            except: pass
            if client in self.active_connections: self.active_connections.remove(client)

    def pull_from_radar(self, target_ips):
        if not target_ips: return
        self.cancel_flag = False
        self.stats["status"] = "GRABBING FILES..."
        for ip in target_ips:
            threading.Thread(target=self._execute_pull, args=(ip,), daemon=True).start()

    def _execute_pull(self, target_ip):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(15.0) 
            self.active_connections.append(client)
            client.connect((target_ip, self.config.transfer_port))
            client.sendall(b"PULL_REQUEST")
            
            response = self._recvall(client, 8)
            if not response or response!= b"ACCEPTED":
                self.stats["status"] = "SENDER NOT READY YET"
                client.close()
                return
            
            client.settimeout(None) 
            
            meta_len_bytes = self._recvall(client, 4)
            if not meta_len_bytes: return
            meta_len = struct.unpack('!I', meta_len_bytes)[ 0 ]
            
            meta_json_bytes = self._recvall(client, meta_len)
            if not meta_json_bytes: return
            meta_json = meta_json_bytes.decode('utf-8')
            
            files_metadata = json.loads(meta_json)
            total_bytes = sum(f["size"] for f in files_metadata)
            received = 0
            start_time = time.time()
            downloaded = list()

            for file_info in files_metadata:
                if self.cancel_flag: break
                name, size = file_info["name"], file_info["size"]
                self.stats["current_file"] = name
                path = os.path.join(self.config.staging_dir, name)
                
                file_recv = 0
                with open(path, 'wb') as f:
                    while file_recv < size:
                        if self.cancel_flag: break
                        chunk = client.recv(min(1048576, size - file_recv))
                        if not chunk: break
                        f.write(chunk)
                        file_recv += len(chunk)
                        received += len(chunk)
                        elapsed = time.time() - start_time
                        self.stats["progress"] = (received / total_bytes) if total_bytes > 0 else 1
                        self.stats["speed_bps"] = received / elapsed if elapsed > 0 else 0
                if not self.cancel_flag: downloaded.append(path)
                
            if not self.cancel_flag:
                self.stats["status"] = "RECEIVED SUCCESSFULLY"
                self.config.latest_received = downloaded 
        except ConnectionRefusedError:
            if not self.cancel_flag: self.stats["status"] = "SENDER NOT HOSTING YET"
        except Exception as e: 
            if not self.cancel_flag: self.stats["status"] = "CONNECTION LOST"
        finally:
            try: client.close()
            except: pass
            if client in self.active_connections: self.active_connections.remove(client)

    def cancel_transfer(self):
        self.cancel_flag = True
        self.is_armed = False
        self.stats["status"] = "CANCELLED"
        for conn in self.active_connections:
            try: conn.close()
            except: pass
        self.active_connections.clear()
        self.running = False
        if self.server_socket:
            try: self.server_socket.close()
            except: pass