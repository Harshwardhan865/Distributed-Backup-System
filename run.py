import sys
from os_ken.base import app_manager
from os_ken.lib import hub

if __name__ == '__main__':
    # Ensure local directory can be scanned for backup_controller.py
    sys.path.append('.')

    # Initialize the OS-Ken application manager
    app_mgr = app_manager.AppManager.get_instance()
    
    # Load your application class
    app_mgr.load_apps(['backup_controller'])
    
    # Create required application contexts
    contexts = app_mgr.create_contexts()
    
    # Instantiate and start the application threads/greenlets
    app_mgr.instantiate_apps(**contexts)
    
    print("BackupController started successfully. Press Ctrl+C to exit.")
    
    # Keep the main process alive using os_ken's event hub
    try:
        while True:
            hub.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down controller...")
