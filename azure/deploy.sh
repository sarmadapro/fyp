#!/bin/bash
# ── VoiceRAG — Azure Container Apps Deployment ─────────────────────────────
#
# Prerequisites:
#   - Azure CLI installed & logged in  (az login)
#   - Docker installed & running
#   - A resource group created
#
# Usage:
#   chmod +x azure/deploy.sh
#   ./azure/deploy.sh
#
# All variables below can be overridden via environment:
#   RESOURCE_GROUP=my-rg ./azure/deploy.sh

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
RESOURCE_GROUP="${RESOURCE_GROUP:-voicerag-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-voiceragacr}"           # must be globally unique
ENVIRONMENT="${ENVIRONMENT:-voicerag-env}"
APP_NAME="${APP_NAME:-voicerag-backend}"

echo "=== VoiceRAG Azure Deployment ==="
echo "Resource Group : $RESOURCE_GROUP"
echo "Location       : $LOCATION"
echo "ACR            : $ACR_NAME"
echo ""

# ── 1. Create resource group ─────────────────────────────────────────────────
echo "[1/7] Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# ── 2. Create Azure Container Registry ──────────────────────────────────────
echo "[2/7] Creating Azure Container Registry..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --output none

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"

# ── 3. Build & push images ───────────────────────────────────────────────────
echo "[3/7] Building and pushing images to ACR..."

az acr login --name "$ACR_NAME"

# Backend
docker build -t "$ACR_LOGIN_SERVER/voicerag-backend:latest" ./backend
docker push "$ACR_LOGIN_SERVER/voicerag-backend:latest"

# STT
docker build -t "$ACR_LOGIN_SERVER/voicerag-stt:latest" ./services/stt
docker push "$ACR_LOGIN_SERVER/voicerag-stt:latest"

# TTS
docker build -t "$ACR_LOGIN_SERVER/voicerag-tts:latest" ./services/tts
docker push "$ACR_LOGIN_SERVER/voicerag-tts:latest"

# Frontend
docker build -t "$ACR_LOGIN_SERVER/voicerag-frontend:latest" ./frontend
docker push "$ACR_LOGIN_SERVER/voicerag-frontend:latest"

# ── 4. Create Container Apps Environment ────────────────────────────────────
echo "[4/7] Creating Container Apps environment..."
az containerapp env create \
  --name "$ENVIRONMENT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# ── 5. Deploy backend ────────────────────────────────────────────────────────
echo "[5/7] Deploying backend container app..."
ACR_PASS=$(az acr credential show --name "$ACR_NAME" --query passwords[0].value -o tsv)

az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT" \
  --image "$ACR_LOGIN_SERVER/voicerag-backend:latest" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASS" \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1 \
  --memory 2Gi \
  --env-vars \
    "DATABASE_URL=${DATABASE_URL:-}" \
    "JWT_SECRET_KEY=${JWT_SECRET_KEY:-change-in-production}" \
    "GROQ_API_KEY=${GROQ_API_KEY:-}" \
    "STT_SERVICE_URL=http://voicerag-stt" \
    "TTS_SERVICE_URL=http://voicerag-tts" \
    "CORS_ORIGINS=${CORS_ORIGINS:-*}" \
  --output none

BACKEND_URL=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Backend deployed at: https://$BACKEND_URL"

# ── 6. Deploy STT & TTS (internal) ──────────────────────────────────────────
echo "[6/7] Deploying STT service..."
az containerapp create \
  --name "voicerag-stt" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT" \
  --image "$ACR_LOGIN_SERVER/voicerag-stt:latest" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASS" \
  --target-port 8001 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 2 \
  --cpu 2 \
  --memory 4Gi \
  --output none

az containerapp create \
  --name "voicerag-tts" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT" \
  --image "$ACR_LOGIN_SERVER/voicerag-tts:latest" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASS" \
  --target-port 8002 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 2 \
  --cpu 1 \
  --memory 2Gi \
  --output none

# ── 7. Deploy frontend ───────────────────────────────────────────────────────
echo "[7/7] Deploying frontend..."
az containerapp create \
  --name "voicerag-frontend" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT" \
  --image "$ACR_LOGIN_SERVER/voicerag-frontend:latest" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASS" \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.25 \
  --memory 0.5Gi \
  --output none

FRONTEND_URL=$(az containerapp show \
  --name "voicerag-frontend" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "=== Deployment Complete ==="
echo "Backend  : https://$BACKEND_URL"
echo "Frontend : https://$FRONTEND_URL"
echo ""
echo "Next steps:"
echo "  1. Set DATABASE_URL to your Azure PostgreSQL connection string"
echo "  2. Update CORS_ORIGINS to the frontend URL"
echo "  3. Set JWT_SECRET_KEY to a strong random value"
echo "  4. Configure SMTP settings for email verification"
