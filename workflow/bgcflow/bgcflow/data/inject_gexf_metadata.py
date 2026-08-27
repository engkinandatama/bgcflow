import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd

def inject_cazyme_and_bgc_to_gexf(gexf_in, pangenome_csv, cazyme_csv, gexf_out):
    """
    Injects CAZyme and BGC annotations as node attributes into a PPanGGOLiN GEXF file.
    
    Parameters:
        gexf_in: path to pangenomeGraph.gexf
        pangenome_csv: path to PPanGGOLiN gene presence/absence or family table
        cazyme_csv: path to concatenated df_cazyme.csv containing gene_id and cazyme_family
        gexf_out: path to output enriched pangenomeGraph_annotated.gexf
    """
    gexf_in = Path(gexf_in)
    gexf_out = Path(gexf_out)
    gexf_out.parent.mkdir(parents=True, exist_ok=True)

    # Load CAZyme annotations
    cazyme_map = {}
    if Path(cazyme_csv).exists() and Path(cazyme_csv).stat().st_size > 0:
        try:
            df_cazyme = pd.read_csv(cazyme_csv, sep="\t" if str(cazyme_csv).endswith(".tsv") else ",")
            if "gene_id" in df_cazyme.columns and "cazyme_family" in df_cazyme.columns:
                for _, row in df_cazyme.iterrows():
                    gid = str(row["gene_id"]).strip()
                    caz = str(row["cazyme_family"]).strip()
                    cls = str(row.get("cazyme_class", "CAZyme")).strip()
                    cazyme_map[gid] = (caz, cls)
        except Exception as e:
            print(f"Warning reading CAZyme CSV: {e}", file=sys.stderr)

    # Parse GEXF
    ET.register_namespace('', "http://www.gexf.net/1.2draft")
    ET.register_namespace('viz', "http://www.gexf.net/1.2draft/viz")
    tree = ET.parse(str(gexf_in))
    root = tree.getroot()

    # Find attributes element for nodes
    ns = {'g': 'http://www.gexf.net/1.2draft'}
    node_attributes = None
    for attrs in root.findall('.//g:attributes', ns):
        if attrs.attrib.get('class') == 'node':
            node_attributes = attrs
            break

    if node_attributes is None:
        graph = root.find('g:graph', ns)
        node_attributes = ET.SubElement(graph, 'attributes', {'class': 'node', 'mode': 'static'})

    # Find maximum attribute id
    max_id = 0
    for attr in node_attributes.findall('g:attribute', ns):
        try:
            max_id = max(max_id, int(attr.attrib.get('id', 0)))
        except ValueError:
            pass

    cazyme_attr_id = str(max_id + 1)
    cazyme_class_attr_id = str(max_id + 2)

    # Add attribute definitions
    attr_caz = ET.SubElement(node_attributes, 'attribute', {'id': cazyme_attr_id, 'title': 'cazyme_family', 'type': 'string'})
    attr_cls = ET.SubElement(node_attributes, 'attribute', {'id': cazyme_class_attr_id, 'title': 'cazyme_class', 'type': 'string'})

    # Populate node attributes
    nodes = root.findall('.//g:node', ns)
    annotated_count = 0

    for node in nodes:
        node_label = node.attrib.get('label', '')
        attvalues = node.find('g:attvalues', ns)
        if attvalues is None:
            attvalues = ET.SubElement(node, 'attvalues')

        # Check if node or its genes match CAZyme
        caz_found = "None"
        cls_found = "Non-CAZyme"

        # Check by node label or inspect existing attvalues
        for attval in attvalues.findall('g:attvalue', ns):
            val = attval.attrib.get('value', '')
            for gid in val.split():
                if gid.strip() in cazyme_map:
                    caz_found, cls_found = cazyme_map[gid.strip()]
                    break
            if caz_found != "None":
                break

        if caz_found == "None" and node_label in cazyme_map:
            caz_found, cls_found = cazyme_map[node_label]

        if caz_found != "None":
            annotated_count += 1

        ET.SubElement(attvalues, 'attvalue', {'for': cazyme_attr_id, 'value': caz_found})
        ET.SubElement(attvalues, 'attvalue', {'for': cazyme_class_attr_id, 'value': cls_found})

    tree.write(str(gexf_out), encoding='utf-8', xml_declaration=True)
    print(f"Successfully injected CAZyme annotations into {gexf_out.name} ({annotated_count} nodes matched CAZymes)")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python inject_gexf_metadata.py <gexf_in> <pangenome_csv> <cazyme_csv> <gexf_out>")
        sys.exit(1)
    inject_cazyme_and_bgc_to_gexf(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
