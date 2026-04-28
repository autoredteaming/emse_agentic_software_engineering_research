"""For each sampled (src,tgt) pair, build a self-contained evidence pack.

Evidence pack = JSON with:
  - src: title, body (truncated), task_type, files, patches (truncated)
  - tgt: title, body (truncated), task_type, patches that touch shared files
  - shared_files: filenames common to src and tgt
  - overlap_frac, agent, language

Memory-careful: we read pr_commit_details with a row-group / column-selective
read filtered to the union of all sample pr_ids (~120 unique), then group
in-memory.

Output: qual/evidence_packs.jsonl  (60 lines)
"""
import os
import json
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(__file__)
DATA = "/home/ubuntu/emse_agentic_software_engineering_V2/AIDev_datasets"

PATCH_LINE_LIMIT = 80   # per file
PATCHES_PER_PR = 6      # max files per PR shown
BODY_CHAR_LIMIT = 600


def truncate_patch(patch: str) -> str:
    if not isinstance(patch, str):
        return ""
    lines = patch.splitlines()
    if len(lines) <= PATCH_LINE_LIMIT:
        return patch
    head = lines[: PATCH_LINE_LIMIT // 2]
    tail = lines[-PATCH_LINE_LIMIT // 2 :]
    return "\n".join(head + [f"... [{len(lines) - PATCH_LINE_LIMIT} lines elided] ..."] + tail)


def build_pr_pack(group: pd.DataFrame, prefer_files: set) -> dict:
    """Pick up to PATCHES_PER_PR files for one PR, prioritizing prefer_files."""
    g = group.copy()
    g["is_pref"] = g["filename"].isin(prefer_files).astype(int)
    g = g.sort_values(["is_pref", "changes"], ascending=[False, False])
    rows = g.head(PATCHES_PER_PR)
    files = []
    for _, r in rows.iterrows():
        files.append(
            {
                "filename": r["filename"],
                "status": r["status"],
                "additions": int(r["additions"]) if pd.notna(r["additions"]) else 0,
                "deletions": int(r["deletions"]) if pd.notna(r["deletions"]) else 0,
                "patch": truncate_patch(r["patch"]),
            }
        )
    return {"files": files, "n_files_total": int(g["filename"].nunique())}


def main() -> None:
    sample = pd.read_csv(os.path.join(HERE, "sample_pairs.csv"))
    print(f"[evid] sample n = {len(sample)}")

    pr_ids = pd.unique(pd.concat([sample["src_pr"], sample["tgt_pr"]]))
    print(f"[evid] unique pr_ids: {len(pr_ids)}")

    # PR meta (title + body)
    pr_meta = pd.read_parquet(
        os.path.join(DATA, "pull_request.parquet"),
        columns=["id", "title", "body", "html_url"],
    )
    pr_meta = pr_meta[pr_meta["id"].isin(pr_ids)].set_index("id")
    print(f"[evid] meta rows: {len(pr_meta)}")

    # Task type
    task = pd.read_parquet(
        os.path.join(DATA, "pr_task_type.parquet"),
        columns=["id", "type", "reason"],
    )
    task = task[task["id"].isin(pr_ids)].drop_duplicates("id").set_index("id")

    # Commit details: stream batches, keep only relevant pr_ids
    print("[evid] streaming pr_commit_details...")
    pf = pq.ParquetFile(os.path.join(DATA, "pr_commit_details.parquet"))
    keep_ids = set(int(x) for x in pr_ids)
    parts = []
    for batch in pf.iter_batches(
        batch_size=20000,
        columns=["pr_id", "filename", "status", "additions",
                 "deletions", "changes", "patch"],
    ):
        b = batch.to_pandas()
        b = b[b["pr_id"].isin(keep_ids)]
        if len(b):
            parts.append(b)
    pcd = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    print(f"[evid] commit rows: {len(pcd):,}")

    # Build packs
    packs = []
    for _, row in sample.iterrows():
        src_id = int(row["src_pr"])
        tgt_id = int(row["tgt_pr"])
        src_files_df = pcd[pcd["pr_id"] == src_id].dropna(subset=["filename"]).copy()
        tgt_files_df = pcd[pcd["pr_id"] == tgt_id].dropna(subset=["filename"]).copy()
        if len(src_files_df) == 0 or len(tgt_files_df) == 0:
            continue
        shared = set(src_files_df["filename"]) & set(tgt_files_df["filename"])
        shared = {f for f in shared if isinstance(f, str)}

        def _meta(pid):
            if pid in pr_meta.index:
                m = pr_meta.loc[pid]
                title = m["title"] if isinstance(m["title"], str) else ""
                body = m["body"] if isinstance(m["body"], str) else ""
                url = m["html_url"] if isinstance(m["html_url"], str) else ""
            else:
                title, body, url = "", "", ""
            t = task.loc[pid]["type"] if pid in task.index else ""
            return title, body[:BODY_CHAR_LIMIT], url, t

        s_title, s_body, s_url, s_task = _meta(src_id)
        t_title, t_body, t_url, t_task = _meta(tgt_id)

        pack = {
            "src_pr": src_id,
            "tgt_pr": tgt_id,
            "agent": row["agent"],
            "language": row["language"],
            "overlap_frac": float(row["overlap_frac"]),
            "shared_files": sorted(shared),
            "src": {
                "title": s_title,
                "body": s_body,
                "task_type": s_task,
                "url": s_url,
                **build_pr_pack(src_files_df, shared),
            },
            "tgt": {
                "title": t_title,
                "body": t_body,
                "task_type": t_task,
                "url": t_url,
                **build_pr_pack(tgt_files_df, shared),
            },
        }
        packs.append(pack)

    out = os.path.join(HERE, "evidence_packs.jsonl")
    with open(out, "w") as fh:
        for p in packs:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"[evid] wrote {len(packs)} packs -> {out}")

    # Quick stats
    avg_files = sum(len(p["src"]["files"]) + len(p["tgt"]["files"]) for p in packs) / max(len(packs), 1)
    print(f"[evid] avg files per pack: {avg_files:.1f}")
    sizes_kb = [len(json.dumps(p)) / 1024 for p in packs]
    print(f"[evid] pack size kb: min={min(sizes_kb):.1f} med={sorted(sizes_kb)[len(sizes_kb)//2]:.1f} max={max(sizes_kb):.1f}")


if __name__ == "__main__":
    main()
