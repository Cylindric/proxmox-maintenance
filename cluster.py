import sys
import json
import requests
import time
from loguru import logger
from proxmoxer import ProxmoxAPI

class Cluster:
    def __init__(self, server: str):
        self._proxmox: ProxmoxAPI = None
        self._host: str = server
        self._server: str = f"https://{server}:8006"

        self._auth_cookie: str = None
        self._csrf_token: str = None

    def login(self, username: str, password: str):
        self._proxmox = ProxmoxAPI(self._host, user=username, password=password, verify_ssl=False)
        url = f'{self._server}/api2/json/access/ticket'
        data = {'username': username, 'password': password}
        response = requests.post(url, data=data, verify=False)
        if not response.ok:
            logger.error(f"{response.status_code}, {response.reason}")
            sys.exit(2)

        logger.success(f"Token successfully retrieved.")
        self._auth_cookie = {'PVEAuthCookie': (response.json()['data']['ticket'])}
        self._csrf_token = {'CSRFPreventionToken': (response.json()['data']['CSRFPreventionToken'])}
        logger.debug(self._auth_cookie)
        logger.debug(self._csrf_token)
    
    def get_nodes(self):
        nodes = self._proxmox.nodes.get() 
        nodes = sorted(nodes, key=lambda d: d['node']) 
        all_vms = self.get_vms()
        for node in nodes:
            node["running_vms"] = list(
                {"name":vm["name"], "status":vm["status"]}
                for vm in all_vms
                if vm["node"] == node["node"]
                and vm["status"] == "running"
            )

            node["running_vms"] = sorted(node["running_vms"], key=lambda d: d["name"])
        return nodes

    def get_vms(self):
        vms = self._proxmox.cluster.resources.get()
        vms = list(vm for vm in vms if vm["type"] == "qemu")
        vms = sorted(vms, key=lambda d: d['name']) 
        return vms
    
    def get_groups(self, name: str = None):
        groups = self._proxmox.cluster.ha.groups.get()
        groups = sorted(groups, key=lambda d: d['group'])

        if name:
            groups = list(g for g in groups if g["group"] == name)

        # Get a list of the VMs and which group they're in
        resources = self._proxmox.cluster.ha.resources.get()
        resources = sorted(resources, key=lambda d: d['sid'])

        # The resources only have a VM SID, so expand that with an actual VM object
        vms = self.get_vms()
        for group in groups:
            group["vms"] = []

            for sid in (resource for resource in resources if resource["group"] == group["group"]):
                vm = next(vm for vm in vms if f'vm:{vm["vmid"]}' == sid["sid"])
                vm["sid"] = sid["sid"]
                group["vms"].append(vm)

            group["vms"] = sorted(group["vms"], key=lambda d: d['name'])

        return groups
    
    def create_group(self, name: str, nodes: list):
        new_group = {
            "group": name,
            "nodes": ",".join(nodes)
        }
        url = f'{self._server}/api2/json/cluster/ha/groups'
        response = requests.post(url, cookies=self._auth_cookie, headers=self._csrf_token, data=new_group, verify=False)
        if not response.ok:
            logger.error(f"Error creating new group. {response.status_code}, {response.reason}")
            sys.exit(5)
        logger.warning("Group created.")
        return self.get_groups(name)[0]

    def create_group_using_proxmoxer(self, name: str, nodes: list):
        '''
        This is a place-holder function so that pytest can tell us
        when the proxmoxer library starts to support POST into groups.
        '''
        new_group = {
            "group": name,
            "nodes": ",".join(nodes)
        }
        self._proxmox.cluster.ha.groups.post(new_group)
        logger.warning("Group created.")
        return self.get_groups(name)[0]

    def delete_group(self, group: dict):
        if len(group["vms"]) > 0:
            logger.error("Cannot delete a group that has members!")
            sys.exit(6)
            
        # Delete the group
        logger.warning("Deleting group {group}...", group=group["group"])
        self._proxmox.cluster.ha.groups.delete(group["group"])
        logger.warning("Group deleted.")
    
    def update_group(self, group: dict, nodes: list):
        # TODO: Cannot delete a group that has VMs in it
        # we need to check for VMs in this group, or catch the 500-error it throws,
        # * cache each member VM
        # * delete the VM from the group
        # * delete the group
        # * re-create the group
        # * replace all the member VMs
        resources_to_put_back = []
        if len(group["vms"]) > 0:
            logger.warning("Group {group} is not empty and contains {vms} VMs", group=group["group"], vms=len(group["vms"]))
            
            # Remove all VMs from the group
            for resource in group["vms"]:
                resources_to_put_back.append({
                    "group": group["group"],
                    "sid": resource["sid"],
                    "type": "vm",
                    "state": resource["hastate"]
                })
                logger.warning("Deleting {sid} from group {group}...", sid=resource["sid"], group=group["group"])
                url = f'{self._server}/api2/json/cluster/ha/resources/{resource["sid"]}'
                response = requests.delete(url, cookies=self._auth_cookie, headers=self._csrf_token, verify=False)
                if not response.ok:
                    logger.exception(f"Error deleting group member. {response.status_code}, {response.reason}")
                    sys.exit(6)
                logger.warning("Member deleted.")
        
            # Wait for all VMs to actually be removed
            wait_for_empty = True
            while wait_for_empty:
                check_groups = list(self.get_groups(group["group"])) #next(g for g in self.get_groups() if g["group"] == group["group"])
                print(check_groups)
                if len(check_groups["vms"]) > 0:
                    logger.info("Waiting for all VMs to be removed from the group...")
                    time.sleep(1)
                else:
                    logger.info("All VMs have been removed from the group.")
                    wait_for_empty = False
            group = next(self.get_groups(group["group"]))
        
        # Delete the group
        self.delete_group(group)

        # Re-create the group
        self.create_group(group["group"], nodes)

        # Add all VMs back into the group
        url = f'{self._server}/api2/json/cluster/ha/resources'
        for vm in resources_to_put_back:
            response = requests.post(url, cookies=self._auth_cookie, headers=self._csrf_token, data=vm, verify=False)
            if not response.ok:
                logger.exception(f"Error updating group. {response.status_code}, {response.reason}")
                sys.exit(6)

        return self.get_groups(group["group"])[0]