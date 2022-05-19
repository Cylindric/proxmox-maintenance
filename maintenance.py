import os
from prettytable import PrettyTable, DOUBLE_BORDER
from cluster import Cluster

# Configuration
server = os.environ["PROXMOX_HOST"]
username = os.environ["PROXMOX_USERNAME"]
password = os.environ["PROXMOX_PASSWORD"]
log_level = "DEBUG" # CRITICAL, ERROR, WARNING, SUCCESS, INFO, DEBUG, TRACE
any_node_name = "test_any_node"
primary_node_name = "test_{name}_primary"
only_node_name = "test_{name}_only"

# Setting up logging
logger.remove()
logger.add(
    sys.stdout, 
    colorize=True, 
    backtrace=True, 
    diagnose=True, 
    format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> <level>{message}</level>", 
    level=log_level
)
logger.success("Starting Maintenance Mode Manager")


cluster = Cluster(server)
cluster.login(username, password)

nodes = cluster.get_nodes()
# nodes_table = PrettyTable()
# nodes_table.add_column("Node", [node["node"] for node in nodes])
# nodes_table.add_column("Status", [node["status"] for node in nodes])
# nodes_table.add_column("Running VMs", list(", ".join(vm["name"] for vm in node["running_vms"]) for node in nodes))
# nodes_table.align = "l"
# nodes_table.set_style(DOUBLE_BORDER)
# logger.debug(f"\n{nodes_table}")

groups = cluster.get_groups()
# groups_table = PrettyTable()
# groups_table.add_column("Group", [group["group"] for group in groups])
# groups_table.add_column("VMs", list(", ".join(vm["name"] for vm in group["vms"]) for group in groups))
# groups_table.set_style(DOUBLE_BORDER)
# groups_table.align = "l"
# logger.debug(f"\n{groups_table}")

logger.info(f"Making sure there is an 'any' group called {any_node_name}...")
if any(group["group"] == any_node_name for group in groups):
    # logger.debug(f"Found the 'any' group {any_node_name}")
    pass
else:
    logger.info(f"The 'any' group was not found, creating...")
    members = sorted(f'{n["node"]}:100' for n in nodes)
    new_group = cluster.create_group(any_node_name, members)

logger.info(f"Making sure there's a primary group for each node...")
for node in nodes:
    name = primary_node_name.format(name = node["node"])
    members = sorted(f'{n["node"]}:{"100" if n["node"]==node["node"] else "1"}' for n in nodes)
    member_list = ",".join(members)

    found = next((group for group in groups if group["group"] == name), None)
    if found:
        # a little dance to put the node list into a predictable order
        found_member_list = ",".join(sorted(found["nodes"].split(",")))
        # logger.debug(f"Found the primary group {name}")
        if found_member_list != member_list:
            logger.info(f"Fixing incorrect member list for {name}...")
            cluster.update_group(name, members)
        
    else:
        logger.info(f"The primary group {name} was not found, creating {members}...")
        new_group = cluster.create_group(name, members)

logger.info(f"Making sure there's an exclusive group for each node...")
for node in nodes:
    name = only_node_name.format(name = node["node"])
    expected_members = [f'{node["node"]}:100']
    found = next((group for group in groups if group["group"] == name), None)
    if found:
        found_members = sorted(found["nodes"].split(","))

        expected_str = ",".join(expected_members)
        found_str = ",".join(found_members)

        if found_str != expected_str:
            logger.warning(f"Fixing incorrect member list for {name}...")
            logger.warning(f"expected {expected_str}")
            logger.warning(f"found    {found_str}")
            cluster.update_group(found, expected_members)
    else:
        logger.info(f"The exclusive group {name} was not found, creating...")
        new_group = cluster.create_group(name, expected_members)
