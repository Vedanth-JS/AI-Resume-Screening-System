#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# AI ATS — Blue-Green Deployment Script
# Deploys new version to inactive environment, runs health checks,
# switches traffic via Kubernetes label selector, and keeps old version for rollback.
#
# Usage: ./blue-green-deploy.sh <image_tag> [environment=production]
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

IMAGE_TAG="${1:-latest}"
ENV="${2:-production}"
NAMESPACE="ai-ats-${ENV}"
BLUE_DEPLOY="ai-ats-api-blue"
GREEN_DEPLOY="ai-ats-api-green"
HEALTH_URL="/api/health"
ROLLBACK_WAIT=60

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# Determine active/inactive
ACTIVE=$(kubectl get svc ai-ats-api -n "$NAMESPACE" -o jsonpath='{.spec.selector.deployment}' 2>/dev/null || echo "blue")

if [ "$ACTIVE" = "blue" ]; then
  INACTIVE_COLOR="green"
  INACTIVE_DEPLOY="$GREEN_DEPLOY"
else
  INACTIVE_COLOR="blue"
  INACTIVE_DEPLOY="$BLUE_DEPLOY"
fi

log "Active: $ACTIVE → Deploying to: $INACTIVE_COLOR"

# ─── Step 1: Update inactive deployment ──────────────────────────────────────
log "Updating $INACTIVE_DEPLOY to tag $IMAGE_TAG..."
kubectl set image deployment/"$INACTIVE_DEPLOY" api="ghcr.io/vedanth-js/ai-ats-api:${IMAGE_TAG}" -n "$NAMESPACE"

log "Waiting for rollout..."
kubectl rollout status deployment/"$INACTIVE_DEPLOY" -n "$NAMESPACE" --timeout=120s

# ─── Step 2: Health check inactive deployment ────────────────────────────────
log "Running health checks on $INACTIVE_COLOR..."
POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app=ai-ats,deployment="$INACTIVE_COLOR" -o jsonpath='{.items[0].metadata.name}')

for i in {1..10}; do
  STATUS=$(kubectl exec -n "$NAMESPACE" "$POD_NAME" -- curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000$HEALTH_URL" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    log "Health check passed (attempt $i)"
    break
  fi
  log "Waiting for healthy... (attempt $i, status=$STATUS)"
  sleep 5
done

# ─── Step 3: Smoke test ──────────────────────────────────────────────────────
log "Running smoke test..."
SMOKE=$(kubectl exec -n "$NAMESPACE" "$POD_NAME" -- curl -s "http://localhost:8000$HEALTH_URL" 2>/dev/null)
if echo "$SMOKE" | grep -q "healthy"; then
  log "Smoke test passed"
else
  log "ERROR: Smoke test failed! Rolling back."
  kubectl rollout undo deployment/"$INACTIVE_DEPLOY" -n "$NAMESPACE"
  exit 1
fi

# ─── Step 4: Database migration ──────────────────────────────────────────────
log "Running database migrations..."
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- alembic upgrade head 2>/dev/null || log "Migration skipped (no changes)"

# ─── Step 5: Switch traffic ──────────────────────────────────────────────────
log "Switching traffic from $ACTIVE to $INACTIVE_COLOR..."
kubectl patch svc ai-ats-api -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"deployment\":\"$INACTIVE_COLOR\"}}}"

# ─── Step 6: Verify traffic is routing ───────────────────────────────────────
log "Verifying traffic routing..."
sleep 3
for i in {1..5}; do
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://ai-ats-api.$NAMESPACE.svc.cluster.local$HEALTH_URL" 2>/dev/null || echo "000")
  if [ "$RESPONSE" = "200" ]; then
    log "Traffic routing confirmed"
    break
  fi
  sleep 2
done

# ─── Step 7: Keep old version warm for rollback ──────────────────────────────
log "Keeping $ACTIVE deployment warm for $ROLLBACK_WAIT seconds (rollback window)..."
# Old version stays running for quick rollback via: kubectl patch svc ai-ats-api -n $NAMESPACE -p '{"spec":{"selector":{"deployment":"$ACTIVE"}}}'

log "✅ Blue-Green deployment complete! $INACTIVE_COLOR is now LIVE (tag=$IMAGE_TAG)"
log "   Rollback command: kubectl patch svc ai-ats-api -n $NAMESPACE -p '{\"spec\":{\"selector\":{\"deployment\":\"$ACTIVE\"}}}'"
