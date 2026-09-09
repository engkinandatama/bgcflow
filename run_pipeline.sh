#!/bin/bash
set -e
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

snakemake --use-conda --rerun-triggers mtime --rerun-incomplete --cores 4 --keep-going \
  data/processed/Bacillus_velezensis_dummy/ppanggolin/genome_roary/gexf/pangenomeGraph_annotated.gexf \
  data/processed/Bacillus_velezensis_dummy/bigscape2/result_as8.0.4/index.html \
  >> run_dummy_pipeline.log 2>&1
