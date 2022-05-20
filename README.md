# Proxmox Maintenance Tools

This might end up being a library of useful utilities. Or it might not.

## Usage

The tool requires certain environment variables to be set:

* `PROXMOX_HOST`, e.g. `prox1.example.com` or `192.168.0.10`
* `PROXMOX_USERNAME`, e.g. `user@pam`
* `PROXMOX_PASSWORD`

## Testing

Some tests are available. Use `pytest` to run them.

These tests require a functioning Proxmox HA cluster to do their thing, and
will make changes to it. They _should_ be non-destructive and self-reversing,
however if a test fails, it's possible some stray objects will remain.

The tests require some additional environment variables to be present:

**Additional ENV**:
* `PROXMOX_NODES`: a list of valid cluster nodes, e.g. "`prox01,prox02,prox03`"
* `PROXMOX_GROUPS`: a list of valid HA groups

**MUST**:
* There MUST be a Proxmox cluster configured for HA
* The cluster MUST contain at least the nodes configured in `valid_nodes`
* The cluster MUST contain at least one HA Group as listed in `valid_groups`
* The cluster MUST have at least one running VM on one of the nodes
* The cluster MUST have at least one non-running VM on one of the nodes

**SHOULD**:
* The cluster SHOULD have at least one LXC container on one of the nodes
* The cluster SHOULD have at least one Pool
