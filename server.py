import hashlib
import json
import socket
import struct
from pathlib import Path

HOST = "0.0.0.0"
PORT = 5001
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
BUFFER_SIZE = 4096


def receive_exactly(conn, size):
    """Read exactly size bytes from a TCP connection."""
    data = bytearray()
    while len(data) < size:
        chunk = conn.recv(min(BUFFER_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError("Connection closed unexpectedly")
        data.extend(chunk)
    return bytes(data)


def receive_filename(conn):
    """Receive and validate a filename sent by the client."""
    name_length = struct.unpack("!I", receive_exactly(conn, 4))[0]
    if not 1 <= name_length <= 255:
        raise ValueError("Invalid filename length")

    filename = receive_exactly(conn, name_length).decode("utf-8")
    filename = Path(filename).name  # Prevent directory traversal.
    if filename in ("", ".", ".."):
        raise ValueError("Invalid filename")
    return filename


def receive_file(conn):
    filename = receive_filename(conn)
    file_size = struct.unpack("!Q", receive_exactly(conn, 8))[0]

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    destination = BACKUP_DIR / filename
    digest = hashlib.sha256()
    remaining = file_size

    with destination.open("wb") as output:
        while remaining > 0:
            chunk = conn.recv(min(BUFFER_SIZE, remaining))
            if not chunk:
                raise ConnectionError("File transfer interrupted")
            output.write(chunk)
            digest.update(chunk)
            remaining -= len(chunk)

    file_hash = digest.hexdigest()
    print(f"Received: {filename} ({file_size} bytes)", flush=True)
    print(f"SHA-256: {file_hash}", flush=True)
    conn.sendall(file_hash.encode("ascii"))


def delete_file(conn):
    filename = receive_filename(conn)
    target_path = BACKUP_DIR / filename

    if target_path.is_file():
        target_path.unlink()
        conn.sendall(struct.pack("!B", 1))
        print(f"Deleted file: {filename}", flush=True)
    else:
        conn.sendall(struct.pack("!B", 0))
        print(f"Delete failed; no file called {filename}", flush=True)


def list_files(conn):
    """Send a JSON list of backed-up filenames and their sizes."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    files = []

    for path in sorted(BACKUP_DIR.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file():
            files.append({
                "name": path.name,
                "size": path.stat().st_size
            })

    payload = json.dumps(files).encode("utf-8")
    conn.sendall(struct.pack("!I", len(payload)))
    conn.sendall(payload)


def handle_client(conn, address):
    with conn:
        print(f"Connected by {address}", flush=True)
        try:
            # Every request starts with a 4-byte opcode:
            # 1 = backup, 2 = delete, 3 = list.
            opcode = struct.unpack("!I", receive_exactly(conn, 4))[0]

            if opcode == 1:
                receive_file(conn)
            elif opcode == 2:
                delete_file(conn)
            elif opcode == 3:
                list_files(conn)
            else:
                raise ValueError(f"Unknown opcode received: {opcode}")

        except (ConnectionError, OSError, ValueError, UnicodeDecodeError) as error:
            print(f"Request failed: {error}", flush=True)


def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"TCP backup server listening on port {PORT}", flush=True)

        while True:
            conn, address = server.accept()
            handle_client(conn, address)


if __name__ == "__main__":
    main()
