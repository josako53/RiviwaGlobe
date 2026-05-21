#!/bin/bash
# =============================================================================
# Connect GitHub → Cloud Build trigger
# Run once after setup.sh. Creates a Cloud Build trigger that fires on
# every push to the 'main' branch of josako53/RiviwaGlobe.
#
#   bash gcp/connect-github.sh
# =============================================================================
set -euo pipefail

PROJECT_ID="riviwa"
REGION="me-west1"
GITHUB_OWNER="josako53"
GITHUB_REPO="RiviwaGlobe"

G='\033[0;32m'; N='\033[0m'
info() { echo -e "${G}[✓]${N} $*"; }

echo "Connecting GitHub repository ${GITHUB_OWNER}/${GITHUB_REPO} to Cloud Build..."
echo ""
echo "Step 1: Open the Cloud Build GitHub App link below and install it"
echo "        on the josako53 GitHub account (select RiviwaGlobe repo only):"
echo ""
echo "  https://console.cloud.google.com/cloud-build/triggers/connect?project=${PROJECT_ID}"
echo ""
echo "After connecting, press ENTER to create the trigger..."
read -r

# Create the push-to-main trigger
gcloud builds triggers create github \
  --name="deploy-on-push-main" \
  --repo-owner="$GITHUB_OWNER" \
  --repo-name="$GITHUB_REPO" \
  --branch-pattern="^main$" \
  --build-config="gcp/cloudbuild.yaml" \
  --region="global" \
  --description="Deploy all Cloud Run services on push to main" \
  --project=$PROJECT_ID

info "Cloud Build trigger created!"
echo ""
echo "  Every push to github.com/${GITHUB_OWNER}/${GITHUB_REPO}/main"
echo "  will now automatically build and deploy all 15 Cloud Run services."
echo ""
echo "  Monitor builds: https://console.cloud.google.com/cloud-build/builds?project=${PROJECT_ID}"
