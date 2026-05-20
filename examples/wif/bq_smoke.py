"""Five-line smoke test that proves WIF works end-to-end.

Run from inside the sync job's container (or any environment where the Azure
managed identity is reachable and GOOGLE_APPLICATION_CREDENTIALS points at
the external_account JSON produced by examples/wif/terraform).

The Python is identical to the SA-key flow — google-auth dispatches on the
JSON's `type` field.
"""

from __future__ import annotations

import os

from google.cloud import bigquery


def main() -> None:
    creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    project = os.environ["BQ_PROJECT_ID"]
    print(f"Using credentials at: {creds_path}")
    print(f"BigQuery project:     {project}")

    client = bigquery.Client(project=project)
    row = next(iter(client.query("SELECT CURRENT_TIMESTAMP() AS ts").result()))
    print(f"BigQuery returned:    {row.ts}")


if __name__ == "__main__":
    main()
