"""NetworkX-based privilege graph builder."""

import networkx as nx

from data.models import Platform


def build_privilege_graph(unified_identities, groups):
    """Build a directed graph representing privilege relationships."""
    G = nx.DiGraph()

    # Add identity nodes
    for identity in unified_identities:
        G.add_node(
            identity.id,
            type="identity",
            label=identity.display_name or identity.primary_email,
            email=identity.primary_email,
            department=identity.department,
            risk_score=identity.risk_score,
        )

    # Add group/role nodes and edges
    group_map = {}
    for group in groups:
        node_id = f"group_{group.platform.value}_{group.name}"
        group_map[(group.platform.value, group.name)] = node_id
        G.add_node(
            node_id,
            type="group",
            label=group.name,
            platform=group.platform.value,
            is_privileged=group.is_privileged,
        )

        # Add permission nodes for privileged groups
        for perm in group.permissions:
            perm_id = f"perm_{group.platform.value}_{perm}"
            if not G.has_node(perm_id):
                G.add_node(
                    perm_id,
                    type="permission",
                    label=perm,
                    platform=group.platform.value,
                )
            G.add_edge(node_id, perm_id, relation="grants")

    # Connect identities to their groups
    for identity in unified_identities:
        for platform_key, account in identity.platform_accounts.items():
            for group_name in account.groups:
                group_node = group_map.get((platform_key, group_name))
                if group_node:
                    G.add_edge(identity.id, group_node, relation="member_of", platform=platform_key)

            # Direct role assignments (AWS)
            for role in account.roles:
                role_node = group_map.get((platform_key, role))
                if role_node:
                    G.add_edge(identity.id, role_node, relation="has_role", platform=platform_key)

    # Add group inheritance edges
    _add_group_inheritance(G, group_map)

    return G


def _add_group_inheritance(G, group_map):
    """Add group-to-group inheritance relationships."""
    inheritance = {
        ("active_directory", "Enterprise Admins"): [("active_directory", "Domain Admins")],
        ("active_directory", "Domain Admins"): [("active_directory", "Server Operators"), ("active_directory", "Backup Operators")],
        ("aws_iam", "AdministratorAccess"): [("aws_iam", "PowerUserAccess")],
        ("aws_iam", "PowerUserAccess"): [("aws_iam", "ReadOnlyAccess")],
        ("okta", "IT-Admins"): [("okta", "Privileged-Access")],
    }

    for parent_key, children in inheritance.items():
        parent_node = group_map.get(parent_key)
        if not parent_node:
            continue
        for child_key in children:
            child_node = group_map.get(child_key)
            if child_node:
                G.add_edge(parent_node, child_node, relation="inherits_from")


def get_effective_permissions(G, identity_id):
    """Compute effective permissions for an identity via BFS through group hierarchy."""
    permissions = set()
    visited = set()
    queue = [identity_id]

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        for _, target, data in G.out_edges(current, data=True):
            node_data = G.nodes.get(target, {})
            if node_data.get("type") == "permission":
                permissions.add(node_data.get("label", target))
            elif node_data.get("type") in ("group", "role"):
                queue.append(target)

    return list(permissions)


def get_identity_subgraph(G, identity_id, depth=3):
    """Extract ego-graph around an identity for focused visualization."""
    if identity_id not in G:
        return {"nodes": [], "edges": []}

    # BFS to get neighbors up to depth
    visited = {identity_id}
    queue = [(identity_id, 0)]
    subgraph_nodes = {identity_id}

    while queue:
        node, d = queue.pop(0)
        if d >= depth:
            continue
        for _, neighbor in G.out_edges(node):
            if neighbor not in visited:
                visited.add(neighbor)
                subgraph_nodes.add(neighbor)
                queue.append((neighbor, d + 1))

    return export_graph_json(G.subgraph(subgraph_nodes))


def export_graph_json(G):
    """Export graph as JSON for vis.js rendering."""
    nodes = []
    for node_id, data in G.nodes(data=True):
        node = {
            "id": node_id,
            "label": data.get("label", str(node_id)[:20]),
            "type": data.get("type", "unknown"),
            "platform": data.get("platform", ""),
            "group": data.get("type", "unknown"),
        }
        # Visual properties based on type
        node_type = data.get("type")
        if node_type == "identity":
            node["color"] = "#4fc3f7"
            node["shape"] = "dot"
            node["size"] = 20
            risk = data.get("risk_score", 0)
            if risk >= 60:
                node["color"] = "#ef5350"
                node["borderWidth"] = 3
            elif risk >= 40:
                node["color"] = "#ffa726"
        elif node_type == "group":
            node["shape"] = "diamond"
            node["size"] = 15
            if data.get("is_privileged"):
                node["color"] = "#ab47bc"
            else:
                node["color"] = "#66bb6a"
        elif node_type == "permission":
            node["shape"] = "triangle"
            node["size"] = 10
            node["color"] = "#78909c"

        nodes.append(node)

    edges = []
    for source, target, data in G.edges(data=True):
        edges.append({
            "from": source,
            "to": target,
            "label": data.get("relation", ""),
            "arrows": "to",
            "color": _edge_color(data.get("relation", "")),
        })

    return {"nodes": nodes, "edges": edges}


def _edge_color(relation):
    colors = {
        "member_of": "#90a4ae",
        "has_role": "#ce93d8",
        "grants": "#ef9a9a",
        "inherits_from": "#a5d6a7",
    }
    return colors.get(relation, "#757575")
