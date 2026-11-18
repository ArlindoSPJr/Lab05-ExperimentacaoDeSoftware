# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

`Lab05Medicao.pdf` is the assignment statement for "Lab05 — Experimento em Software Real" (Laboratório de Experimentação de Software, Engenharia de Software, PUC Minas). It is written in Portuguese, and deliverables (documents, slides, reports) should be in Portuguese unless the user says otherwise.

The chosen study is the **performance and accessibility of the Mercado Livre website**, measured from outside through the PageSpeed Insights API on a GitHub Actions schedule. Sources of truth:
- Design: `docs/superpowers/specs/2026-11-16-mercadolivre-desempenho-acessibilidade-design.md`
- Issues by wave and sprint: `docs/superpowers/plans/2026-11-16-issues-ondas.md`, mirrored as GitHub issues on the Kanban https://github.com/users/ArlindoSPJr/projects/7

## Workflow rules

- **Every commit must reference its GitHub issue** by number in the message, e.g. `Refs #5`. The Pull Request that completes an issue carries `Closes #5` in its description; commits use only `Refs #N`. The issue-to-number map is in each issue's title (`[A-4]` etc.).
- Work moves in sequential waves A → B → C. Issues start in **Backlog** and move to **Ready** only once all their dependencies are done (the end of the previous wave).

## What this project is

A group of three students plans, runs, and analyzes an experiment on a **real, in-production, high-impact software system**, then answers "what did the study show?" and "what does it mean for the people who use this software?". The group chooses the software, the research question, the study type, the metrics, and the formats of the document and the presentation. The grade depends on how good those choices are and how well they apply course concepts.

## Hard constraints from the assignment (do not violate)

- **No GitHub repository mining as the object of study**: no mining commits, issues, or PRs, and no static analysis of OSS source code (that was Labs 01/03). Running an OSS system that companies use in production (e.g., PostgreSQL) in the group's own environment is allowed. In that case the object of study is the running software, not its repository.
- **Ethics when measuring third-party services**: no load or stress testing of others' systems, respect ToS and `robots.txt`, **max 1 request/second**, and collect no personal data. Any load testing must target software running locally. Scripts that hit external endpoints must enforce this rate limit.
- With human participants: get consent, and do not use their real accounts or data.
- Each group must study a different software than the other groups.
- The software must show evidence (numbers plus sources, with link and access date) of being **real**, **in operation** (maintained version, recent release), and **high impact** (users, downloads, companies, transactions).

## Expected study structure

Possible approaches, which may be combined (combining them is valued): run the software locally while varying versions, configs, or load; measure a public service from outside; a user study; analysis of published operational data (status pages, postmortems, open gov data); survey or interviews; ISO/IEC 25010 quality evaluation (e.g., WCAG via axe/Lighthouse, HTTP security headers).

Course concepts the work is expected to apply:
- GQM (Basili template), entity/attribute classification, the measurement scale of each metric and the statistics that scale allows, and measurement pitfalls (Goodhart, Campbell, McNamara).
- Classification into the **7 research categories** (Aula 8): nature, objectives, approach, procedures, time, control, and level of evidence, each with a justification.
- Experiment planning: hypotheses, variables, subjects/objects, design, instrumentation.
- Analysis: descriptive statistics, a hypothesis test suited to the data and scale, and effect size.
- The 4 types of threats to validity (conclusion, internal, construct, external), each with mitigation.
- An impact estimate translated to real-world numbers, stating clearly what *cannot* be claimed.

Material that may be reused from earlier labs: automated API collection and a GitHub Projects Kanban (Lab01), treatment/participant design (Lab02), DORA metrics (Lab03), and hypothesis test choice, type I error/power simulation, and a dashboard (Lab04).

## Sprints

| Sprint | Deliverable |
|---|---|
| Lab05S01 | Proposal: software plus evidence for the 3 criteria, research question, approach, first version of the 7 categories, collection and analysis plan, pilot collection |
| Lab05S02 | Full collection, data validated and **versioned in the repo**, analysis, threats to validity |
| Lab05S03 | Impact estimate, revised 7 categories, conclusions and limitations, drafts of the document and presentation |
| Final | Document plus a 10-minute presentation (free format) |

Any team member may be asked to explain any part of the work, so keep scripts and analyses readable and documented.
