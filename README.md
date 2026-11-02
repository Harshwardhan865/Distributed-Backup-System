# Distributed Backup System Using TCP and SDN

## 1. Project Overview

The Distributed Backup System
          
## 2. Problem Statement:
          Implement a distributed backup application where client transfer files to the backup servers through the TCP.
          SDN should dynamically select suitable paths and support the recovery during the links failures.
## 3. Objectives

- Enable multiple clients to upload files.
- Transfer files using TCP.
- Maintain file integrity using SHA-256 hashing.
- Allow users to list and delete backup files.
- Use SDN for network path management.

## 4. Network Architecture

The following figure illustrates the network architecture of the Distributed Backup System.

![Network Architecture](network-architecture.png)


## 5. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Client-server and controller implementation |
| TCP Socket Programming | Reliable file transfer |
| Mininet | Network topology emulation |
| SDN | Dynamic network path management |
| OpenFlow | Communication between controller and switches |
| Ubuntu Linux | Development environment |
| SHA-256 | File integrity verification |




## 6. Installation Requirements

The following tools and software are required to run the project:

- Ubuntu Linux
- Python 3
- Mininet
- OpenFlow-compatible SDN controller
- Required Python libraries




##7. Execution Instructions

Follow the steps below to execute the Distributed Backup System in the Ubuntu environment

Step 1: Start the SDN Controller

     Command 1:

                  source ~/ryu-env/bin/activate
                      Explanation:

                           ryu-env is the Python virtual environment.

                           bin/activate activates the virtual environment.

                           Purpose: This command activates the Python environment containing the dependencies required by the controller.


     Command 2:

                python3 run.py

                       Explanation:

                            python3 invokes the Python 3 interpreter.

                            run.py is the Python script used to start the backup controller.

                       Purpose: This command starts the controller process.

                            Expected Output:

                                BackupController started successfully. Press Ctrl+C to exit.

       Keep this terminal open while running the application.

Step 2: Start the Mininet Network Topology

Open a second terminal.


        Command 1:

               sudo python3 topo.py

                      Explanation:

                           sudo executes the command with administrator privileges.

                           python3 runs the Python 3 interpreter.

                           topo.py contains the Mininet topology configuration.


                       Purpose: Mininet requires elevated privileges to create virtual network interfaces, switches and links. This command starts the emulated network topology.
 
                             The topology consists of:

                                 Two hosts: h1 and h2.

                                 Six switches: s1, s2, s3, s4, s5 and s6.

                                 Multiple alternative network paths between the source and destination hosts.

                                 After successful execution, the Mininet command-line interface (CLI) appears.


     command 2:
                 

                 At the Mininet CLI, execute:

                     h2 python3 server.py &

                          Explanation:

                              h2 specifies that the command should execute on host h2.

                              python3 invokes the Python interpreter.

                              server.py contains the backup server implementation.

                              & runs the server process in the background.

                        Purpose: This command starts the backup server on host h2. The server waits for incoming TCP connections and processes file backup requests from clients.

    command 3:
              Run the Client Application

                At the Mininet CLI, execute:

                      h1 python3 client.py

                            Explanation:

                               h1 specifies that the command should execute on host h1.

                               python3 invokes the Python interpreter.

                               client.py contains the client-side application logic.

                          Purpose: This command starts the client application on host h1. The client communicates with the backup server using TCP.

                             The application displays an interactive menu through which users can perform backup operations


 Network Failure Testing and Flow Verification

To test network failure handling and inspect the forwarding rules installed by the SDN controller, Mininet provides the following commands.

provides the following commands.

         1. Simulate a Network Link Failure

                    sh1 ovs-ofctl mod-port s1 s1-eth2 down -O OpenFlow13

                          Explanation:

                                     sh executes a shell command from the Mininet CLI.

                                     ovs-ofctl is a utility used to manage Open vSwitch.

                                     mod-port modifies the status of a switch port.

                                     s1 specifies the switch.

                                     s1-eth2 specifies the interface to be disabled.

                                     down disables the selected port.

                                    -O OpenFlow13 specifies OpenFlow version 1.3.

                         Purpose: This command disables a port on switch s1, simulating a network link failure. 
                                  The SDN controller can detect the failure and select an alternative path if failure-recovery logic is implemented.

3. Display Flow Entries


                  sh ovs-ofctl dump-flows s1 -O OpenFlow13

                       Explanation:

                                   sh executes the command through the shell.

                                   ovs-ofctl communicates with Open vSwitch.

                                   dump-flows displays the flow entries installed in the switch.

                                   s1 specifies the switch whose flow entries are being inspected.

                                   -O OpenFlow13 specifies OpenFlow version 1.3.

                      Purpose: This command displays the forwarding rules installed in switch s1.
                                These rules contain packet-matching conditions and actions that determine how network traffic is handled.

                 Note:
                     The above commands are used to simulate failures on different network paths by disabling specific interfaces of switch s1.

                                  First failure: Disables s1-eth2 to test the first alternative path.

                                  Second failure: Disables s1-eth3 to test the second alternative path.

                                  Third failure: Disables s1-eth4 to test the third alternative path.



## Team Members

| Sl. No. | Name           | SRN           |
| ------- | -------------- | ------------- |
| 1       | Harshwardhan   | PES2UG24CS189 |
| 2       | Akshaya Dasari | PES2UG25CS049 |
| 3       | Ahalya Sharma  | PES2UG25CS038 |
