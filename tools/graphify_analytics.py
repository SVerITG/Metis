#!/usr/bin/env python3
"""
graphify_analytics.py — Extract knowledge-focused analytics from a Graphify graph.

Called by the Metis dashboard via subprocess using the pipx Python:
    ~/.local/share/pipx/venvs/graphifyy/bin/python3 \
        tools/graphify_analytics.py [path/to/graph.json]

Outputs JSON to stdout with:
  - god_nodes: most-connected knowledge hubs
  - surprising: cross-community bridges within knowledge content
  - communities: knowledge community overview
  - stats: node/edge counts
"""

import json
import sys
from collections import Counter
from pathlib import Path


def main(graph_path: str) -> dict:
    p = Path(graph_path)
    if not p.exists():
        return {"error": "graph.json not found", "graph_exists": False}

    with open(p) as f:
        raw = json.load(f)

    nodes = raw.get("nodes", [])
    links = raw.get("links", [])
    graph_meta = raw.get("graph", {})

    # Build quick lookup
    node_by_id = {n["id"]: n for n in nodes}

    # In a knowledge-only graph, all nodes are knowledge.
    # In a mixed graph, filter to graphify-knowledge/ paths.
    knowledge_ids = set()
    for n in nodes:
        sf = n.get("source_file") or ""
        if "graphify-knowledge/" in sf or not any(
            p in sf for p in ("system/", "agents/", ".claude/", "tools/", "tests/")
        ):
            knowledge_ids.add(n["id"])

    # Build adjacency for knowledge subgraph
    degree = Counter()
    knowledge_edges = []
    for e in links:
        src, tgt = e.get("source"), e.get("target")
        # Count edges where at least one end is knowledge
        if src in knowledge_ids or tgt in knowledge_ids:
            if src in knowledge_ids:
                degree[src] += 1
            if tgt in knowledge_ids:
                degree[tgt] += 1
            if src in knowledge_ids and tgt in knowledge_ids:
                knowledge_edges.append(e)

    # God nodes — most-connected knowledge hubs
    god_nodes = []
    for nid, deg in degree.most_common(12):
        n = node_by_id.get(nid, {})
        sf = n.get("source_file", "")
        # Extract a readable label
        label = n.get("label", "")
        if not label:
            label = Path(sf).stem if sf else nid
        # Determine content type from path
        content_type = _classify_knowledge_node(sf)
        community_id = n.get("community")
        community_name = n.get("community_name") or f"Cluster {community_id}"
        god_nodes.append({
            "label": label,
            "degree": deg,
            "type": content_type,
            "community": community_name,
            "source_file": sf,
        })

    # Knowledge communities — group by community, count members
    community_members = {}
    for nid in knowledge_ids:
        n = node_by_id.get(nid, {})
        cid = n.get("community")
        if cid is not None:
            community_members.setdefault(cid, []).append(n)

    # Top communities by size
    community_summary = []
    for cid, members in sorted(community_members.items(),
                                key=lambda x: len(x[1]), reverse=True)[:10]:
        # Sample member labels for a readable summary
        sample_labels = []
        for m in members[:5]:
            lbl = m.get("label") or Path(m.get("source_file", "")).stem
            sample_labels.append(lbl)
        name = members[0].get("community_name") or f"Cluster {cid}"
        # Classify dominant type
        type_counts = Counter(_classify_knowledge_node(m.get("source_file", ""))
                              for m in members)
        dominant_type = type_counts.most_common(1)[0][0] if type_counts else "mixed"
        community_summary.append({
            "id": cid,
            "name": name,
            "size": len(members),
            "dominant_type": dominant_type,
            "sample_members": sample_labels,
        })

    # Surprising connections — cross-community edges within knowledge
    surprising = []
    for e in knowledge_edges:
        src_n = node_by_id.get(e["source"], {})
        tgt_n = node_by_id.get(e["target"], {})
        src_c = src_n.get("community")
        tgt_c = tgt_n.get("community")
        if src_c is not None and tgt_c is not None and src_c != tgt_c:
            src_label = src_n.get("label") or Path(src_n.get("source_file", "")).stem
            tgt_label = tgt_n.get("label") or Path(tgt_n.get("source_file", "")).stem
            surprising.append({
                "from_label": src_label,
                "to_label": tgt_label,
                "from_type": _classify_knowledge_node(src_n.get("source_file", "")),
                "to_type": _classify_knowledge_node(tgt_n.get("source_file", "")),
                "relation": e.get("relation", "related"),
                "confidence": e.get("confidence", ""),
            })

    # Deduplicate and limit
    seen = set()
    unique_surprising = []
    for s in surprising:
        key = tuple(sorted([s["from_label"], s["to_label"]]))
        if key not in seen:
            seen.add(key)
            unique_surprising.append(s)
    unique_surprising = unique_surprising[:8]

    # File modification time as "built_at"
    built_at = ""
    try:
        import datetime
        mtime = p.stat().st_mtime
        built_at = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass

    return {
        "graph_exists": True,
        "built_at": built_at,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(links),
            "knowledge_nodes": len(knowledge_ids),
            "knowledge_edges": len(knowledge_edges),
            "knowledge_communities": len(community_members),
        },
        "god_nodes": god_nodes,
        "surprising": unique_surprising,
        "communities": community_summary,
    }


def _classify_knowledge_node(source_file: str) -> str:
    """Classify a knowledge node by its source path."""
    sf = (source_file or "").lower()
    if "/papers/" in sf:
        return "paper"
    if "/ideas/" in sf:
        return "idea"
    if "/projects/" in sf:
        return "project"
    if "/tasks/" in sf:
        return "task"
    if "/meetings/" in sf:
        return "meeting"
    if "/concepts/" in sf:
        return "concept"
    if "/journal/" in sf:
        return "journal"
    if "/sessions/" in sf:
        return "session"
    if "/library-corpus/" in sf:
        return "corpus"
    if "/memory/" in sf:
        return "memory"
    return "knowledge"


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "graphify-out/graph.json"
    result = main(path)
    json.dump(result, sys.stdout, indent=2)
