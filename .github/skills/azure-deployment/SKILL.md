---
name: azure-deployment
description: 'Deploys the application to Azure using azd and Terraform. Use when deploying, provisioning cloud resources, running azd provision, azd deploy, or setting up Azure infrastructure.'
argument-hint: 'Specify target environment or any custom Terraform variables'
---

## Purpose
Exact step-by-step commands for deploying the full stack to Azure using `azd` + Terraform.

## When to Use
- First-time deployment to Azure.
- Redeploying after code changes.
- Provisioning infrastructure with Terraform.

## Prerequisites
- Azure CLI installed and signed in: `az login`
- Azure Developer CLI installed: `azd auth login`
- Docker installed (for container image builds)

## Flow

1. **Configure environment**:
   ```bash
   cp .env.azure.example .env.azure
   # Edit .env.azure with your values:
   # - AZURE_FOUNDRY_PROJECT_ENDPOINT
   # - AZURE_CLIENT_ID (managed identity)
   # - APPLICATIONINSIGHTS_CONNECTION_STRING
   ```

2. **Set Terraform variables**:
   ```bash
   cp infra/main.tfvars.example infra/main.tfvars
   # Edit infra/main.tfvars:
   # - subscription_id
   # - environment_name (default: dev)
   # - location (default: eastus)
   # - enable_cosmos_db (default: true)
   # - backend_image, frontend_image (container registry URIs)
   ```

3. **Provision infrastructure**:
   ```bash
   azd provision
   ```
   This runs Terraform to create: Resource Group, Managed Identity, ACR, Container App Environment, backend + frontend Container Apps, and optionally Cosmos DB and Key Vault.
   Post-provision script (`infra/scripts/postprovision.sh`) runs automatically.

4. **Deploy application**:
   ```bash
   azd deploy
   ```
   Builds and deploys backend + frontend container images to Container Apps.

5. **Verify deployment**:
   ```bash
   # Check backend health
   curl https://<backend-url>/healthz

   # Check frontend loads
   open https://<frontend-url>

   # URLs are in Terraform outputs:
   cd infra && terraform output
   ```

6. **Update existing deployment**:
   ```bash
   # After code changes:
   azd deploy

   # After infra changes:
   azd provision
   ```

## Troubleshooting
- **Auth error**: Run `az login` and `azd auth login` again.
- **Terraform state**: Check `infra/backend.tf` for state backend config.
- **Container build fails**: Verify Dockerfiles in `py/apps/app-template/` and `ts/apps/ui-copilot-template/`.
- **Cosmos connection**: Verify managed identity has `Cosmos DB Data Contributor` role.

## Checklist
- [ ] `.env.azure` configured with real values
- [ ] `infra/main.tfvars` set with subscription + region
- [ ] `azd provision` succeeds
- [ ] `azd deploy` succeeds
- [ ] Backend `/healthz` returns `{"status": "ok"}`
- [ ] Frontend loads in browser
- [ ] Cosmos DB accessible from backend
