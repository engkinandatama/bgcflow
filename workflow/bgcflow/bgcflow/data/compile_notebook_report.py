import sys
import json
import subprocess
from pathlib import Path

def fallback_markdown(notebook_path, markdown_path, project_name, rule_name, reason="Module Not Executed"):
    title = rule_name.replace("-", " ").replace("_", " ").title()
    desc = f"The `{rule_name}` analysis was disabled (`FALSE`) in `project_config.yaml` or did not produce output for project `{project_name}`."
    
    # Try reading title & description from notebook if available
    if notebook_path.exists():
        try:
            with open(notebook_path, "r", encoding="utf-8") as f:
                nb = json.load(f)
            md_cells = [c["source"] for c in nb.get("cells", []) if c.get("cell_type") == "markdown"]
            if md_cells:
                first_cell = "".join(md_cells[0])
                if "# " in first_cell:
                    lines = first_cell.strip().split("\n")
                    title = lines[0].replace("# ", "").strip()
        except Exception:
            pass

    content = f"""# {title}

Summary of {title} results from project: `[{{{{ project().name }}}}]`

> ℹ️ **Notice: {reason}**
>
> {desc}
"""
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    if len(sys.argv) < 6:
        print("Usage: compile_notebook_report.py <notebook_path> <markdown_path> <project_name> <rule_name> <log_path>")
        sys.exit(1)

    notebook_path = Path(sys.argv[1]).resolve()
    markdown_path = Path(sys.argv[2]).resolve()
    project_name = sys.argv[3]
    rule_name = sys.argv[4]
    log_path = Path(sys.argv[5]).resolve()

    proc_dir = Path("data/processed") / project_name

    # Mapping of rules to representative output directories or files
    rule_outputs = {
        "antismash": proc_dir / "antismash",
        "bigscape": proc_dir / "bigscape",
        "bigscape2": proc_dir / "bigscape2",
        "ppanggolin": proc_dir / "ppanggolin",
        "ppanggolin_roary": proc_dir / "ppanggolin/genome_roary",
        "dbcan": proc_dir / "tables/df_cazyme.csv",
        "cazyme_gexf": proc_dir / "tables/df_bgc_cazyme_overlap.csv",
        "mash": proc_dir / "mash/df_mash.csv",
        "fastani": proc_dir / "fastani/df_fastani.csv",
        "roary": proc_dir / "roary",
        "seqfu": proc_dir / "tables/df_seqfu_stats.csv",
        "checkm": proc_dir / "tables/df_checkm_stats.csv",
        "gtdbtk": proc_dir / "tables/gtdbtk.bac120.summary.tsv",
        "prokka-gbk": proc_dir / "genbank",
        "automlst-wrapper": proc_dir / "automlst_wrapper/final.newick",
        "arts": proc_dir / "tables/df_arts_allhits_as-8.0.4.csv",
        "gecco": proc_dir / "gecco"
    }

    target = rule_outputs.get(rule_name)
    data_exists = False
    if target is not None:
        if target.exists():
            data_exists = True
    else:
        # Fallback dynamic detection
        if (proc_dir / rule_name).exists() or any(proc_dir.glob(f"tables/*{rule_name}*")):
            data_exists = True

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if data_exists and notebook_path.exists():
        # Execute notebook via nbconvert
        cmd = [
            "jupyter", "nbconvert",
            "--to", "markdown",
            "--execute",
            "--allow-errors",
            str(notebook_path),
            "--no-input",
            "--output", markdown_path.stem,
            "--output-dir", str(markdown_path.parent)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        with open(log_path, "a", encoding="utf-8") as f_log:
            f_log.write(f"--- Running {rule_name} notebook ---\n")
            f_log.write(res.stdout + "\n" + res.stderr + "\n")

        # Post-process: fix paths and sanitize any traceback
        if markdown_path.exists():
            content = markdown_path.read_text(encoding="utf-8")
            content = content.replace("{{ project().file_server() }}/antismash/", "antismash/")
            content = content.replace("{{ project().file_server() }}/bigscape/result_as", "bigscape2/result_as")
            content = content.replace("{{ project().file_server() }}/bigscape2/result_as", "bigscape2/result_as")
            content = content.replace("{{ project().file_server() }}/", "")

            if "Traceback (most recent call last):" in content and ("FileNotFoundError" in content or "KeyError" in content or "IndexError" in content):
                cleaned_header = f"""# {rule_name.replace('-', ' ').title()}

Summary of results from project: `[{{{{ project().name }}}}]`

> ℹ️ **Notice: Partial or Incomplete Data**
>
> The analysis output for `{rule_name}` was not found or was only partially generated for this project.
"""
                markdown_path.write_text(cleaned_header, encoding="utf-8")
            else:
                markdown_path.write_text(content, encoding="utf-8")
        else:
            fallback_markdown(notebook_path, markdown_path, project_name, rule_name, reason="Report Conversion Incomplete")
    else:
        fallback_markdown(notebook_path, markdown_path, project_name, rule_name, reason="Module Not Executed")
        with open(log_path, "a", encoding="utf-8") as f_log:
            f_log.write(f"--- Skipped {rule_name}: no output data present in {proc_dir} ---\n")

if __name__ == "__main__":
    main()
