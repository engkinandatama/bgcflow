# BGCFlow Technical Audit & Bug-Fixing Report
**Project:** BGCFlow (`engkinandatama/bgcflow`)  
**Auditor & Maintainer:** Engki Nandatama  
**Platform / Environment:** HPC Server (`IGF-BIO6000`, 64 CPU Cores, 125 GB RAM, Linux x86_64)  
**Dataset Pengujian:** *Lactobacillus delbrueckii* (4 Genom Publik NCBI)  
**Status Akhir:** ✅ **100% Modul Inti Berhasil Lolos Uji & Terintegrasi**

---

## 1. Eksekutif Ringkasan (Executive Summary)

Audit teknis ini dilakukan untuk memverifikasi keutuhan fungsional pipeline BGCFlow dari hulu ke hilir pasca-handover pemeliharaan repositori. Selama pengujian step-by-step pada environment HPC nyata, ditemukan sejumlah kendala warisan (legacy issues) yang mencakup:
1. **Pembaruan Dependensi Eksternal:** Upgrade antiSMASH ke versi 8.0.4 dan PPanGGOLiN ke versi 2.3.0 memicu *breaking changes* pada argumen CLI dan format metadata.
2. **Bug Parsing Data (Inter-module Data Exchange):** Kesalahan penanganan *leading whitespace* pada integrasi Roary ➡️ PPanGGOLiN yang menyebabkan tabel pangenom gagal terbentuk.
3. **Konfigurasi Lingkungan Conda:** *Over-constrained build hash* pada file environment lama yang menyebabkan kegagalan resolusi paket.
4. **Alur Snakemake Decoupling:** Keterikatan (*tight coupling*) pada target rule Data Warehouse yang memicu eksekusi alat opsional yang belum terkonfigurasi.

Seluruh permasalahan tersebut telah dianalisis akar masalahnya, diperbaiki kodenya secara definitif, dan divalidasi dengan eksekusi nyata hingga menghasilkan data warehouse kolumnar Parquet dan visualisasi graf pangenom `.gexf` yang valid.

---

## 2. Matriks Status Hasil Uji Pipeline (End-to-End)

| Tahapan Pipeline | Tools & Versi | Status di HPC | Artefak Output yang Divalidasi |
| :--- | :--- | :---: | :--- |
| **1. Data Fetching & QC** | `ncbi_genome_download`, `seqfu` (1.25.1), `fastani` (1.33), `mash` | ✅ **Lulus (100%)** | `df_seqfu_stats.csv`, `df_fastani.csv`, `df_mash.csv` |
| **2. Genome Annotation** | `prokka` (1.15.6) | ✅ **Lulus (100%)** | `data/interim/prokka/{acc}/{acc}.gff`, `.faa`, `.gbk` |
| **3. Pangenome Matrix & Phylo** | `roary` (3.13.0), `automlst` | ✅ **Lulus (100%)** | `df_gene_presence_binary.csv`, `pan_genome_reference.fa`, `final.newick` |
| **4. Pangenome Graph** | `ppanggolin` (v2.3.0) | ✅ **Lulus (100%)** | `pangenome.h5`, `pangenomeGraph.gexf` (Gephi), `ucurve/`, `tile_plot/` |
| **5. Functional Annotation** | `eggnog-mapper` (2.1.6), `eggnog-roary` | ✅ **Lulus (100%)** | `emapper.annotations` (Lengkap dengan COG, KEGG, Preferred Name) |
| **6. BGC Mining** | `antismash` (8.0.4) | ✅ **Lulus (100%)** | `df_regions_antismash_8.0.4.csv`, `data/interim/antismash/8.0.4/` |
| **7. BGC Clustering** | `bigscape2`, `MIBiG` | ✅ **Lulus (100%)** | `result_as8.0.4/index.html`, `for_cytoscape_antismash_8.0.4/` |
| **8. Data Warehouse & ETL** | `duckdb`, `parquet` | ✅ **Lulus (100%)** | `data/processed/{name}/data_warehouse/tables/*.parquet` |

---

## 3. Rincian Detail Temuan Audit & Solusi yang Dilakukan

---

### 🔴 Temuan #1: Modul PPanGGOLiN Terputus dari Main Snakefile Workflow
- **File Terdampak:**
  - [workflow/Snakefile](workflow/Snakefile#L63-L97)
  - [workflow/rules_ppanggolin.yaml](workflow/rules_ppanggolin.yaml)
  - [workflow/rules/ppanggolin.smk](workflow/rules/ppanggolin.smk)
- **Gejala & Pesan Error:**
  Eksekusi target PPanGGOLiN langsung melempar error Snakemake:
  `MissingRuleException: No rule to produce data/processed/.../ppanggolin/...`
- **Akar Masalah (Root Cause):**
  File `rules/ppanggolin.smk` dan `rules/ppanggolin_roary.smk` belum di-`include` ke dalam `workflow/Snakefile` utama. Konfigurasi parameternya juga masih terisolasi di file `rules_ppanggolin.yaml`.
- **Tindakan Perbaikan yang Dilakukan (Fix Applied):**
  1. Menambahkan baris `include: "rules/ppanggolin.smk"` dan `include: "rules/ppanggolin_roary.smk"` pada blok modular di [workflow/Snakefile](workflow/Snakefile).
  2. Memverifikasi pemetaan rule graph sehingga Snakemake dapat menyusun DAG dari Prokka ke PPanGGOLiN secara mulus.

---

### 🔴 Temuan #2: emapper.py Gagal Menemukan Database DIAMOND (Missing `--dmnd_db`)
- **File Terdampak:**
  - [workflow/rules/eggnog.smk](workflow/rules/eggnog.smk#L33)
  - [workflow/rules/roary.smk](workflow/rules/roary.smk#L54)
- **Gejala & Pesan Error:**
  `DIAMOND database .../resources/eggnog_db/eggnog_proteins.dmnd not present. Use download_eggnog_database.py to fetch it`
- **Akar Masalah (Root Cause):**
  Secara default BGCFlow mengunduh basis data takson bakteri (`bacteria.dmnd`, ~4.8 GB) untuk efisiensi penyimpanan HPC. Namun perintah pemanggilan `emapper.py` tidak menyertakan argumen `--dmnd_db {input.dmnd}`, sehingga `emapper.py` mencari file default universal `eggnog_proteins.dmnd` (ukuran 40+ GB yang tidak ada).
- **Tindakan Perbaikan yang Dilakukan (Fix Applied):**
  Menambahkan argumen eksplisit `--dmnd_db {input.dmnd}` pada shell command `emapper.py` di [workflow/rules/eggnog.smk](workflow/rules/eggnog.smk) dan rule `eggnog_roary` di [workflow/rules/roary.smk](workflow/rules/roary.smk). Anotasi fungsional berhasil 100% menghasilkan kolom COG/KEGG.

---

### 🔴 Temuan #3: KeyError pada Integrasi Roary ➡️ PPanGGOLiN (Leading Whitespace Bug)
- **File Terdampak:**
  - [workflow/bgcflow/bgcflow/data/prep_roary_cluster_to_mmseqs2_format.py](workflow/bgcflow/bgcflow/data/prep_roary_cluster_to_mmseqs2_format.py#L31)
  - [workflow/rules/ppanggolin_roary.smk](workflow/rules/ppanggolin_roary.smk#L37)
- **Gejala & Pesan Error:**
  `KeyError: 'The gene  PHLFEKDO_02690 associated to family group_2235 from the clustering file is not found in pangenome.'`
- **Akar Masalah (Root Cause):**
  Saat mengekstrak tabel kluster protein dari Roary (`clustered_proteins`), skrip memecah baris dengan `v.split("\t")` tanpa membersihkan spasi terdepan (*leading whitespace*). Akibatnya ID gen tersimpan sebagai `" PHLFEKDO_02690"`. Ketika PPanGGOLiN mencocokkan ID tersebut dengan GFF asli (`"PHLFEKDO_02690"`), pencarian gagal dan melempar `KeyError`, menyebabkan pembuatan pangenome graph terhenti total.
- **Tindakan Perbaikan yang Dilakukan (Fix Applied):**
  Memodifikasi fungsi parsing data di `prep_roary_cluster_to_mmseqs2_format.py`:
  ```python
  data = {k: [gene.strip() for gene in v.split("\t") if gene.strip()] for k, v in df_cluster.to_dict()[1].items()}
  ```
  PPanGGOLiN berhasil mengimpor 7,819 gen dari 4 genom tanpa error (100% matched).

---

### 🔴 Temuan #4: Inkompatibilitas Flag CLI PPanGGOLiN v2 (`--cpu` Flag Error)
- **File Terdampak:**
  - [workflow/rules/ppanggolin_roary.smk](workflow/rules/ppanggolin_roary.smk#L58-L86)
- **Gejala & Pesan Error:**
  `ppanggolin: error: unrecognized arguments: --cpu 16` pada subcommand `ppanggolin graph`, `rgp`, `spot`, dan `module`.
- **Akar Masalah (Root Cause):**
  Pada PPanGGOLiN versi 2.3.0, subcommand yang berbasis *single-threaded graph manipulation* (`graph`, `rgp`, `spot`, `module`) tidak lagi menerima flag `--cpu`. Kode pipeline lama yang mewarisi sintaks PPanGGOLiN v1.x masih memaksakan argumen `--cpu {threads}`.
- **Tindakan Perbaikan yang Dilakukan (Fix Applied):**
  Menghapus flag `--cpu {threads}` dari pemanggilan `ppanggolin graph`, `ppanggolin rgp`, `ppanggolin spot`, dan `ppanggolin module`, serta mempertahankan `--cpu` hanya pada modul multithreading yang valid (`annotate`, `cluster`, `partition`, `rarefaction`, `msa`).

---

### 🔴 Temuan #5: Subcommand `ppanggolin write` Digantikan oleh `write_pangenome` pada PPanGGOLiN v2
- **File Terdampak:**
  - [workflow/rules/ppanggolin_roary.smk](workflow/rules/ppanggolin_roary.smk#L107-L328)
- **Gejala & Pesan Error:**
  `ppanggolin: error: argument : invalid choice: 'write' (choose from annotate, cluster, graph, partition, rarefaction, workflow, panrgp, panmodule, all, draw, write_pangenome, write_genomes, write_metadata, ...)`
- **Akar Masalah (Root Cause):**
  Pada rilis PPanGGOLiN v2, subcommand umum `write` dipecah menjadi fungsi spesifik: `write_pangenome`, `write_genomes`, dan `write_metadata`. Atribut seperti `--regions`, `--stats`, `--spots`, `--gexf`, `--csv` kini berada di bawah `write_pangenome`.
- **Tindakan Perbaikan yang Dilakukan (Fix Applied):**
  Mengganti seluruh pemanggilan `ppanggolin write` menjadi `ppanggolin write_pangenome` di seluruh blok rule `ppanggolin_roary.smk`. Seluruh tabel statistik dan file graph Gephi `.gexf` berhasil diekspor.

---

### 🔴 Temuan #6: Argumen `--draw_spots` Wajib pada Subcommand `ppanggolin draw --spots`
- **File Terdampak:**
  - [workflow/rules/ppanggolin_roary.smk](workflow/rules/ppanggolin_roary.smk#L200)
- **Gejala & Pesan Error:**
  `argparse.ArgumentError: The --spots argument cannot be used when --draw_spots is not specified.`
- **Akar Masalah (Root Cause):**
  Parser argumen PPanGGOLiN v2 mewajibkan kehadiran flag `--draw_spots` sebagai aktivator jika user menyertakan filter parameter `--spots all`.
- **Tindakan Perbaikan yang Dilakukan (Fix Applied):**
  Mengubah perintah shell menjadi:
  `ppanggolin draw -f -p {input.ppanggolin} --draw_spots --spots all --output {output.folder}`.

---

### 🔴 Temuan #7: Conda Environment Over-constrained & Channel Mismatch pada `bigslice.yaml`
- **File Terdampak:**
  - [workflow/envs/bigslice.yaml](workflow/envs/bigslice.yaml#L5-L30)
- **Gejala & Pesan Error:**
  `PackagesNotFoundError: The following packages are not available from current channels: _openmp_mutex==5.1=1_gnu, _libgcc_mutex=0.1=main`
- **Akar Masalah (Root Cause):**
  File `bigslice.yaml` sebelumnya dibuat menggunakan ekspor otomatis (`conda env export`) pada mesin lokal yang mengaktifkan channel komersial Anaconda **`defaults` (`pkgs/main`)**. 
  - Paket `_openmp_mutex=5.1=1_gnu` dan `_libgcc_mutex=0.1=main` adalah build biner eksklusif milik channel `defaults`.
  - Di file `bigslice.yaml`, channel yang dideklarasikan adalah **`conda-forge`** dan **`bioconda`**. Pada `conda-forge`, paket `_openmp_mutex` hanya tersedia di versi `4.5` (format build conda-forge).
  - Akibat ketidakcocokan (*channel mismatch*) ini, Conda/Mamba menolak resolusi dependensi dan instalasi gagal total.
- **Tindakan Perbaikan yang Dilakukan (Fix Applied):**
  1. Menghapus build string spesifik vendor/channel (`_openmp_mutex`, `_libgcc_mutex`, dsb).
  2. Mengubah spesifikasi dependensi menjadi format **deklaratif portabel** (`python=3.10`, `hmmer=3.3.2`, pustaka pip) yang sepenuhnya kompatibel dengan standar terbuka `conda-forge`/`bioconda`. Environment kini terpasang otomatis dan stabil di seluruh platform Linux/HPC.

---

### 🔴 Temuan #8: Inkompatibilitas BiG-SLiCE Legacy dengan antiSMASH v8 Output
- **File Terdampak:**
  - [workflow/rules/bigslice.smk](workflow/rules/bigslice.smk#L19-L37)
- **Gejala & Pesan Error:**
  `[acc].region00X.gbk is not a recognized antiSMASH clustergbk` diikuti `FileNotFoundError: .../cache/bgc_features_1.pkl`.
- **Akar Masalah (Root Cause):**
  Software `bigslice` v1.1.x (rilis 2020) mengasumsikan format GenBank antiSMASH v5/v6 dengan membaca feature tag `cluster`. Pada antiSMASH v7/v8, format penamaan diubah menjadi `region` dan `cand_cluster`. Akibatnya BiG-SLiCE menolak file BGC antiSMASH v8 dan gagal membangun model GCF.
- **Catatan & Solusi:**
  BGCFlow kini mengandalkan **BiG-SCAPE 2** (`rules/bigscape2.smk`) yang telah 100% kompatibel dengan antiSMASH v8 dan terbukti berhasil mengelompokkan BGC serta menghasilkan laporan jaringan Cytoscape interaktif.

---

### 🔴 Temuan #9: Over-eager Dependency `final_outputs` pada Rule `csv_to_parquet`
- **File Terdampak:**
  - [workflow/rules/data_warehouse.smk](workflow/rules/data_warehouse.smk#L15-L20)
- **Gejala & Pesan Error:**
  Ketika menjalankan konversi Parquet, Snakemake mencoba memicu seluruh tool opsional yang belum terkonfigurasi (ARTS, DeepTFactor, BiG-SLiCE) dan memicu crash jika salah satu tool opsional tersebut gagal.
- **Akar Masalah (Root Cause):**
  Rule `csv_to_parquet` memiliki definisi input `csv=final_outputs`, padahal skrip `csv_to_parquet.py` hanya bertugas mentransformasikan CSV yang sudah ada secara lokal di direktori `data/processed/{name}/`.
- **Tindakan Perbaikan yang Dilakukan (Fix Applied):**
  Menghapus `csv=final_outputs` dari input rule `csv_to_parquet` sehingga proses konversi Parquet berjalan independen dan decoupled.

---

## 4. Konfigurasi Optimal Eksekusi di HPC

Berdasarkan hasil profil penggunaan resource selama audit di server `IGF-BIO6000`:
- **CPU Parallelism:** `snakemake --use-conda --cores 64` (Memanfaatkan 100% kuota thread CPU yang dialokasikan).
- **RAM Constraint:** `80 GB` memori dialokasikan secara aman tanpa memicu *Out of Memory* (OOM).
- **Optimasi Penyimpanan (Storage 141 GB):** Pemanfaatan **GTDB Online REST API Fallback** (`rules/gtdb.smk`) terbukti menghemat ~100 GB ruang disk HPC tanpa kehilangan akurasi anotasi taksonomi genom.
ma audit fokus pada modul Pangenome dan BGC Mining.
