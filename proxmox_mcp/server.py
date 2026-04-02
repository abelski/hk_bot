"""
Proxmox MCP (Model Context Protocol) Server
Provides MCP interface for Proxmox management operations
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
import asyncio

try:
    from proxmoxer import ProxmoxAPI
except ImportError:
    ProxmoxAPI = None

logger = logging.getLogger(__name__)


class ProxmoxMCPServer:
    """MCP Server for Proxmox management"""

    def __init__(
        self,
        host: str,
        user: str,
        token_name: str,
        token_value: str,
        verify_ssl: bool = False,
    ):
        """
        Initialize Proxmox MCP Server

        Args:
            host: Proxmox host URL (e.g., "192.168.0.31:8006")
            user: Proxmox user (e.g., "root@pam")
            token_name: API token name/ID
            token_value: API token secret
            verify_ssl: Whether to verify SSL certificates
        """
        self.host = host
        self.user = user
        self.token_name = token_name
        self.token_value = token_value
        self.verify_ssl = verify_ssl
        self.proxmox: Optional[ProxmoxAPI] = None

    def connect(self) -> bool:
        """Connect to Proxmox"""
        if not ProxmoxAPI:
            logger.error("proxmoxer not installed")
            return False

        try:
            self.proxmox = ProxmoxAPI(
                self.host,
                user=self.user,
                token_name=self.token_name,
                token_value=self.token_value,
                verify_ssl=self.verify_ssl,
            )
            logger.info(f"Connected to Proxmox at {self.host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from Proxmox"""
        self.proxmox = None
        logger.info("Disconnected from Proxmox")

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get list of all nodes"""
        if not self.proxmox:
            return []

        try:
            nodes = []
            for node in self.proxmox.nodes.get():
                nodes.append({
                    "node": node.get("node"),
                    "status": node.get("status"),
                    "uptime": node.get("uptime"),
                    "maxcpu": node.get("maxcpu"),
                    "maxmem": node.get("maxmem"),
                    "mem": node.get("mem"),
                    "cpu": node.get("cpu"),
                })
            return nodes
        except Exception as e:
            logger.error(f"Failed to get nodes: {e}")
            return []

    def get_vms(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of virtual machines"""
        if not self.proxmox:
            return []

        try:
            vms = []
            if node:
                for vm in self.proxmox.nodes(node).qemu.get():
                    vms.append({
                        "vmid": vm.get("vmid"),
                        "name": vm.get("name"),
                        "status": vm.get("status"),
                        "maxmem": vm.get("maxmem"),
                        "maxcpu": vm.get("maxcpu"),
                    })
            else:
                for node_obj in self.proxmox.nodes.get():
                    node_name = node_obj.get("node")
                    for vm in self.proxmox.nodes(node_name).qemu.get():
                        vms.append({
                            "node": node_name,
                            "vmid": vm.get("vmid"),
                            "name": vm.get("name"),
                            "status": vm.get("status"),
                        })
            return vms
        except Exception as e:
            logger.error(f"Failed to get VMs: {e}")
            return []

    def get_containers(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of LXC containers"""
        if not self.proxmox:
            return []

        try:
            containers = []
            if node:
                for container in self.proxmox.nodes(node).lxc.get():
                    containers.append({
                        "vmid": container.get("vmid"),
                        "hostname": container.get("hostname"),
                        "status": container.get("status"),
                        "maxmem": container.get("maxmem"),
                        "maxcpu": container.get("maxcpu"),
                    })
            else:
                for node_obj in self.proxmox.nodes.get():
                    node_name = node_obj.get("node")
                    for container in self.proxmox.nodes(node_name).lxc.get():
                        containers.append({
                            "node": node_name,
                            "vmid": container.get("vmid"),
                            "hostname": container.get("hostname"),
                            "status": container.get("status"),
                        })
            return containers
        except Exception as e:
            logger.error(f"Failed to get containers: {e}")
            return []

    def get_next_vmid(self) -> int:
        """Get the next available VMID"""
        return int(self.proxmox.cluster.nextid.get())

    def download_template(self, node: str, storage: str, template: str, location: str) -> Dict[str, Any]:
        """Download an LXC template from a URL"""
        try:
            task = self.proxmox.nodes(node).storage(storage).download_url.post(
                url=location,
                filename=template,
                content="vztmpl",
            )
            logger.info(f"Template download started: {task}")
            return {"success": True, "task": task}
        except Exception as e:
            logger.error(f"Failed to download template: {e}")
            return {"success": False, "error": str(e)}

    def create_container(
        self,
        node: str,
        vmid: int,
        hostname: str,
        ostemplate: str,
        memory: int = 512,
        cores: int = 1,
        storage: str = "local",
        disk_size: str = "8",
        password: str = "changeme",
        net0: str = "name=eth0,bridge=vmbr0,ip=dhcp",
        start: bool = True,
    ) -> Dict[str, Any]:
        """Create an LXC container"""
        try:
            task = self.proxmox.nodes(node).lxc.create(
                vmid=vmid,
                hostname=hostname,
                ostemplate=ostemplate,
                memory=memory,
                cores=cores,
                rootfs=f"{storage}:{disk_size}",
                password=password,
                net0=net0,
                start=int(start),
            )
            logger.info(f"Container {vmid} creation started: {task}")
            return {"success": True, "task": task, "vmid": vmid}
        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            return {"success": False, "error": str(e)}

    def start_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """Start a virtual machine"""
        if not self.proxmox:
            return {"success": False, "error": "Not connected"}

        try:
            self.proxmox.nodes(node).qemu(vmid).status.start.create()
            return {"success": True, "message": f"VM {vmid} started"}
        except Exception as e:
            logger.error(f"Failed to start VM: {e}")
            return {"success": False, "error": str(e)}

    def stop_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """Stop a virtual machine"""
        if not self.proxmox:
            return {"success": False, "error": "Not connected"}

        try:
            self.proxmox.nodes(node).qemu(vmid).status.stop.create()
            return {"success": True, "message": f"VM {vmid} stopped"}
        except Exception as e:
            logger.error(f"Failed to stop VM: {e}")
            return {"success": False, "error": str(e)}

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        if not self.proxmox:
            return {}

        try:
            cluster = self.proxmox.cluster.status.get()
            return {
                "cluster": cluster,
                "nodes": self.get_nodes(),
                "total_vms": len(self.get_vms()),
                "total_containers": len(self.get_containers()),
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {}


def create_mcp_server(
    host: Optional[str] = None,
    user: Optional[str] = None,
    token_name: Optional[str] = None,
    token_value: Optional[str] = None,
) -> ProxmoxMCPServer:
    """Factory function to create Proxmox MCP Server from environment"""
    host = host or os.getenv("PROXMOX_HOST", "localhost:8006")
    user = user or os.getenv("PROXMOX_USER", "root@pam")
    token_name = token_name or os.getenv("PROXMOX_TOKEN_NAME", "")
    token_value = token_value or os.getenv("PROXMOX_TOKEN_VALUE", "")

    return ProxmoxMCPServer(host, user, token_name, token_value)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Example usage
    server = create_mcp_server()
    if server.connect():
        print("Nodes:", server.get_nodes())
        print("VMs:", server.get_vms())
        print("Containers:", server.get_containers())
        server.disconnect()
