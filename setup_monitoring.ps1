$ErrorActionPreference = "Stop"

Write-Host "Downloading Prometheus..."
Invoke-WebRequest -Uri "https://github.com/prometheus/prometheus/releases/download/v2.53.1/prometheus-2.53.1.windows-amd64.zip" -OutFile "prometheus.zip"
Write-Host "Extracting Prometheus..."
Expand-Archive -Path "prometheus.zip" -DestinationPath "prometheus_bin" -Force

Write-Host "Downloading Grafana..."
Invoke-WebRequest -Uri "https://dl.grafana.com/oss/release/grafana-11.1.0.windows-amd64.zip" -OutFile "grafana.zip"
Write-Host "Extracting Grafana..."
Expand-Archive -Path "grafana.zip" -DestinationPath "grafana_bin" -Force

Write-Host "Done downloading binaries. You can start them now."
