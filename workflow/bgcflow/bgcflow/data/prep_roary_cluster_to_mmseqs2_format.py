import logging
import sys
from pathlib import Path

import pandas as pd


def export_paired_values(input_file, output_file, gff_list_file=None):
    """
    Read roary cluster output, create paired values, and export them to a text file.
    Filters out any genes not present in the annotated GFFs (e.g. pseudogenes).

    Parameters:
        input_file (str): Path to the input file.
        output_file (str): Path to the output text file.
        gff_list_file (str, optional): Path to file containing list of GFFs to whitelist valid CDS IDs.
    """
    # Set up logging
    log_file = Path(output_file).parent / "export_paired_values.log"
    logging.basicConfig(filename=log_file, level=logging.INFO)

    # Optional: collect valid gene IDs from GFFs
    valid_gene_ids = set()
    if gff_list_file and Path(gff_list_file).exists():
        logging.info(f"Reading valid gene IDs from GFF list: {gff_list_file}...")
        try:
            with open(gff_list_file, "r") as gf:
                content = gf.read()
            gff_paths = [p.strip() for p in content.replace("\n", " ").split() if p.strip().endswith(".gff")]
            for gpath in gff_paths:
                p = Path(gpath)
                if p.exists():
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.startswith("#"):
                                continue
                            parts = line.split("\t")
                            if len(parts) >= 9 and parts[2] == "CDS":
                                attrs = parts[8]
                                for item in attrs.split(";"):
                                    if item.startswith("ID="):
                                        valid_gene_ids.add(item[3:].strip())
        except Exception as e:
            logging.warning(f"Error extracting valid gene IDs from GFFs: {e}")

    # Read the input file into a DataFrame
    logging.info(f"Reading input file {input_file}...")
    df_cluster = pd.read_csv(input_file, sep=":", header=None, index_col=0)

    # Process the DataFrame and create paired values
    logging.info("Processing input data...")
    data = {k: [gene.strip() for gene in v.split("\t") if gene.strip()] for k, v in df_cluster.to_dict()[1].items()}
    
    if valid_gene_ids:
        logging.info(f"Filtering clusters against {len(valid_gene_ids)} valid GFF CDS IDs...")
        paired_list = [
            (key, item)
            for key, values in data.items()
            for item in values
            if item in valid_gene_ids
        ]
    else:
        paired_list = [(key, item) for key, values in data.items() for item in values]

    # Export the paired values to the output file
    logging.info(f"Exporting {len(paired_list)} paired values to output file {output_file}...")
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as file:
        for pair in paired_list:
            file.write(f"{pair[0]}\t{pair[1]}\n")

    logging.info("Done.")
    return


if __name__ == "__main__":
    gff_arg = sys.argv[3] if len(sys.argv) > 3 else None
    export_paired_values(sys.argv[1], sys.argv[2], gff_arg)
