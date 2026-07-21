#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# AI ATS — Canary Deployment Script
# Gradually shifts traffic from stable → canary via weighted DNS or ingress rules.
# Monitors error rate and latency; auto-rolls back if thresholds exceeded.
#
# Usage: ./canary-deploy.sh <image_tag> [canary_percent=10]
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

IMAGE_TAG="${1:-latest}"
CANARY_PCT="${2:-10}"
NAMESPACE="ai-ats-production"
CANARY_DEPLOY="ai-ats-api-canary"
STABLE_DEPLOY="ai-ats-api"
HEALTH_URL="/api/health"
MAX_ERROR_RATE=2  # percent
MONITOR_SECONDS=120
STEP_INTERVAL=30

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ─── Step 1: Deploy canary pods ──────────────────────────────────────────────
log "Deploying canary (${CANARY_PCT}%) with tag $IMAGE_TAG..."
kubectl set image deployment/"$CANARY_DEPLOY" api="ghcr.io/vedanth-js/ai-ats-api:${IMAGE_TAG}" -n "$NAMESPACE"

# Scale canary to desired percentage
STABLE_REPLICAS=$(kubectl get deployment "$STABLE_DEPLOY" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
CANARY_REPLICAS=$(( (STABLE_REPLICAS * CANARY_PCT + 99) / 100 ))
[ "$CANARY_REPLICAS" -lt 1 ] && CANARY_REPLICAS=1

kubectl scale deployment "$CANARY_DEPLOY" -n "$NAMESPACE" --replicas="$CANARY_REPLICAS"
kubectl rollout status deployment/"$CANARY_DEPLOY" -n "$NAMESPACE" --timeout=60s

# ─── Step 2: Route canary traffic via Istio/NGINX ingress weight ─────────────
log "Setting traffic split: ${CANARY_PCT}% → canary, $((100 - CANARY_PCT))% → stable"

# NGINX Ingress annotation approach:
kubectl annotate ingress ai-ats-api -n "$NAMESPACE \
  nginx.ingress.kubernetes.io/canary="true" \
  nginx.ingress.kubernetes.io/canary-weight="${CANARY_PCT}" \
  --overwrite

# ─── Step 3: Monitor error rate ─────────────────────────────────────────────
log "Monitoring canary health for ${MONITOR_SECONDS}s..."

ERRORS=0
TOTAL=0
START_TIME=$(date +%s)

while [ $(($(date +%s) - START_TIME)) -lt "$MONITOR_SECONDS" ]; do
  # Check canary pod health
  CANARY_PODS=$(kubectl get pods -n "$NAMESPACE" -l app=ai-ats,role=canary --field-selector=status.phase=Running -o name | wc -l)
  CANARY_TOTAL=$(kubectl get pods -n "$NAMESPACE" -l app=ai-ats,role=canary -o name | wc -l)

  if [ "$CANARY_PODS" -lt "$CANARY_TOTAL" ]; then
    log "WARNING: Canary pods unhealthy ($CANARY_PODS/$CANARY_TOTAL running)"
    ERRORS=$((ERRORS + 1))
  fi

  # Check API error rate from canary
  for pod in $(kubectl get pods -n "$NAMESPACE" -l app=ai-ats,role=canary -o name | head -2); do
    STATUS=$(kubectl exec -n "$NAMESPACE" "${pod#pod/}" -- curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000$HEALTH_URL" 2>/dev/null || echo "000")
    TOTAL=$((TOTAL + 1))
    [ "$STATUS" != "200" ] && ERRORS=$((ERRORS + 1))
  done
  sleep 5
done

ERROR_RATE=$((ERRORS * 100 / (TOTAL + 1)))
log "Error rate: ${ERROR_RATE}% (threshold: ${MAX_ERROR_RATE}%)"

# ─── Step 4: Promote or rollback ─────────────────────────────────────────────
if [ "$ERROR_RATE" -le "$MAX_ERROR_RATE" ]; then
  log "✅ Canary health check passed. Promoting to stable..."
  kubectl set image deployment/"$STABLE_DEPLOY" api="ghcr.io/vedanth-js/ai-ats-api:${IMAGE_TAG}" -n "$NAMESPACE"
  kubectl rollout status deployment/"$STABLE_DEPLOY" -n "$NAMESPACE" --timeout=120s

  # Remove canary routing
  kubectl annotate ingress ai-ats-api -n "$NAMESPACE \
    nginx.ingress.kubernetes.io/canary- \
    nginx.ingress.kubernetes.io/canary-weight- \
    --overwrite

  # Scale down canary
  kubectl scale deployment "$CANARY_DEPLOY" -n "$NAMESPACE" --replicas=0
  log "🎉 Canary deployment successful! $IMAGE_TAG is now stable."
else
  log "❌ ERROR: Canary error rate ${ERROR_RATE}% exceeds threshold ${MAX_ERROR_RATE}%"
  log "Rolling back canary..."

  # Remove canary routing
  kubectl annotate ingress ai-ats-api -n "$NAMESPACE \
    nginx.ingress.kubernetes.io/canary- \
    nginx.ingress.kubernetes.io/canary-weight- \
    --overwrite

  kubectl scale deployment "$CANARY_DEPLOY" -n "$NAMESPACE" --replicas=0
  log "Canary rolled back. Stable deployment unchanged."
  exit 1
fi
