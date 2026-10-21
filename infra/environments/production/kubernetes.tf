module "kubernetes_cluster" {
  source = "../../modules/kubernetes-cluster"

  environment        = var.environment
  region             = var.region
  cluster_name       = "algorise-ai-${var.environment}"
  kubernetes_version = "1.30"
  enable_irsa        = true
  node_instance_types = ["m6i.large", "c6i.xlarge"]
  min_node_count     = 3
  max_node_count     = 12
  enable_spot        = true
  enable_auto_upgrade = true
}

module "ingress_waf" {
  source = "../../modules/ingress-waf"

  environment        = var.environment
  region             = var.region
  domain             = "api.algorise.ai"
  certificate_arn    = var.certificate_arn
  enable_waf         = true
  rate_limit_per_minute = 1200
  target_port        = 80
}

module "dns_tls" {
  source = "../../modules/dns-tls"

  environment = var.environment
  region      = var.region
  domain      = "api.algorise.ai"
  zone_id     = var.hosted_zone_id
}
