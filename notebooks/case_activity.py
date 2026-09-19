# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "httpx", "pandas"]
# ///
"""
FindMyPal Activity Explorer (marimo)

Run (optional):
  pip install marimo httpx pandas
  marimo run notebooks/case_activity.py

This notebook calls the FastAPI analytics route — it does not embed DB credentials.
"""

import marimo

__generated_with = "0.0.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import httpx
    import pandas as pd
    return httpx, mo, pd


@app.cell
def _(mo):
    api = mo.ui.text(value="http://127.0.0.1:8000", label="API base")
    person_id = mo.ui.text(value="", label="Person UUID")
    bucket = mo.ui.slider(1, 72, value=24, label="Bucket hours")
    mo.vstack([api, person_id, bucket])
    return api, bucket, person_id


@app.cell
def _(api, bucket, httpx, mo, pd, person_id):
    if not person_id.value.strip():
        mo.md("Enter a person UUID from an active FindMyPal case.")
    else:
        url = f"{api.value.rstrip('/')}/analytics/case-activity/{person_id.value.strip()}?bucket_hours={bucket.value}"
        r = httpx.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data.get("series") or [])
        mo.vstack(
            [
                mo.md(f"**Tips:** {data.get('total_tips')} · provenance `{data.get('provenance')}`"),
                df if not df.empty else mo.md("No tips yet."),
            ]
        )
    return


if __name__ == "__main__":
    app.run()
