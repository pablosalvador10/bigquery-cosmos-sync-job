---
description: "Deploy the application to Azure using azd and Terraform. Walks through provisioning, deployment, and verification."
---

# Deploy to Azure

Walk me through deploying this application to Azure.

## Steps

1. **Check prerequisites**:
   - Azure CLI signed in (`az account show`)
   - Azure Developer CLI (`azd version`)
   - Docker running

2. **Configure** — set up `.env.azure` and `infra/main.tfvars` with my Azure details.

3. **Provision infrastructure**:
   ```bash
   azd provision
   ```

4. **Deploy application**:
   ```bash
   azd deploy
   ```

5. **Verify**:
   - Backend health: `curl https://<backend-url>/healthz`
   - Frontend loads in browser
   - Chat works end-to-end

6. **Show me** the deployed URLs and any issues.

## If something fails
Tell me the exact error and the fix. Don't just say "check logs" — show me what to look for.
