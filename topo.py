from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

class FourPathTopo(Topo):
    def build(self):
        # Add hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24') #the client host
        h2 = self.addHost('h2', ip='10.0.0.2/24') #server host
        
        # Add switches: 1 ingress, 4 parallel intermediate, 1 egress
        s1 = self.addSwitch('s1', protocols='OpenFlow13') # Ingress Switch, meaning the first switch
        #the traffic encounters in the network
        s2 = self.addSwitch('s2', protocols='OpenFlow13') # Path 1 Switch
        s3 = self.addSwitch('s3', protocols='OpenFlow13') # Path 2 Switch
        s4 = self.addSwitch('s4', protocols='OpenFlow13') # Path 3 Switch
        s5 = self.addSwitch('s5', protocols='OpenFlow13') # Path 4 Switch
        s6 = self.addSwitch('s6', protocols='OpenFlow13') # Egress Switch
        
        # Host to Ingress Switch
        self.addLink(h1, s1, port1=1, port2=1) #creates communication link between h1 and s1
        #port1 is the 1st port of the host h1 and port2 is the 1st port of the switch s1

        #same applicable to the below part
        
        # 4 Parallel Paths from s1 to intermediate switches (ports 2, 3, 4, 5)
        self.addLink(s1, s2, port1=2, port2=1)
        self.addLink(s1, s3, port1=3, port2=1)
        self.addLink(s1, s4, port1=4, port2=1)
        self.addLink(s1, s5, port1=5, port2=1)
        
        # Intermediate switches to Egress Switch s6
        self.addLink(s2, s6, port1=2, port2=2)
        self.addLink(s3, s6, port1=2, port2=3)
        self.addLink(s4, s6, port1=2, port2=4)
        self.addLink(s5, s6, port1=2, port2=5)
        
        # Egress Switch to Host h2
        self.addLink(s6, h2, port1=1, port2=1)

def run():
    topo = FourPathTopo()
    net = Mininet(topo=topo, controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653), switch=OVSKernelSwitch)
    #OVSKernelSwitch handles packet switching in the linux kernel space
    net.start() #start up virtual network
    print("*** 4-Path Redundant Network Started")
    print("*** Testing initial connectivity...")
    net.pingAll() #tests connectivity across the topology
    CLI(net) #mininet CLI, can run commands in terminal
    net.stop() #if u exit

if __name__ == '__main__':
    setLogLevel('info')
    run()
