#!/usr/bin/env bash
# =============================================================================
# setup-swarm.sh — Initialize Docker Swarm cluster across 3 machines
#
# Usage:
#   On Machine 1 (Manager): bash scripts/setup-swarm.sh manager
#   On Machine 2 & 3 (Workers): bash scripts/setup-swarm.sh worker <JOIN_TOKEN> <MANAGER_IP>
#
# Prerequisites:
#   - Docker installed on all machines
#   - SSH access from Machine 1 to Machine 2 & 3
#   - Port 2377 (Swarm management), 7946 (node comms), 4789 (overlay) open in firewall
# =============================================================================
set -euo pipefail

ROLE="${1:-}"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[setup-swarm]${NC} $*"; }
warn() { echo -e "${YELLOW}[setup-swarm]${NC} $*"; }
err()  { echo -e "${RED}[setup-swarm] ERROR:${NC} $*" >&2; exit 1; }

# ── Detect local IP ───────────────────────────────────────────────────────────
LOCAL_IP=$(hostname -I | awk '{print $1}')

# =============================================================================
# MANAGER SETUP
# =============================================================================
setup_manager() {
    log "Setting up Manager node (IP: ${LOCAL_IP})"

    # Check Docker
    docker info > /dev/null 2>&1 || err "Docker is not running. Start Docker first."

    # Init swarm if not already in one
    if docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active"; then
        warn "This node is already part of a Swarm. Skipping init."
    else
        log "Initializing Docker Swarm..."
        docker swarm init --advertise-addr "${LOCAL_IP}"
        log "Swarm initialized!"
    fi

    # ── Labels ────────────────────────────────────────────────────────────────
    MANAGER_ID=$(docker node ls --filter role=manager --format "{{.ID}}" | head -1)
    docker node update --label-add pg=primary "${MANAGER_ID}" 2>/dev/null || true
    log "Labeled manager node with pg=primary"

    # ── Local Docker Registry ─────────────────────────────────────────────────
    if ! docker service ls --filter name=registry -q | grep -q .; then
        log "Starting local Docker Registry on port 5000..."
        docker service create \
            --name registry \
            --publish published=5000,target=5000 \
            registry:2
        log "Registry available at localhost:5000"
    else
        warn "Registry already running."
    fi

    # ── Print join tokens ─────────────────────────────────────────────────────
    echo ""
    echo "══════════════════════════════════════════════════════════════════════"
    echo "  🎉 Manager node ready!"
    echo ""
    echo "  Run this command on WORKER machines (Machine 2 & 3):"
    echo ""
    docker swarm join-token worker | grep "docker swarm join"
    echo ""
    echo "  Or run: bash scripts/setup-swarm.sh worker <TOKEN> ${LOCAL_IP}"
    echo "══════════════════════════════════════════════════════════════════════"
}


# =============================================================================
# WORKER SETUP
# =============================================================================
setup_worker() {
    JOIN_TOKEN="${2:-}"
    MANAGER_IP="${3:-}"

    [[ -z "${JOIN_TOKEN}" ]] && err "Usage: $0 worker <JOIN_TOKEN> <MANAGER_IP>"
    [[ -z "${MANAGER_IP}" ]] && err "Usage: $0 worker <JOIN_TOKEN> <MANAGER_IP>"

    log "Setting up Worker node (IP: ${LOCAL_IP})"
    docker info > /dev/null 2>&1 || err "Docker is not running."

    if docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active"; then
        warn "Already part of a Swarm. Skipping join."
    else
        log "Joining Swarm cluster at ${MANAGER_IP}..."
        docker swarm join --token "${JOIN_TOKEN}" "${MANAGER_IP}:2377"
        log "Joined Swarm!"
    fi

    # ── Configure insecure registry (to pull from local registry on port 5000) ─
    REGISTRY_IP="${MANAGER_IP}"
    DAEMON_JSON="/etc/docker/daemon.json"
    if ! grep -q "${REGISTRY_IP}:5000" "${DAEMON_JSON}" 2>/dev/null; then
        warn "Configuring Docker to trust local registry at ${REGISTRY_IP}:5000"
        echo "{\"insecure-registries\": [\"${REGISTRY_IP}:5000\"]}" \
            | sudo tee "${DAEMON_JSON}" > /dev/null
        sudo systemctl restart docker
        log "Docker restarted with insecure registry config."
    fi

    log "Worker node setup complete!"
}


# =============================================================================
# LABEL GPU WORKER
# =============================================================================
label_gpu() {
    HOSTNAME="${2:-}"
    [[ -z "${HOSTNAME}" ]] && err "Usage: $0 label-gpu <worker-hostname>"
    log "Labeling ${HOSTNAME} as GPU node..."
    docker node update --label-add gpu=true "${HOSTNAME}"
    log "Done. Node ${HOSTNAME} is now labeled gpu=true."
}


# =============================================================================
# VERIFY CLUSTER
# =============================================================================
verify_cluster() {
    log "─── Swarm Nodes ──────────────────────────────────────────────"
    docker node ls
    echo ""
    log "─── Running Services ─────────────────────────────────────────"
    docker service ls 2>/dev/null || warn "No stack deployed yet."
    echo ""
    log "─── Node Labels ──────────────────────────────────────────────"
    docker node ls -q | while read -r id; do
        echo "Node ${id}: $(docker node inspect "$id" --format '{{.Spec.Labels}}')"
    done
}


# =============================================================================
# BUILD & PUSH IMAGES
# =============================================================================
build_and_push() {
    REGISTRY="${2:-localhost:5000}"
    TAG="${3:-latest}"
    ROOT="$(cd "$(dirname "$0")/.." && pwd)"

    log "Building images → ${REGISTRY} (tag: ${TAG})"

    for svc in backend frontend hybrid-router burst-controller; do
        if [[ -d "${ROOT}/${svc}" ]]; then
            log "  Building ${svc}..."
            docker build -t "${REGISTRY}/${svc}:${TAG}" "${ROOT}/${svc}"
            docker push "${REGISTRY}/${svc}:${TAG}"
            log "  ✓ ${REGISTRY}/${svc}:${TAG}"
        else
            warn "  Directory ${ROOT}/${svc} not found, skipping"
        fi
    done

    log "All images pushed to ${REGISTRY}"
}


# =============================================================================
# DEPLOY STACK
# =============================================================================
deploy_stack() {
    REGISTRY="${2:-localhost:5000}"
    TAG="${3:-latest}"
    ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    ENV_FILE="${ROOT}/.env"

    [[ ! -f "${ENV_FILE}" ]] && err ".env file not found at ${ENV_FILE}. Copy .env.example and fill in values."

    log "Deploying ai-platform stack..."
    set -a; source "${ENV_FILE}"; set +a

    REGISTRY="${REGISTRY}" TAG="${TAG}" \
        docker stack deploy \
        --compose-file "${ROOT}/docker-compose.swarm.yml" \
        --with-registry-auth \
        ai-platform

    log "Stack deployed! Monitor with:"
    log "  docker service ls"
    log "  docker stack ps ai-platform"
}


# =============================================================================
# MAIN
# =============================================================================
case "${ROLE}" in
    manager)      setup_manager "$@" ;;
    worker)       setup_worker  "$@" ;;
    label-gpu)    label_gpu     "$@" ;;
    verify)       verify_cluster    ;;
    build)        build_and_push "$@" ;;
    deploy)       deploy_stack   "$@" ;;
    *)
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands:"
        echo "  manager               — Init Swarm Manager (run on Machine 1)"
        echo "  worker <token> <ip>   — Join as Worker (run on Machine 2 & 3)"
        echo "  label-gpu <hostname>  — Label a node as having a GPU"
        echo "  verify                — Show cluster status"
        echo "  build [registry] [tag]— Build and push all Docker images"
        echo "  deploy [registry] [tag]— Deploy the full stack"
        echo ""
        echo "Full setup example:"
        echo "  Machine 1: bash scripts/setup-swarm.sh manager"
        echo "  Machine 2: bash scripts/setup-swarm.sh worker SWMTKN-xxx 192.168.1.10"
        echo "  Machine 3: bash scripts/setup-swarm.sh worker SWMTKN-xxx 192.168.1.10"
        echo "  Machine 1: bash scripts/setup-swarm.sh label-gpu machine2-hostname"
        echo "  Machine 1: bash scripts/setup-swarm.sh label-gpu machine3-hostname"
        echo "  Machine 1: bash scripts/setup-swarm.sh build"
        echo "  Machine 1: bash scripts/setup-swarm.sh deploy"
        exit 1
        ;;
esac
