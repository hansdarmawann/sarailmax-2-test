"""Deploy item Fabric dari repo ini ke workspace target menggunakan fabric-cicd.

Lokal (setelah `az login`):
    python .deploy/deploy.py --environment TEST --workspace_id <workspace-id>

Di GitHub Actions, kredensial service principal dibaca dari environment variable
AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, dan workspace dari
FABRIC_WORKSPACE_ID.
"""

import argparse
import os
import sys
from pathlib import Path

from azure.identity import AzureCliCredential, ClientSecretCredential
from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items

REPO_ROOT = Path(__file__).resolve().parent.parent

# Workspace Test tersinkron langsung dengan Git (sumber repo ini), jadi tidak boleh jadi target deploy.
SOURCE_WORKSPACE_ID = "00821748-8426-4cd3-ba81-824368c7e101"

# MLExperiment dan MLModel sengaja tidak di-deploy: MLModel tidak didukung fabric-cicd,
# dan keduanya dibuat sendiri oleh SarailmaxNB saat dijalankan di workspace target.
ITEM_TYPES = ["Lakehouse", "Environment", "Notebook"]

SPN_VARS = ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET")


def get_credential():
    if all(os.getenv(name) for name in SPN_VARS):
        return ClientSecretCredential(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
        )
    if os.getenv("CI"):
        missing = ", ".join(name for name in SPN_VARS if not os.getenv(name))
        sys.exit(f"ERROR: secret belum diisi di GitHub Environment: {missing}")
    return AzureCliCredential()


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=["PROD"],
        help="Harus sama dengan key di parameter.yml",
    )
    parser.add_argument(
        "--workspace_id",
        default=os.getenv("FABRIC_WORKSPACE_ID"),
        help="ID workspace target (default: env FABRIC_WORKSPACE_ID)",
    )
    args = parser.parse_args()

    if SOURCE_WORKSPACE_ID.startswith("TODO") or "TODO" in (REPO_ROOT / "parameter.yml").read_text(encoding="utf-8"):
        sys.exit("ERROR: SOURCE_WORKSPACE_ID di deploy.py dan nilai find_value di parameter.yml masih placeholder TODO.")
    if not args.workspace_id:
        sys.exit("ERROR: workspace ID kosong. Isi --workspace_id atau variable FABRIC_WORKSPACE_ID.")
    if args.workspace_id.lower() == SOURCE_WORKSPACE_ID:
        sys.exit("ERROR: workspace target adalah workspace Test (tersinkron Git). Gunakan workspace Prod.")

    workspace = FabricWorkspace(
        workspace_id=args.workspace_id,
        environment=args.environment,
        repository_directory=str(REPO_ROOT),
        item_type_in_scope=ITEM_TYPES,
        token_credential=get_credential(),
    )
    publish_all_items(workspace)
    # Menghapus Notebook/Environment di target yang sudah tidak ada di repo.
    # Lakehouse tidak ikut dihapus (butuh feature flag enable_lakehouse_unpublish).
    unpublish_all_orphan_items(workspace)


if __name__ == "__main__":
    main()
