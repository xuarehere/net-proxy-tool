---
inclusion: manual
---
# Field validation on real nodes

Use this when the maintainer asks for checks against real servers or containers.

- Read-only by default: gateway tests, node checks (`/api/test-node`, MCP `test_node`) and baselines. Switching a node on or off, provisioning or restoring requires the maintainer to name the node and approve that action in the current conversation.
- Run the console from a copy of the configuration in a temporary directory (`NET_PROXY_CONFIG`) and on a port other than 8899, so the maintainer's running console is not affected.
- Record results in `scratch/field/<date>.md`: node id, check, outcome, final HTTP status or the host where the request stopped. Real addresses and names appear only there.
- Before any commit, `tools/kiro/scan_secrets.py` must report no entry of `scratch/private-denylist.txt`. Add new private names and addresses to that file as soon as you see them.
- If a check changes something unexpectedly, stop, report what changed, and do not try to repair a real node without approval.
