from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet, ether_types, ipv4, arp

class BackupController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(BackupController, self).__init__(*args, **kwargs)
        self.datapaths = {} #keeps track of all the switches
        # Track status of the 4 parallel paths on s1 (ports 2, 3, 4, 5)
        self.path_status = {2: True, 3: True, 4: True, 5: True}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath 
        self.datapaths[dp.id] = dp
        parser = dp.ofproto_parser #creates rules for routing table
        ofproto = dp.ofproto

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, match, actions) #adds rule to flow table
        self.logger.info("Switch connected: Dpid=%s", dp.id)

    def add_flow(self, dp, priority, match, actions):
        parser = dp.ofproto_parser
        ofproto = dp.ofproto
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=priority, match=match, instructions=instructions)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        port_no = msg.desc.port_no
        if dp.id == 1 and port_no in [2, 3, 4, 5]: 
            # Check both link state down and port config down for maximum reliability
            is_down = (msg.desc.state & ofproto.OFPPS_LINK_DOWN) or (msg.desc.config & ofproto.OFPPC_PORT_DOWN)
            
            if is_down:
                self.path_status[port_no] = False
                self.logger.warning(">>> LINK DOWN on s1 port %s. Clearing all switch flow tables for rerouting.", port_no)
            else:
                self.path_status[port_no] = True
                self.logger.info(">>> LINK UP on s1 port %s", port_no)

        # Clear IP flow entries across ALL switches so both forward and return paths re-learn correctly
        for datapath in self.datapaths.values():
            d_parser = datapath.ofproto_parser
            d_ofproto = datapath.ofproto
            mod = d_parser.OFPFlowMod(
                datapath=datapath,
                command=d_ofproto.OFPFC_DELETE,
                match=d_parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP)
            ) #modification message, tells the info about the changes
            datapath.send_msg(mod) 

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        parser = dp.ofproto_parser
        ofproto = dp.ofproto
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dpid = dp.id

        # Flood ARP requests across the topology so hosts can discover each other
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=msg.data)
            dp.send_msg(out)
            return

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt is None:
            return

        src = ip_pkt.src
        dst = ip_pkt.dst
        out_port = None

        # Robust Bi-directional Multi-Path Routing Logic
        if dpid == 1:
            if dst == "10.0.0.2":
                # Forward to h2: pick first healthy path (ports 2, 3, 4, 5)
                for p in [2, 3, 4, 5]:
                    if self.path_status[p]:
                        out_port = p
                        break
            elif dst == "10.0.0.1":
                # Return traffic coming back to h1
                out_port = 1

        elif dpid in [2, 3, 4, 5]:
            # Intermediate switches: forward to s6 (port 2) if coming from s1 (port 1), else back to s1
            out_port = 2 if in_port == 1 else 1

        elif dpid == 6:
            if dst == "10.0.0.2":
                # Forward to h2 (port 1)
                out_port = 1
                # Dynamically install reverse flow on s6 so return traffic follows the exact same path back
                if in_port in [2, 3, 4, 5]:
                    rev_match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=dst, ipv4_dst=src)
                    rev_actions = [parser.OFPActionOutput(in_port)]
                    self.add_flow(dp, 10, rev_match, rev_actions)
            elif dst == "10.0.0.1":
                out_port = in_port if in_port in [2, 3, 4, 5] else 2

        if out_port is None:
            return

        actions = [parser.OFPActionOutput(out_port)]
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src, ipv4_dst=dst)

        self.add_flow(dp, 10, match, actions)
        dp.send_msg(parser.OFPPacketOut(datapath=dp, buffer_id=ofproto.OFP_NO_BUFFER, in_port=in_port, actions=actions, data=msg.data))
