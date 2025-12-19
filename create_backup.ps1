# MAX Project Backup Script
# Creates verified backup with integrity check

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupName = "MAX_BACKUP_$timestamp.zip"
$backupPath = Join-Path ".." $backupName

Write-Host "[*] Creating backup: $backupName"
Write-Host "[*] This may take a few minutes..."

try {
    # Create backup
    Compress-Archive -Path "." -DestinationPath $backupPath -CompressionLevel Optimal -Force
    
    if (Test-Path $backupPath) {
        $backupFile = Get-Item $backupPath
        $sizeMB = [math]::Round($backupFile.Length / 1MB, 2)
        
        Write-Host "[+] Backup created successfully!"
        Write-Host "[+] Location: $backupPath"
        Write-Host "[+] Size: $sizeMB MB"
        Write-Host "[+] Created: $($backupFile.CreationTime)"
        
        # Verify backup
        Write-Host ""
        Write-Host "[?] Verifying backup integrity..."
        python verify_backup.py $backupPath
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[+] Backup verification PASSED"
            exit 0
        } else {
            Write-Host "[X] Backup verification FAILED"
            exit 1
        }
    } else {
        Write-Host "[X] Backup file was not created"
        exit 1
    }
} catch {
    Write-Host "[X] Error creating backup: $_"
    exit 1
}
