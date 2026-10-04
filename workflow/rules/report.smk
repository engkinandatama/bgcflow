rule copy_readme:
    output:
        "data/processed/{name}/README.md",
    log:
        "logs/report/copy-readme-{name}.log",
    shell:
        """
        cp workflow/notebook/README_template.md {output} 2>> {log}
        mkdir -p data/processed/{wildcards.name}/docs
        # Symlink interactive assets into docs so MkDocs serves them with 200 OK without 404
        for tool in antismash bigscape bigscape2 ppanggolin tables automlst_wrapper; do
            if [ -d "data/processed/{wildcards.name}/$tool" ] && [ ! -e "data/processed/{wildcards.name}/docs/$tool" ]; then
                ln -sf "../$tool" "data/processed/{wildcards.name}/docs/$tool" 2>> {log} || true
            fi
        done
        """

if len(py_wildcards) > 0:

    rule copy_template_notebook:
        output:
            notebook="data/processed/{name}/docs/{bgcflow_rules_py}.ipynb",
        conda:
            "../envs/bgcflow_notes.yaml"
        log:
            "logs/report/{bgcflow_rules_py}-report-copy-{name}.log",
        wildcard_constraints:
            bgcflow_rules_py="|".join(py_wildcards),
        params:
            notebook="workflow/notebook/{bgcflow_rules_py}.py.ipynb",
            fallback="workflow/notebook/template.py.ipynb",
        shell:
            """
            if [ -f "{params.notebook}" ]; then
                cp "{params.notebook}" "{output.notebook}" 2>> {log}
            else
                cp "{params.fallback}" "{output.notebook}" 2>> {log}
            fi
            """

    rule mkdocs_py_report:
        input:
            dependency_version = "data/processed/{name}/metadata/dependency_versions.json",
            notebook="data/processed/{name}/docs/{bgcflow_rules_py}.ipynb",
        output:
            markdown="data/processed/{name}/docs/{bgcflow_rules_py}.md",
        conda:
            "../envs/bgcflow_notes.yaml"
        log:
            "logs/report/{bgcflow_rules_py}-report-{name}.log",
        wildcard_constraints:
            bgcflow_rules_py="|".join(py_wildcards),
        shell:
            """
            python workflow/bgcflow/bgcflow/data/compile_notebook_report.py "{input.notebook}" "{output.markdown}" "{wildcards.name}" "{wildcards.bgcflow_rules_py}" "{log}"
            """


if len(rpy_wildcards) > 0:

    rule copy_template_rnotebook:
        output:
            notebook="data/processed/{name}/docs/{bgcflow_rules_rpy}.ipynb",
        conda:
            "../envs/bgcflow_notes.yaml"
        log:
            "logs/report/{bgcflow_rules_rpy}-report-copy-{name}.log",
        wildcard_constraints:
            bgcflow_rules_rpy="|".join(rpy_wildcards),
        params:
            notebook="workflow/notebook/{bgcflow_rules_rpy}.rpy.ipynb",
            fallback="workflow/notebook/template.py.ipynb",
        shell:
            """
            if [ -f "{params.notebook}" ]; then
                cp "{params.notebook}" "{output.notebook}" 2>> {log}
            else
                cp "{params.fallback}" "{output.notebook}" 2>> {log}
            fi
            """

    rule mkdocs_rpy_report:
        input:
            dependency_version = "data/processed/{name}/metadata/dependency_versions.json",
            notebook="data/processed/{name}/docs/{bgcflow_rules_rpy}.ipynb",
        output:
            markdown="data/processed/{name}/docs/{bgcflow_rules_rpy}.md",
        conda:
            "../envs/r_notebook.yaml"
        log:
            "logs/report/{bgcflow_rules_rpy}-report-{name}.log",
        wildcard_constraints:
            bgcflow_rules_rpy="|".join(rpy_wildcards),
        shell:
            """
            python workflow/bgcflow/bgcflow/data/compile_notebook_report.py "{input.notebook}" "{output.markdown}" "{wildcards.name}" "{wildcards.bgcflow_rules_rpy}" "{log}"
            """
