module "postgres_ha" {
  source = "../../modules/postgres-ha"

  environment           = var.environment
  region                = var.region
  availability_zones    = var.availability_zones
  engine_version        = "15.7"
  instance_class        = "db.r6g.xlarge"
  allocated_storage_gb  = 500
  max_allocated_storage_gb = 2000
  database_name         = "algorise"
  master_username       = "algorise_admin"
  backup_retention_days = 30
  deletion_protection   = true
  skip_final_snapshot   = false
  multi_az              = true
  performance_insights_enabled = true
  tags = {
    Application = "algorise-ai"
  }
}

module "redis_ha" {
  source = "../../modules/redis-ha"

  environment        = var.environment
  region             = var.region
  node_type          = "cache.r7g.large"
  num_cache_clusters = 2
  replicas_per_node  = 2
  engine_version     = "7.1"
  at_rest_encryption_enabled = true
  transit_encryption_enabled  = true
  auth_token_enabled          = true
  multi_az_enabled            = true
  snapshot_retention_limit    = 7
}

module "object_storage" {
  source = "../../modules/object-storage"

  environment            = var.environment
  region                 = var.region
  bucket_name            = "algorise-ai-artifacts-${var.environment}"
  versioning_enabled     = true
  lifecycle_enabled      = true
  block_public_access    = true
  server_side_encryption = "aws:kms"
}
