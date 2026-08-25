# BGCFlow Technical Audit & Onboarding Notes

Dokumen ini mencatat temuan teknis, status modul, dan rencana perbaikan pipeline BGCFlow selama masa transisi pemeliharaan dan ekspansi repository.

---

## Ringkasan Progres & Status Pipeline (Test Dataset: *Lactobacillus delbrueckii*)

| Tahapan / Modul | Tools Terkait | Status di HPC | Catatan Hasil Audit |
| :--- | :--- | :---: | :--- |
| **1. Data Selection & QC** | `ncbi_genome_download`, `seqfu`, `fastani`, `mash` | ✅ **Lulus (100% Berhasil)** | Otomatis download sekuens NCBI, kalkulasi N50 & GC content via SeqFu, dan pairwise ANI matrix via FastANI bekerja sangat cepat & stabil. |
| **2. Anotasi Genom** | `prokka` | ✅ **Lulus (100% Berhasil)** | Berhasil mengekstrak CDS, protein (`.faa`), GFF, dan GenBank (`.gbk`) untuk seluruh sampel pengujian. |
| **3. Pangenome** | `roary` | ✅ **Lulus (100% Berhasil)** | Berhasil mengelompokkan matriks kehadiran gen pangenom (`df_gene_presence_binary.csv`) dan pohon autoMLST secara paralel. |
| **3b. Pangenome (PPanGGOLiN)** | `ppanggolin` (v2.x) | ✅ **Lulus (100% Berhasil)** | Berhasil mengintegrasikan GFF Prokka ke PPanGGOLiN, partisi graf pangenome, rarefaction curve, dan MSA core/phylo ke `data/processed/{name}/ppanggolin/genome/pangenome.h5`. |
| **4. Functional Annotation** | `eggnog-mapper`, `eggnog-roary` | ✅ **Lulus (100% Berhasil)** | Berhasil meng-anotasi pangenome Roary dengan COG/KEGG dan menghasilkan `data/processed/{name}/eggnog_roary/emapper.annotations`. |
| **5. BGC Mining** | `antismash` (v8.0.4) | ✅ **Lulus (100% Berhasil)** | Berhasil mendeteksi kluster BGC dari seluruh genom dan mengekstrak tabel region ke `data/processed/{name}/tables/df_regions_antismash_8.0.4.csv`. |
| **5b. BGC Clustering** | `bigscape2`, `MIBiG` | ✅ **Lulus (100% Berhasil)** | Berhasil mengelompokkan BGC ke jaringan kemiripan (GCF) dan menghasilkan laporan visualisasi Cytoscape & HTML di `data/processed/{name}/bigscape2/`. |
| **6. Reporting & Warehouse** | `duckdb`, `metabase`, `parquet` | ⏳ *Akan Diuji* | Validasi pipeline ETL ke format database analitik. |

---

## Log Temuan Audit Teknis

### 🔴 Temuan #1: Modul PPanGGOLiN Terputus dari Main Snakefile Workflow
- **Lokasi File:**
  - [workflow/Snakefile](file:///home/nanda/projects/bgcflow/workflow/Snakefile#L63-L97)
  - [workflow/rules_ppanggolin.yaml](file:///home/nanda/projects/bgcflow/workflow/rules_ppanggolin.yaml)
  - [workflow/rules/ppanggolin.smk](file:///home/nanda/projects/bgcflow/workflow/rules/ppanggolin.smk)
- **Gejala / Error:**
  Saat pengguna mengeksekusi target output pangenom PPanGGOLiN (`data/processed/{name}/ppanggolin/genome/pangenome.h5`), Snakemake mengeluarkan error:
  `MissingRuleException: No rule to produce data/processed/.../ppanggolin/...`
- **Akar Masalah (Root Cause):**
  1. File `workflow/Snakefile` pada baris 64–97 menyertakan modul `roary.smk`, tetapi baris `include: "rules/ppanggolin.smk"` **belum ditambahkan**.
  2. Definisi target output dan deskripsi rule PPanGGOLiN berada di file terpisah `workflow/rules_ppanggolin.yaml`, belum digabungkan ke `workflow/rules.yaml`.
- **Rencana Tindakan (Action Plan):**
  1. Tambahkan `include: "rules/ppanggolin.smk"` ke dalam [workflow/Snakefile](file:///home/nanda/projects/bgcflow/workflow/Snakefile).
  2. Gabungkan isi [workflow/rules_ppanggolin.yaml](file:///home/nanda/projects/bgcflow/workflow/rules_ppanggolin.yaml) ke dalam [workflow/rules.yaml](file:///home/nanda/projects/bgcflow/workflow/rules.yaml).
  3. Uji kembali rule `ppanggolin_genome` dengan input GFF dari Prokka.

---

### 🔴 Temuan #2: emapper.py Gagal Menemukan Database DIAMOND (Missing `--dmnd_db`)
- **Lokasi File:**
  - [workflow/rules/eggnog.smk](file:///home/nanda/projects/bgcflow/workflow/rules/eggnog.smk#L33)
- **Gejala / Error:**
  `DIAMOND database .../resources/eggnog_db/eggnog_proteins.dmnd not present. Use download_eggnog_database.py to fetch it`
- **Akar Masalah (Root Cause):**
  Rule `install_eggnog` mendownload dan membuat database spesifik bakteri dengan nama `bacteria.dmnd` (`resources/eggnog_db/bacteria.dmnd`). Namun pada rule `eggnog`, perintah `emapper.py` tidak menyertakan argumen `--dmnd_db {input.dmnd}` sehingga `emapper.py` secara default mencari database universal `eggnog_proteins.dmnd` (40 GB+).
- **Perbaikan yang Dilakukan (Fix Applied):**
  Menambahkan `--dmnd_db {input.dmnd}` pada pemanggilan `emapper.py` di [workflow/rules/eggnog.smk](file:///home/nanda/projects/bgcflow/workflow/rules/eggnog.smk).

---

### 🔴 Temuan #3: KeyError pada Integrasi Roary ➡️ PPanGGOLiN (Whitespace Parsing Bug)
- **Lokasi File:**
  - [workflow/bgcflow/bgcflow/data/prep_roary_cluster_to_mmseqs2_format.py](file:///home/nanda/projects/bgcflow/workflow/bgcflow/bgcflow/data/prep_roary_cluster_to_mmseqs2_format.py#L31)
  - [workflow/rules/ppanggolin_roary.smk](file:///home/nanda/projects/bgcflow/workflow/rules/ppanggolin_roary.smk#L37)
- **Gejala / Error:**
  `KeyError: 'The gene  PHLFEKDO_02690 associated to family group_2235 from the clustering file is not found in pangenome.'`
- **Akar Masalah (Root Cause):**
  Saat mem-parsing file `clustered_proteins` dari Roary ke format MMseqs2/PPanGGOLiN, fungsi `v.split("\t")` tidak melakukan `.strip()`. Nama gen mengandung spasi terdepan (`" PHLFEKDO_02690"` alih-alih `"PHLFEKDO_02690"`), sehingga PPanGGOLiN gagal mencocokkan ID gen dengan anotasi GFF dan melempar `KeyError`. Inilah penyebab utama pipeline PPanGGOLiN gagal dan graf pangenome kosong.
- **Perbaikan yang Dilakukan (Fix Applied):**
  Menambahkan pembersihan whitespace: `[gene.strip() for gene in v.split("\t") if gene.strip()]` di `prep_roary_cluster_to_mmseqs2_format.py`.

---

### 🔴 Temuan #4: Inkompatibilitas Flag CLI PPanGGOLiN v2 (`--cpu` Flag Error)
- **Lokasi File:**
  - [workflow/rules/ppanggolin_roary.smk](file:///home/nanda/projects/bgcflow/workflow/rules/ppanggolin_roary.smk#L58-L78)
- **Gejala / Error:**
  `ppanggolin: error: unrecognized arguments: --cpu 16` pada `ppanggolin graph` dan `ppanggolin spot`.
- **Akar Masalah (Root Cause):**
  Pada upgrade PPanGGOLiN versi 2.3.0, subcommand `ppanggolin graph` dan `ppanggolin spot` tidak lagi menerima argumen multithreading `--cpu`. Kode pipeline lama masih menyertakan `--cpu {threads}` sehingga eksekusi graph building crash di step 3.
- **Perbaikan yang Dilakukan (Fix Applied):**
  Menghapus argumen `--cpu {threads}` dari pemanggilan `ppanggolin graph` dan `ppanggolin spot` di `ppanggolin_roary.smk`.

---

### 💡 Rekomendasi Resource HPC untuk Pengujian Cepat



- **CPU Cores:** `--cores 64` (Memanfaatkan 100% kuota CPU yang tersedia untuk eksekusi paralel maksimal).
- **RAM Constraint:** Cukup dialokasikan `--resources mem_mb=80000` (atau biarkan default untuk sub-rules ringan).
- **Strategi Storage 141 GB:** Database masif seperti GTDB-Tk (~100 GB) dinonaktifkan sementara selama audit fokus pada modul Pangenome dan BGC Mining.
