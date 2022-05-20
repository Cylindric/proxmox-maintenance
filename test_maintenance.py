import os
import random
import pytest
import proxmoxer
from cluster import Cluster

server = os.environ["PROXMOX_HOST"]
username = os.environ["PROXMOX_USERNAME"]
password = os.environ["PROXMOX_PASSWORD"]
valid_nodes = os.environ["PROXMOX_NODES"].split(",")
valid_groups = os.environ["PROXMOX_GROUPS"].split(",")


# Create a random tag to use to reduce chance of clobbering
def rnd(s:str = "{r}"):
    r = ''
    for _ in range(10):
        random_integer = random.randint(97, 97 + 26 - 1)
        flip_bit = random.randint(0, 1)
        random_integer = random_integer - 32 if flip_bit == 1 else random_integer
        r += (chr(random_integer))
    return s.format(r=r)


def test_cluster_init():
    cluster = Cluster(server)

def test_cluster_login():
    cluster = Cluster(server)
    cluster.login(username, password)

def test_get_nodes_returns_nodes():
    cluster = Cluster(server)
    cluster.login(username, password)
    nodes = cluster.get_nodes()
    assert isinstance(nodes, list)
    assert len(nodes) > 0

def test_get_nodes_returns_node_vms():
    cluster = Cluster(server)
    cluster.login(username, password)
    node = cluster.get_nodes()[0]
    assert "running_vms" in node
    assert len(node["running_vms"]) > 0

def test_get_nodes_returns_node_running_vms():
    cluster = Cluster(server)
    cluster.login(username, password)
    nodes = cluster.get_nodes()
    for node in nodes:
        for vm in node["running_vms"]:
            assert vm["status"] == "running"

def test_get_vms_returns_vms():
    cluster = Cluster(server)
    cluster.login(username, password)
    vms = cluster.get_vms()
    assert isinstance(vms, list)
    assert len(vms) > 0

def test_get_vms_returns_only_qemu():
    cluster = Cluster(server)
    cluster.login(username, password)
    vms = cluster.get_vms()
    for vm in vms:
        assert vm["type"] == "qemu"

def test_get_groups_returns_groups():
    cluster = Cluster(server)
    cluster.login(username, password)
    groups = cluster.get_groups()
    assert isinstance(groups, list)
    assert len(groups) > 0

def test_get_groups_returns_group_vms():
    cluster = Cluster(server)
    cluster.login(username, password)
    groups = cluster.get_groups()
    found_vms = False
    for group in groups:
        assert "vms" in group

        # Make sure at least one group has some VMs in it
        if len(group["vms"]) > 0:
            # Make sure the VM has the SID injected
            assert "sid" in group["vms"][0]
            found_vms = True
    
    assert found_vms

def test_get_single_group():
    cluster = Cluster(server)
    cluster.login(username, password)
    g = cluster.get_groups(valid_groups[0])
    assert len(g) == 1
    assert isinstance(g[0], dict)
   
def test_get_single_nonexistent_group():
    cluster = Cluster(server)
    cluster.login(username, password)
    g = cluster.get_groups(rnd())
    assert len(g) == 0
   
def test_create_and_delete_group():
    cluster = Cluster(server)
    cluster.login(username, password)
    g = cluster.create_group(rnd("pytest_group_{r}"), valid_nodes)
    assert "digest" in g
    cluster.delete_group(g)
    g = cluster.get_groups(g["group"])
    assert len(g) == 0

def test_create_and_delete_group_using_proxmoxer():
    # If this test fails, that means Proxmoxer now supports the 
    # addition of HA Groups using POST, so the `create_group` function
    # should be removed and replaced with the proxmoxer equivalent.
    cluster = Cluster(server)
    cluster.login(username, password)
    with pytest.raises(proxmoxer.core.ResourceException):
        g = cluster.create_group_using_proxmoxer(rnd("pytest_group_{r}"), valid_nodes)

def test_update_group():
    cluster = Cluster(server)
    cluster.login(username, password)
    g = cluster.create_group(rnd("pytest_group_{r}"), [valid_nodes[0]])
    assert g["nodes"] == valid_nodes[0]
    g = cluster.update_group(g, [valid_nodes[1]])
    assert isinstance(g, dict)
    assert g["nodes"] == valid_nodes[1]
    cluster.delete_group(g)
