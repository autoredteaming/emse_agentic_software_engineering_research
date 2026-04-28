"""Memory-efficient loaders for the AIDev parquet corpus.

All public methods use column-selective reads so the 2 GB RAM environment
can process the 460 MB pr_commit_details table without OOMs.
"""
import os
import pandas as pd

DATA_DIR = "/home/ubuntu/emse_agentic_software_engineering_V2/AIDev_datasets"


class AIDev:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir

    def _p(self, name: str) -> str:
        return os.path.join(self.data_dir, name)

    # ---- PR metadata ----
    def load_agent_prs(self, merged_only: bool = True) -> pd.DataFrame:
        df = pd.read_parquet(
            self._p("pull_request.parquet"),
            columns=[
                "id", "number", "agent", "state",
                "created_at", "closed_at", "merged_at",
                "repo_id", "repo_url", "user_id", "user",
            ],
        )
        df["is_agent"] = 1
        if merged_only:
            df = df[df["merged_at"].notna()].copy()
        for c in ("created_at", "closed_at", "merged_at"):
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
        return df

    def load_human_prs(self, merged_only: bool = True) -> pd.DataFrame:
        df = pd.read_parquet(
            self._p("human_pull_request.parquet"),
            columns=[
                "id", "number", "agent", "state",
                "created_at", "closed_at", "merged_at",
                "repo_url", "user_id", "user",
            ],
        )
        df["is_agent"] = 0
        df["agent"] = "Human"
        if merged_only:
            df = df[df["merged_at"].notna()].copy()
        for c in ("created_at", "closed_at", "merged_at"):
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
        return df

    def load_task_types(self) -> pd.DataFrame:
        a = pd.read_parquet(self._p("pr_task_type.parquet"), columns=["id", "type"])
        h = pd.read_parquet(self._p("human_pr_task_type.parquet"), columns=["id", "type"])
        return pd.concat([a, h], ignore_index=True).drop_duplicates("id")

    def load_repos(self) -> pd.DataFrame:
        return pd.read_parquet(
            self._p("repository.parquet"),
            columns=["id", "url", "full_name", "language", "stars", "forks", "license"],
        ).rename(columns={"id": "repo_id"})

    # ---- PR commit details (column-selective) ----
    def load_commit_stats(self, pr_ids=None) -> pd.DataFrame:
        cols = [
            "sha", "pr_id", "filename", "status",
            "additions", "deletions", "changes",
            "commit_stats_total", "commit_stats_additions", "commit_stats_deletions",
        ]
        df = pd.read_parquet(self._p("pr_commit_details.parquet"), columns=cols)
        if pr_ids is not None:
            df = df[df["pr_id"].isin(pr_ids)].copy()
        return df

    def load_file_index(self) -> pd.DataFrame:
        """Per-(pr_id, filename) dedup — used by survival + follow-up mining."""
        df = pd.read_parquet(
            self._p("pr_commit_details.parquet"),
            columns=["pr_id", "filename"],
        )
        df = df.dropna(subset=["filename"])
        df = df[df["filename"].str.len() > 0]
        return df.drop_duplicates(["pr_id", "filename"])

    # ---- review/comment/timeline/issue ----
    def load_reviews(self) -> pd.DataFrame:
        return pd.read_parquet(
            self._p("pr_reviews.parquet"),
            columns=["pr_id", "user", "user_type", "state", "submitted_at"],
        )

    def load_comments(self) -> pd.DataFrame:
        return pd.read_parquet(
            self._p("pr_comments.parquet"),
            columns=["pr_id", "user", "user_type", "created_at", "body"],
        )

    def load_timeline(self, events=None, cols=None) -> pd.DataFrame:
        c = cols or ["pr_id", "event", "commit_id", "created_at", "actor", "message"]
        df = pd.read_parquet(self._p("pr_timeline.parquet"), columns=c)
        if events is not None:
            df = df[df["event"].isin(events)].copy()
        return df

    def load_related_issue(self) -> pd.DataFrame:
        return pd.read_parquet(self._p("related_issue.parquet"))

    def load_issues(self) -> pd.DataFrame:
        return pd.read_parquet(
            self._p("issue.parquet"),
            columns=["id", "number", "title", "state",
                     "created_at", "closed_at", "html_url"],
        )


if __name__ == "__main__":
    ai = AIDev()
    a = ai.load_agent_prs()
    h = ai.load_human_prs()
    print(f"merged agent: {len(a):,}")
    print(f"merged human: {len(h):,}")
    print(f"agent window: {a['merged_at'].min()} -> {a['merged_at'].max()}")
