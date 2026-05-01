# Git Push Checklist

Use this checklist before sharing the repository publicly.

## 1. Review the generated outputs

```bash
make PYTHON=.venv/bin/python check
git status --short
```

## 2. Remove tracked macOS metadata from Git

`.DS_Store` is already tracked in the existing repository history. The new `.gitignore` prevents future accidental additions, but tracked files need to be removed from Git explicitly:

```bash
git rm --cached .DS_Store
```

This does not delete the local `.DS_Store` file from your laptop.

## 3. Stage the portfolio-ready files

```bash
git add .gitignore Makefile README.md requirements.txt
git add data figures notebooks reports src
```

## 4. Commit and push

```bash
git commit -m "Organize FDA citizen petition research project"
git push origin main
```

## 5. Final GitHub checks

- README renders cleanly on GitHub.
- Figures are visible in the `figures/` folder.
- `reports/research_brief.md` reads like a polished writing sample.
- `reports/writing_sample/Kyaw_Min_Khant_FDA_Citizen_Petitions_Research_Paper.pdf` is ready as the standalone research paper.
- `reports/methods_comparison.md` clearly differentiates this work from the reference repositories.
- Raw PDFs, virtual environments, and local system files are not included.
