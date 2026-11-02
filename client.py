import hashlib
import json
import socket
import struct
from pathlib import Path

# Keep this address consistent with the IP of the Mininet backup server.
SERVER_HOST = "10.0.0.2"
SERVER_PORT = 5001
BUFFER_SIZE = 4096


def receive_exactly(sock, size):
    """Receive exactly size bytes from the TCP socket."""
    data = bytearray() #raw stream of bytes
    while len(data) < size: 
        chunk = sock.recv(size - len(data)) #a chunk of data
        if not chunk:
            raise ConnectionError("Server closed the connection unexpectedly")
        data.extend(chunk)
    return bytes(data)


def backup_file(sock, filename, file_size):
    """Send the filename length, filename, and file size."""
    sock.sendall(struct.pack("!I", len(filename)))
    sock.sendall(filename)
    sock.sendall(struct.pack("!Q", file_size))


def send_file(file_path):
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    filename = path.name.encode("utf-8")
    if not 1 <= len(filename) <= 255:
        raise ValueError("Filename must be between 1 and 255 UTF-8 bytes")

    file_size = path.stat().st_size
    digest = hashlib.sha256()

    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=15) as sock:
        # Opcode 1 tells the server this is a backup/upload request.
        sock.sendall(struct.pack("!I", 1))
        backup_file(sock, filename, file_size)

        with path.open("rb") as source:
            while True:
                chunk = source.read(BUFFER_SIZE)
                if not chunk:
                    break
                sock.sendall(chunk)
                digest.update(chunk)

        original_hash = digest.hexdigest()
        server_hash = receive_exactly(sock, 64).decode("ascii")

    print("\nTransfer completed!")
    print(f"Original SHA-256: {original_hash}")
    print(f"Server SHA-256:   {server_hash}")
    if original_hash == server_hash:
        print("INTEGRITY CHECK: PASSED")
    else:
        print("INTEGRITY CHECK: FAILED")


def delete_file(file_path):
    path = Path(file_path).expanduser()
    filename = path.name.encode("utf-8")

    if not 1 <= len(filename) <= 255:
        raise ValueError("Filename must be between 1 and 255 UTF-8 bytes")

    # The server deletes by filename from its backup directory. The local
    # source file does not need to exist for a remote deletion request.
    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=15) as sock:
        # Opcode 2 tells the server this is a deletion request.
        sock.sendall(struct.pack("!I", 2))
        sock.sendall(struct.pack("!I", len(filename)))
        sock.sendall(filename)

        status = struct.unpack("!B", receive_exactly(sock, 1))[0]
        if status == 1:
            print(f"\nSuccessfully deleted the file {path.name}!\n")
        else:
            print(f"\nERROR: {path.name} was not found on the backup server.\n")


def list_files():
    """Request and display the files stored in the server's backup directory."""
    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=15) as sock:
        # Opcode 3 tells the server this is a file-listing request.
        sock.sendall(struct.pack("!I", 3))

        response_length = struct.unpack("!I", receive_exactly(sock, 4))[0]
        response = receive_exactly(sock, response_length)
        files = json.loads(response.decode("utf-8"))

    print("\n========== BACKUP FILE LIST ==========")
    if not files:
        print("No backed-up files found.")
    else:
        for index, item in enumerate(files, start=1):
            print(f"{index}. {item['name']:<30} {format_size(item['size'])}")
        print(f"\nTotal files: {len(files)}")
    print("======================================\n")


def format_size(size):
    units = ["bytes", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == "TB":
            return f"{int(value)} {unit}" if unit == "bytes" else f"{value:.2f} {unit}"
        value /= 1024


def main():
    while True:
        try:
            choice = int(input(
                "Enter the number for the corresponding function:\n"
                "1. Backup\n"
                "2. Delete\n"
                "3. List\n"
                "4. Exit\n"
            ))
        except ValueError:
            print("Please enter a valid number.\n")
            continue

        try:
            if choice == 1:
                #multiple file paths as a list of elements
                file_paths = input("Enter the path(s) of the file to back up (separate by spaces please): ").strip().strip('"').split()
                #traverse the list for each file path
                for file_path in file_paths:
                    try:
                        #will send the file through TCP connection
                        send_file(file_path)
                    except (OSError, ValueError) as e:
                        #error handling
                        print(f"Failed to send file: {e}")
            elif choice == 2:
                #enter file path for deletion
                file_path = input("Enter the name/path of the file to delete from backup: ").strip().strip('"')
                delete_file(file_path)
            elif choice == 3:
                list_files()
            elif choice == 4:
                print("Exiting.")
                break
            else:
                #default statement for wrong choice
                print("Invalid choice. Please enter 1, 2, 3, or 4.\n")
        except (OSError, ValueError, ConnectionError, json.JSONDecodeError) as error:
            print(f"Operation failed: {error}")


if __name__ == "__main__":
    main()
