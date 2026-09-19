from __future__ import annotations

from xml.etree import ElementTree as ET


GEXF_NS = "http://gexf.net/1.3"


def build_gexf(graph: dict) -> bytes:
    ET.register_namespace("", GEXF_NS)
    root = ET.Element(f"{{{GEXF_NS}}}gexf", {"version": "1.3"})
    graph_element = ET.SubElement(
        root,
        f"{{{GEXF_NS}}}graph",
        {"mode": "static", "defaultedgetype": "directed"},
    )

    node_attributes = ET.SubElement(graph_element, f"{{{GEXF_NS}}}attributes", {"class": "node"})
    ET.SubElement(node_attributes, f"{{{GEXF_NS}}}attribute", {"id": "entity_type", "title": "entity_type", "type": "string"})
    ET.SubElement(node_attributes, f"{{{GEXF_NS}}}attribute", {"id": "aliases", "title": "aliases", "type": "string"})
    ET.SubElement(node_attributes, f"{{{GEXF_NS}}}attribute", {"id": "mention_count", "title": "mention_count", "type": "integer"})

    edge_attributes = ET.SubElement(graph_element, f"{{{GEXF_NS}}}attributes", {"class": "edge"})
    ET.SubElement(edge_attributes, f"{{{GEXF_NS}}}attribute", {"id": "relation_type", "title": "relation_type", "type": "string"})
    ET.SubElement(edge_attributes, f"{{{GEXF_NS}}}attribute", {"id": "evidence_count", "title": "evidence_count", "type": "integer"})

    nodes_element = ET.SubElement(graph_element, f"{{{GEXF_NS}}}nodes")
    for node in graph["nodes"]:
        node_element = ET.SubElement(
            nodes_element,
            f"{{{GEXF_NS}}}node",
            {"id": str(node["id"]), "label": str(node["name"])},
        )
        values = ET.SubElement(node_element, f"{{{GEXF_NS}}}attvalues")
        ET.SubElement(values, f"{{{GEXF_NS}}}attvalue", {"for": "entity_type", "value": str(node["entity_type"])})
        ET.SubElement(values, f"{{{GEXF_NS}}}attvalue", {"for": "aliases", "value": " | ".join(node["aliases"])})
        ET.SubElement(values, f"{{{GEXF_NS}}}attvalue", {"for": "mention_count", "value": str(node["mention_count"])})

    edges_element = ET.SubElement(graph_element, f"{{{GEXF_NS}}}edges")
    for index, edge in enumerate(graph["edges"]):
        edge_element = ET.SubElement(
            edges_element,
            f"{{{GEXF_NS}}}edge",
            {
                "id": str(index),
                "source": str(edge["source_id"]),
                "target": str(edge["target_id"]),
                "label": str(edge["relation_type"]),
                "weight": str(edge["evidence_count"]),
            },
        )
        values = ET.SubElement(edge_element, f"{{{GEXF_NS}}}attvalues")
        ET.SubElement(values, f"{{{GEXF_NS}}}attvalue", {"for": "relation_type", "value": str(edge["relation_type"])})
        ET.SubElement(values, f"{{{GEXF_NS}}}attvalue", {"for": "evidence_count", "value": str(edge["evidence_count"])})

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
