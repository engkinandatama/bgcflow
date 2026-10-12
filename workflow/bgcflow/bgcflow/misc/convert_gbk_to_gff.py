import logging
import sys

from BCBio import GFF
from Bio import SeqIO

log_format = "%(levelname)-8s %(asctime)s   %(message)s"
date_format = "%d/%m %H:%M:%S"
logging.basicConfig(format=log_format, datefmt=date_format, level=logging.DEBUG)


def convert_gbk_to_gff3(input_file, output_file, write_fasta=True):
    """
    Convert a GenBank (.gbk) file to a GFF3 file with sequence.
    Ensures standard GFF3 conformance where features have unique ID attributes.

    Parameters:
    input_file (str): Path to the input GenBank file.
    output_file (str): Path to the output GFF3 file.
    """
    with open(input_file, "r") as input_handle, open(output_file, "w") as output_handle:
        records = list(SeqIO.parse(input_handle, "genbank"))
        for r in records:
            feature_counter = 0
            for f in r.features:
                feature_counter += 1
                if "ID" not in f.qualifiers:
                    if "locus_tag" in f.qualifiers and f.qualifiers["locus_tag"]:
                        f.qualifiers["ID"] = [f.qualifiers["locus_tag"][0]]
                    elif "protein_id" in f.qualifiers and f.qualifiers["protein_id"]:
                        f.qualifiers["ID"] = [f.qualifiers["protein_id"][0]]
                    else:
                        f.qualifiers["ID"] = [f"{r.id}_{f.type}_{feature_counter}"]
                    f.id = f.qualifiers["ID"][0]
        GFF.write(records, output_handle, include_fasta=write_fasta)


if __name__ == "__main__":
    write_fasta = sys.argv[3].lower() == "true"
    convert_gbk_to_gff3(sys.argv[1], sys.argv[2], write_fasta)
