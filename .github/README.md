# GitHub Automation

This folder contains reusable GitHub Actions automation for Power BI/PBIP workflows.

## PBIP Change Summary

The workflow in [`workflows/pbip-summary.yml`](workflows/pbip-summary.yml) runs on pull requests that change PBIP-related files and posts a readable summary of report, semantic model, TMDL, JSON, M, and PQM changes.

The reviewer script lives in [`scripts/pbip_change_reviewer.py`](scripts/pbip_change_reviewer.py).

## Usage Notes

- The workflow is active in this repository, but it is mainly intended as a copy-ready example for PBIP repositories.
- If you copy it into another repository, keep the same `.github/scripts/pbip_change_reviewer.py` path or update the workflow path.
- The workflow requires `pull-requests: write` permission so it can post or update a PR comment.
