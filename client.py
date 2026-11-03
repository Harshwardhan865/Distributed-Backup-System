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
        chunk = sock.recv(size - len(data)) #a chunk of data, size - len(data) = number to bytes to be received yet
        if not chunk: #if there's no data 
            raise ConnectionError("Server closed the connection unexpectedly") 
        data.extend(chunk) #append the bytes gotten in chunk to the byte array container.
    return bytes(data)


def backup_file(sock, filename, file_size):
    """Send the filename length, filename, and file size."""
    sock.sendall(struct.pack("!I", len(filename))) #sends the filename length in bytes
    sock.sendall(filename) #the actual file name
    sock.sendall(struct.pack("!Q", file_size)) #the size of the file in bytes


def send_file(file_path):
    path = Path(file_path).expanduser() #path object, turns your string path into an actual path
    #expanduser makes your path absolute in nature.
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    filename = path.name.encode("utf-8") #encodes file name into raw streams of bytes for server to understand
    if not 1 <= len(filename) <= 255: #condition to check if filename size within permitted limit
        raise ValueError("Filename must be between 1 and 255 UTF-8 bytes")

    file_size = path.stat().st_size
    digest = hashlib.sha256() #makes a SHA-256 object, meaning it generates a 256 unique 
    #signature for your data, like encrypting it

    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=15) as sock:
        # Opcode 1 tells the server this is a backup/upload request.
        sock.sendall(struct.pack("!I", 1)) #an opcode prefix to denote that the connection is for a backup request
        backup_file(sock, filename, file_size) #call the backup function

        with path.open("rb") as source: #open binary object in read mode
            while True:
                chunk = source.read(BUFFER_SIZE) #read a chunk of data from source of size buffer_size
                if not chunk: #if NULL
                    break #no point in continuing, so break out of the loop
                sock.sendall(chunk) #send chunk to server
                digest.update(chunk)

        original_hash = digest.hexdigest() #this gives the checksum strng after hashing/encrypting the data
        #using the hashlib.sha256() function, 
        server_hash = receive_exactly(sock, 64).decode("ascii") #checks whether all bytes have been received by server,
        #and decodes it to a normal py str , server does its own hash and sends to client -> checks whether hashes
    #are matching, if they do -> sent successfully, code is below

    print("\nTransfer completed!")
    print(f"Original SHA-256: {original_hash}")
    print(f"Server SHA-256:   {server_hash}")
    if original_hash == server_hash:
        print("INTEGRITY CHECK: PASSED")
    else:
        print("INTEGRITY CHECK: FAILED")


def delete_file(file_path):
    path = Path(file_path).expanduser() #path object
    filename = path.name.encode("utf-8") #encoding filename

    if not 1 <= len(filename) <= 255: #permitted range
        raise ValueError("Filename must be between 1 and 255 UTF-8 bytes")

    # The server deletes by filename from its backup directory. The local
    # source file does not need to exist for a remote deletion request.
    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=15) as sock:
        # Opcode 2 tells the server this is a deletion request.
        sock.sendall(struct.pack("!I", 2)) #an opcode prefix to denote that the connection is for a deletion request
        sock.sendall(struct.pack("!I", len(filename))) #length of file name
        sock.sendall(filename) #raw bytes stream

        status_response = sock.recv(1) #server's response to the file
        if status_response: #if OK
            status = struct.unpack("!B", receive_exactly(sock, 1))[0] #converts status_response byte object to translate it
            #unpack returns tuple, and [0] takes only the opcode value from those elements
            if status == 1:
                print(f"\nSuccessfully deleted the file {path.name}!\n") #path.name extracts only the filename in the path object
            else:
                print(f"\nERROR: {path.name} was not found on the backup server.\n")


def list_files():
    """Request and display the files stored in the server's backup directory."""
    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=15) as sock:
        # Opcode 3 tells the server this is a file-listing request.
        sock.sendall(struct.pack("!I", 3)) 

        response_length = struct.unpack("!I", receive_exactly(sock, 4))[0] #converts response_length byte object to translate it
        #to get the length
        response = receive_exactly(sock, response_length) #checks whether all bytes received of size reponse_length
        files = json.loads(response.decode("utf-8")) #decodes the byte object

    print("\n========== BACKUP FILE LIST ==========")
    if not files:
        print("No backed-up files found.")
    else:
        for index, item in enumerate(files, start=1):
            print(f"{index}. {item['name']:<30} {format_size(item['size'])}")
        print(f"\nTotal files: {len(files)}")
    print("======================================\n")


def format_size(size):
    units = ["bytes", "KB", "MB", "GB", "TB"] #for the sake of mentioning the file size next to the bytes.
    value = float(size)
    for unit in units:
        if value < 1024 or unit == "TB":  #converting to most accurate representation of size 
            return f"{int(value)} {unit}" if unit == "bytes" else f"{value:.2f} {unit}"
        value /= 1024

def main():
    while True:
        try: #menu driven program, options 
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
                for file_path in file_paths: #file path container / list
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
