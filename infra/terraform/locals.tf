locals {
  common_tags = {
    project     = "TradeJournal"
    environment = var.environment
    managed_by  = "Terraform"
    week        = "Week1"
    cost-centre = "tradejournal"
    owner       = "tradejournal"
  }
}