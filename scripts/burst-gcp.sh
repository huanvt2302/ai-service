#!/usr/bin/env bash
# =============================================================================
# burst-gcp.sh — Setup and manage GCP Cloud Run burst layer
#
# This script automates all GCP infrastructure needed for the cloud burst layer:
#   - Enable GCP APIs
#   - Create Artifact Registry
#   - Create Cloud SQL instance (PostgreSQL + pgvector)
#   - Create Memorystore Redis
#   - Create Cloud Storage buckets
#   - Store secrets in Secret Manager
#   - Deploy backend + vLLM to Cloud Run
#   - Configure IAM service account
#
# Usage:
#   bash scripts/burst-gcp.sh <command>
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (`gcloud auth login`)
#   - .env file with GCP_PROJECT, GCP_REGION, etc.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ROOT}/.env"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GREEN}[burst-gcp]${NC} $*"; }
warn() { echo -e "${YELLOW}[burst-gcp]${NC} $*"; }
err()  { echo -e "${RED}[burst-gcp] ERROR:${NC} $*" >&2; exit 1; }
step() { echo -e "\n${BLUE}══ $* ══${NC}"; }

# Load .env
[[ -f "${ENV_FILE}" ]] && { set -a; source "${ENV_FILE}"; set +a; }

# Required vars
GCP_PROJECT="${GCP_PROJECT:-}"
GCP_REGION="${GCP_REGION:-asia-southeast1}"
REGISTRY="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/ai-service-repo"
SA_NAME="ai-service-sa"
SA_EMAIL="${SA_NAME}@${GCP_PROJECT}.iam.gserviceaccount.com"


# =============================================================================
# 1. ENABLE APIs
# =============================================================================
enable_apis() {
    step "Enabling GCP APIs"
    [[ -z "${GCP_PROJECT}" ]] && err "GCP_PROJECT not set in .env"

    gcloud config set project "${GCP_PROJECT}"

    gcloud services enable \
        run.googleapis.com \
        sql.googleapis.com \
        redis.googleapis.com \
        storage.googleapis.com \
        artifactregistry.googleapis.com \
        cloudbuild.googleapis.com \
        secretmanager.googleapis.com \
        monitoring.googleapis.com \
        logging.googleapis.com \
        compute.googleapis.com \
        --quiet

    log "✓ APIs enabled"
}


# =============================================================================
# 2. ARTIFACT REGISTRY
# =============================================================================
setup_registry() {
    step "Setting up Artifact Registry"
    gcloud artifacts repositories create ai-service-repo \
        --repository-format=docker \
        --location="${GCP_REGION}" \
        --description="AI Service Docker images" \
        --quiet 2>/dev/null || warn "Registry already exists"

    log "✓ Registry: ${REGISTRY}"
}


# =============================================================================
# 3. IAM SERVICE ACCOUNT
# =============================================================================
setup_iam() {
    step "Setting up IAM Service Account"

    # Create SA
    gcloud iam service-accounts create "${SA_NAME}" \
        --display-name="AI Service Runtime SA" \
        --quiet 2>/dev/null || warn "SA already exists"

    # Grant roles
    for role in \
        roles/cloudsql.client \
        roles/storage.objectAdmin \
        roles/secretmanager.secretAccessor \
        roles/run.admin \
        roles/monitoring.metricWriter \
        roles/logging.logWriter; do

        gcloud projects add-iam-policy-binding "${GCP_PROJECT}" \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="${role}" \
            --quiet > /dev/null
        log "  Granted ${role}"
    done

    log "✓ Service Account: ${SA_EMAIL}"

    # Download key for Burst Controller (mounted into container)
    KEY_FILE="${ROOT}/.gcp-sa-key.json"
    if [[ ! -f "${KEY_FILE}" ]]; then
        log "Downloading SA key to ${KEY_FILE} (for Burst Controller)..."
        gcloud iam service-accounts keys create "${KEY_FILE}" \
            --iam-account="${SA_EMAIL}"
        warn "  ⚠ Keep ${KEY_FILE} secret! Add to .gitignore."
    fi
}


# =============================================================================
# 4. CLOUD SQL (PostgreSQL 16 + pgvector)
# =============================================================================
setup_database() {
    step "Creating Cloud SQL (PostgreSQL 16 + pgvector)"
    DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -hex 16)}"

    # Create instance
    gcloud sql instances create ai-postgres \
        --database-version=POSTGRES_16 \
        --tier=db-g1-small \
        --region="${GCP_REGION}" \
        --storage-auto-increase \
        --database-flags=cloudsql.enable_pgvector=on \
        --quiet 2>/dev/null || warn "Cloud SQL instance already exists"

    # Create database
    gcloud sql databases create aiplatform \
        --instance=ai-postgres \
        --quiet 2>/dev/null || warn "Database already exists"

    # Create user
    gcloud sql users create aiplatform \
        --instance=ai-postgres \
        --password="${DB_PASSWORD}" \
        --quiet 2>/dev/null || warn "DB user already exists"

    INSTANCE_CONNECTION="${GCP_PROJECT}:${GCP_REGION}:ai-postgres"
    CLOUD_SQL_URL="postgresql://aiplatform:${DB_PASSWORD}@/aiplatform?host=/cloudsql/${INSTANCE_CONNECTION}"

    log "✓ Cloud SQL ready"
    log "  Instance connection: ${INSTANCE_CONNECTION}"
    echo "  DATABASE_URL_CLOUD=${CLOUD_SQL_URL}" >> "${ENV_FILE}"
    log "  Saved DATABASE_URL_CLOUD to .env"
}


# =============================================================================
# 5. MEMORYSTORE REDIS
# =============================================================================
setup_redis() {
    step "Creating Memorystore Redis 7"

    gcloud redis instances create ai-redis \
        --size=1 \
        --region="${GCP_REGION}" \
        --redis-version=redis_7_0 \
        --tier=BASIC \
        --quiet 2>/dev/null || warn "Redis instance already exists"

    REDIS_HOST=$(gcloud redis instances describe ai-redis \
        --region="${GCP_REGION}" \
        --format="value(host)")
    CLOUD_REDIS_URL="redis://${REDIS_HOST}:6379"

    log "✓ Redis: ${CLOUD_REDIS_URL}"
    echo "  REDIS_URL_CLOUD=${CLOUD_REDIS_URL}" >> "${ENV_FILE}"
}


# =============================================================================
# 6. CLOUD STORAGE BUCKETS
# =============================================================================
setup_storage() {
    step "Creating Cloud Storage Buckets"

    gcloud storage buckets create "gs://${GCP_PROJECT}-ai-uploads" \
        --location="${GCP_REGION}" \
        --uniform-bucket-level-access \
        --quiet 2>/dev/null || warn "Uploads bucket already exists"

    gcloud storage buckets create "gs://${GCP_PROJECT}-hf-cache" \
        --location="${GCP_REGION}" \
        --uniform-bucket-level-access \
        --quiet 2>/dev/null || warn "HF cache bucket already exists"

    log "✓ Buckets: gs://${GCP_PROJECT}-ai-uploads, gs://${GCP_PROJECT}-hf-cache"
    echo "GCS_BUCKET=${GCP_PROJECT}-ai-uploads" >> "${ENV_FILE}"
}


# =============================================================================
# 7. SECRET MANAGER
# =============================================================================
setup_secrets() {
    step "Populating Secret Manager"

    _upsert_secret() {
        local name="$1"
        local value="$2"
        echo -n "${value}" | gcloud secrets create "${name}" \
            --data-file=- --quiet 2>/dev/null \
        || echo -n "${value}" | gcloud secrets versions add "${name}" \
            --data-file=- --quiet
        log "  ✓ ${name}"
    }

    source "${ENV_FILE}"
    _upsert_secret "DATABASE_URL"     "${DATABASE_URL_CLOUD:-${DATABASE_URL}}"
    _upsert_secret "REDIS_URL"        "${REDIS_URL_CLOUD:-${REDIS_URL}}"
    _upsert_secret "JWT_SECRET"       "${JWT_SECRET:?JWT_SECRET required in .env}"
    _upsert_secret "HF_TOKEN"         "${HF_TOKEN:-}"
    _upsert_secret "NEXTAUTH_SECRET"  "${NEXTAUTH_SECRET:?NEXTAUTH_SECRET required in .env}"

    log "✓ Secrets stored in Secret Manager"
}


# =============================================================================
# 8. BUILD & PUSH IMAGES TO ARTIFACT REGISTRY
# =============================================================================
build_images() {
    step "Building images → Artifact Registry"
    TAG="${1:-latest}"

    for svc in backend frontend hybrid-router burst-controller; do
        if [[ -d "${ROOT}/${svc}" ]]; then
            IMAGE="${REGISTRY}/${svc}:${TAG}"
            log "  Building ${svc} → ${IMAGE}"
            docker build -t "${IMAGE}" "${ROOT}/${svc}"
            docker push "${IMAGE}"
            log "  ✓ ${IMAGE}"
        else
            warn "  Skipping ${svc} (directory not found)"
        fi
    done

    log "✓ Images pushed to ${REGISTRY}"
}


# =============================================================================
# 9. DEPLOY TO CLOUD RUN
# =============================================================================
deploy_cloud_run() {
    step "Deploying Cloud Run services"
    TAG="${1:-latest}"
    source "${ENV_FILE}"

    INSTANCE_CONNECTION="${GCP_PROJECT}:${GCP_REGION}:ai-postgres"

    # ──  Backend ──────────────────────────────────────────────────────────────
    log "Deploying ai-backend..."
    gcloud run deploy ai-backend \
        --image="${REGISTRY}/backend:${TAG}" \
        --region="${GCP_REGION}" \
        --platform=managed \
        --no-allow-unauthenticated \
        --service-account="${SA_EMAIL}" \
        --min-instances=0 \
        --max-instances=20 \
        --concurrency=80 \
        --cpu=2 \
        --memory=2Gi \
        --timeout=300 \
        --add-cloudsql-instances="${INSTANCE_CONNECTION}" \
        --set-secrets="DATABASE_URL=DATABASE_URL:latest,REDIS_URL=REDIS_URL:latest,JWT_SECRET=JWT_SECRET:latest" \
        --set-env-vars="LLM_BASE_URL=\${VLLM_CLOUD_URL:-}" \
        --port=8080 \
        --quiet

    BACKEND_URL=$(gcloud run services describe ai-backend \
        --region="${GCP_REGION}" --format="value(status.url)")
    log "  ✓ Backend: ${BACKEND_URL}"

    # ── vLLM (GPU) ────────────────────────────────────────────────────────────
    log "Deploying ai-vllm (GPU — requires quota)..."
    gcloud run deploy ai-vllm \
        --image="vllm/vllm-openai:latest" \
        --region="${GCP_REGION}" \
        --platform=managed \
        --no-allow-unauthenticated \
        --service-account="${SA_EMAIL}" \
        --min-instances=0 \
        --max-instances=20 \
        --concurrency=10 \
        --cpu=4 \
        --memory=16Gi \
        --gpu=1 \
        --gpu-type=nvidia-l4 \
        --timeout=3600 \
        --args="--model,${VLLM_MODEL:-Qwen/Qwen2.5-3B-Instruct},--served-model-name,${VLLM_SERVED_NAME:-qwen3.5-plus},--host,0.0.0.0,--port,8000" \
        --set-secrets="HUGGING_FACE_HUB_TOKEN=HF_TOKEN:latest" \
        --port=8000 \
        --quiet 2>/dev/null || warn "  vLLM GPU deploy may require quota increase. Check GCP console."

    # ── Update backend with vLLM URL ──────────────────────────────────────────
    VLLM_URL=$(gcloud run services describe ai-vllm \
        --region="${GCP_REGION}" --format="value(status.url)" 2>/dev/null || echo "")
    if [[ -n "${VLLM_URL}" ]]; then
        gcloud run services update ai-backend \
            --region="${GCP_REGION}" \
            --set-env-vars="LLM_BASE_URL=${VLLM_URL}" \
            --quiet
    fi

    echo ""
    echo "══════════════════════════════════════════════════════════════════════"
    echo "  ✅ Cloud Run deployment complete!"
    echo ""
    echo "  Backend URL: ${BACKEND_URL}"
    echo ""
    echo "  👉 Add to your local .env:"
    echo "     CLOUD_BACKEND_URL=${BACKEND_URL}"
    echo ""
    echo "  Then update the Swarm stack:"
    echo "     docker service update --env-add CLOUD_BACKEND_URL=${BACKEND_URL} ai-platform_hybrid-router"
    echo "══════════════════════════════════════════════════════════════════════"
}


# =============================================================================
# STATUS
# =============================================================================
status() {
    step "Cloud Run Services"
    gcloud run services list --region="${GCP_REGION}" --format="table(name,status.url,spec.template.spec.containerConcurrency)"
    echo ""
    step "Burst Controller Scaling State"
    for svc in ai-backend ai-vllm; do
        MIN=$(gcloud run services describe "${svc}" \
            --region="${GCP_REGION}" \
            --format="value(spec.template.metadata.annotations['autoscaling.knative.dev/minScale'])" 2>/dev/null || echo "N/A")
        MAX=$(gcloud run services describe "${svc}" \
            --region="${GCP_REGION}" \
            --format="value(spec.template.metadata.annotations['autoscaling.knative.dev/maxScale'])" 2>/dev/null || echo "N/A")
        log "  ${svc}: min=${MIN} max=${MAX}"
    done
}


# =============================================================================
# TEARDOWN (CAREFUL!)
# =============================================================================
teardown() {
    warn "This will DELETE all Cloud Run services, Cloud SQL, and Redis!"
    read -p "Type 'yes' to confirm: " -r
    [[ "${REPLY}" != "yes" ]] && { log "Cancelled."; exit 0; }

    gcloud run services delete ai-backend --region="${GCP_REGION}" --quiet 2>/dev/null || true
    gcloud run services delete ai-vllm    --region="${GCP_REGION}" --quiet 2>/dev/null || true
    gcloud sql instances delete ai-postgres --quiet 2>/dev/null || true
    gcloud redis instances delete ai-redis --region="${GCP_REGION}" --quiet 2>/dev/null || true
    log "Teardown complete."
}


# =============================================================================
# MAIN
# =============================================================================
CMD="${1:-help}"
shift || true

case "${CMD}" in
    enable-apis)     enable_apis ;;
    setup-registry)  setup_registry ;;
    setup-iam)       setup_iam ;;
    setup-database)  setup_database ;;
    setup-redis)     setup_redis ;;
    setup-storage)   setup_storage ;;
    setup-secrets)   setup_secrets ;;
    build)           build_images "$@" ;;
    deploy)          deploy_cloud_run "$@" ;;
    status)          status ;;
    teardown)        teardown ;;
    all)
        # Full setup from scratch
        enable_apis
        setup_registry
        setup_iam
        setup_database
        setup_redis
        setup_storage
        setup_secrets
        build_images "${1:-latest}"
        deploy_cloud_run "${1:-latest}"
        ;;
    *)
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands (run in order for fresh setup):"
        echo "  all [tag]           — Run all setup steps + deploy"
        echo "  enable-apis         — Enable required GCP APIs"
        echo "  setup-registry      — Create Artifact Registry"
        echo "  setup-iam           — Create Service Account + roles"
        echo "  setup-database      — Create Cloud SQL (PostgreSQL + pgvector)"
        echo "  setup-redis         — Create Memorystore Redis"
        echo "  setup-storage       — Create GCS buckets"
        echo "  setup-secrets       — Populate Secret Manager"
        echo "  build [tag]         — Build & push images to Artifact Registry"
        echo "  deploy [tag]        — Deploy to Cloud Run"
        echo "  status              — Show current Cloud Run status"
        echo "  teardown            — Delete all cloud resources (CAREFUL!)"
        exit 1
        ;;
esac
