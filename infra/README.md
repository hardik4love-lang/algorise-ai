# Algorise AI - Infrastructure as Code

Terraform provisions the platform substrate; Kubernetes manifests in
`gitops/k8s` own the application workloads; Argo CD syncs those manifests
and Argo Rollouts performs the canary rollout.

## Layout

```
infra/
  main.tf                 # root module: composes the shared modules
  variables.tf
  modules/
    network/              # VPC, subnets, NAT, security groups
    kubernetes-cluster/   # EKS control plane + node pools
    postgres-ha/          # Multi-AZ PostgreSQL with PITR
    redis-ha/             # TLS Redis with replication
    object-storage/       # Versioned, encrypted artifact storage
    secrets-manager/      # Secrets Store + rotation
    container-registry/   # ECR mirror + retention
    ingress-waf/          # ALB + WAF + TLS
    dns-tls/              # Route53 records + ACME
    observability/        # CloudWatch, Prometheus, alerting
    iam-workload-identity/# GitHub OIDC federation
    backup-disaster-recovery/
  environments/
    dev/
    staging/
    production/
```

## Provisioning order

The modules have hard dependencies. Provision in this order:

```bash
# 1. State backend (one-time, outside Terraform)
aws s3api create-bucket --bucket algorise-ai-terraform-state --region ap-south-1
aws dynamodb create-table \
  --table-name algorise-ai-terraform-locks \
  --key-schema AttributeName=LockID,AttributeType=S \
  --billing-mode PAY_PER_REQUEST --region ap-south-1

# 2. Network substrate
terraform -chdir=infra/environments/production init
terraform -chdir=infra/environments/production apply -target=module.network

# 3. Data plane and platform services
terraform -chdir=infra/environments/production apply \
  -target=module.container_registry \
  -target=module.secrets_manager \
  -target=module.postgres_ha \
  -target=module.redis_ha

# 4. Kubernetes and GitOps
terraform -chdir=infra/environments/production apply \
  -target=module.kubernetes_cluster \
  -target=module.iam_workload_identity

# 5. Observability, ingress, backups
terraform -chdir=infra/environments/production apply
```

## Required secret values

Populate these in the secrets manager before the first production rollout.
The Kubernetes `ExternalSecret` in `gitops/k8s/secrets.yaml` maps them by
property name.

| Secret property | Purpose |
|---|---|
| `database_url` | `postgresql+asyncpg://...` with TLS required |
| `redis_url` | `rediss://...` with TLS required |
| `secret_key` | JWT signing key |
| `admin_secret` | Admin control panel key |
| `tenant_registry` | JSON tenant map for the DevEx gateway |
| `telegram_bot_token` | Telegram bot credential |
| `meta_app_secret` | Meta Graph API secret |
| `github_app_private_key` | GitHub App installation key |
| `github_webhook_secret` | GitHub webhook HMAC secret |
| `llm_api_key` | Model provider credential |

## Promotion flow

```text
push to master
  -> .github/workflows/ci.yml (tests, build check, release gates)
  -> .github/workflows/container.yml (build, SBOM, Trivy, smoke test)
  -> digest published to GHCR
  -> .github/workflows/promote.yml (reviewed PR pinning the digest)
  -> merge into the release tag
  -> Argo CD syncs gitops/k8s
  -> migration Job runs as PreSync
  -> Argo Rollouts canary 10/25/50/100 with analysis
  -> automatic rollback on analysis failure
```

## State safety

- Remote state in S3 with DynamoDB locking and encryption.
- No secret values stored in Terraform state; only secret ARNs.
- Production applies require a reviewed pull request against the
  environment repository.
- `prevent_destroy` is set on the production database and state bucket.
