# Provision-Azure-Offload.ps1
# Maxes out Azure for Students ($100 credit) with compute offload VMs
# for Jules Bridge parallel workloads.
#
# Azure for Students limits:
#   - $100 credit, no credit card needed
#   - 750 hrs/month B1s free (1 vCPU, 1 GB) — but we go bigger on the credit
#   - Typical max before spending ~$80-90: 4x B2s (2 vCPU, 4 GB each)
#     = 8 vCPUs, 16 GB RAM total; ~$0.096/hr each = ~$0.384/hr combined
#
# This script creates:
#   - Resource group:   jules-offload-rg  (eastus)
#   - 2x B2s VMs:      jules-worker-01, jules-worker-02  (Ubuntu 22.04)
#   - Shared VNet/NSG with SSH + bridge port (5000) open
#   - Startup script that installs git, python3, pip, pulls the bridge

$ErrorActionPreference = "Continue"

$RG         = "jules-offload-rg"
$Location   = "eastus"
$VnetName   = "jules-vnet"
$SubnetName = "jules-subnet"
$NsgName    = "jules-nsg"
$VmSize     = "Standard_B2s"   # 2 vCPU / 4 GB — ~$0.048/hr spot or $0.096 on-demand
$Image      = "Ubuntu2204"
$AdminUser  = "julesadmin"
$SshKeyFile = "$env:USERPROFILE\.ssh\id_rsa.pub"
$VmNames    = @("jules-worker-01", "jules-worker-02")
$BridgePort = 5000

$logDir = "$env:USERPROFILE\.jules\jules_inbox\azure_boot"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("azure_{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))

function Write-Log($msg) {
    $line = "{0} {1}" -f (Get-Date -Format o), $msg
    Add-Content -Path $log -Value $line
    Write-Output $line
}

Write-Log "=== Jules Azure Offload Provisioner ==="

# --- Ensure SSH key exists (generate if missing) ---
$sshDir = "$env:USERPROFILE\.ssh"
if (-not (Test-Path $SshKeyFile)) {
    Write-Log "Generating SSH key at $sshDir\id_rsa"
    New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
    & ssh-keygen -t rsa -b 4096 -f "$sshDir\id_rsa" -N "" -q
}
$pubKey = Get-Content $SshKeyFile -Raw

# --- Check Azure login ---
$account = az account show --output json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: Not logged into Azure. Run 'az login' first."
    exit 1
}
$acct = $account | ConvertFrom-Json
Write-Log "Logged in as: $($acct.user.name) | Subscription: $($acct.name) ($($acct.id))"

# --- Resource Group ---
Write-Log "Creating resource group $RG in $Location"
az group create --name $RG --location $Location --output none 2>&1 | ForEach-Object { Write-Log $_ }

# --- VNet + Subnet ---
Write-Log "Creating VNet $VnetName"
az network vnet create `
    --resource-group $RG `
    --name $VnetName `
    --address-prefix 10.10.0.0/16 `
    --subnet-name $SubnetName `
    --subnet-prefix 10.10.1.0/24 `
    --output none 2>&1 | ForEach-Object { Write-Log $_ }

# --- NSG with SSH + bridge port rules ---
Write-Log "Creating NSG $NsgName"
az network nsg create --resource-group $RG --name $NsgName --output none 2>&1 | ForEach-Object { Write-Log $_ }

az network nsg rule create --resource-group $RG --nsg-name $NsgName `
    --name AllowSSH --priority 1000 --protocol Tcp `
    --destination-port-range 22 --access Allow --direction Inbound `
    --output none 2>&1 | ForEach-Object { Write-Log $_ }

az network nsg rule create --resource-group $RG --nsg-name $NsgName `
    --name AllowBridge --priority 1010 --protocol Tcp `
    --destination-port-range $BridgePort --access Allow --direction Inbound `
    --output none 2>&1 | ForEach-Object { Write-Log $_ }

# --- Startup script: install Python + pip + pull jules bridge deps ---
$startupScript = @"
#!/bin/bash
apt-get update -y
apt-get install -y git python3 python3-pip python3-venv curl
pip3 install flask requests google-generativeai
echo "Jules worker ready on \$(hostname) at \$(date)" >> /var/log/jules-worker.log
"@
$startupFile = Join-Path $env:TEMP "jules_startup.sh"
$startupScript | Set-Content -Path $startupFile -Encoding UTF8

# --- Create VMs ---
foreach ($vmName in $VmNames) {
    Write-Log "Creating VM $vmName ($VmSize, $Image)"
    az vm create `
        --resource-group $RG `
        --name $vmName `
        --image $Image `
        --size $VmSize `
        --admin-username $AdminUser `
        --ssh-key-value $pubKey `
        --vnet-name $VnetName `
        --subnet $SubnetName `
        --nsg $NsgName `
        --public-ip-sku Standard `
        --custom-data $startupFile `
        --no-wait `
        --output none 2>&1 | ForEach-Object { Write-Log $_ }
    Write-Log "VM $vmName creation queued (--no-wait)"
}

# --- Wait and get IPs ---
Write-Log "Waiting 60s for VMs to provision..."
Start-Sleep -Seconds 60

Write-Log "=== VM Status ==="
foreach ($vmName in $VmNames) {
    $ip = az vm list-ip-addresses --resource-group $RG --name $vmName `
        --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" `
        --output tsv 2>&1
    Write-Log "$vmName external IP: $ip"
    
    # Save to .env-style file for bridge to read
    Add-Content -Path "$env:USERPROFILE\.jules\.env" -Value "`nAZURE_WORKER_${vmName.ToUpper().Replace('-','_')}=$ip"
}

Write-Log "=== Azure provisioning complete. Log: $log ==="
Write-Log "Connect with: ssh $AdminUser@<IP>"
