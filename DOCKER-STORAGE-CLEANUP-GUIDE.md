# Docker Storage Problem & Cleanup Guide

## Problem Overview

### What is Docker Storage Problem?

Docker Desktop on Windows uses Virtual Hard Disks (VHD) files to store container data, images, and build caches. These VHD files have a critical limitation: **they never automatically shrink**, even when you delete containers and images.

### Why Does This Happen?

1. **VHD Files Never Shrink Automatically**
   - Docker uses WSL2 (Windows Subsystem for Linux 2) with VHDX files
   - When data is deleted inside the VHD, the space remains allocated to Windows
   - Only explicit export/import operations compact and return space to Windows

2. **Build Cache Accumulation**
   - Docker layer caching stores intermediate build results
   - Over time, build cache can grow 3-12GB between cleanups
   - `docker builder prune` only clears Docker internals, not Windows disk space

3. **Unused Images and Containers**
   - Images and stopped containers accumulate and consume space
   - Kubernetes images alone can take 600MB-900MB when enabled
   - Without cleanup, VHD can grow from 0.14GB to 25-30GB in hours/days

4. **Volumes**
   - Named volumes and mount data persist after containers are deleted
   - Can accumulate hundreds of MB over time

### Symptoms

- ❌ C: or D: drive rapidly fills up (loss of 25-30GB in hours/days)
- ❌ `docker system df` shows high disk usage but `docker prune` doesn't free Windows space
- ❌ VHD files (`docker_data.vhdx`, `ext4.vhdx`) keep growing
- ❌ Even with 0 images/containers, VHD doesn't shrink
- ❌ Docker Desktop reports space but Windows shows it as used

---

## Docker Storage Cleanup Flow

### Step 1: Clean Docker Cache & Containers

```powershell
# Remove stopped containers
docker container prune -f

# Remove dangling images (untagged)
docker image prune -f

# Remove ALL unused images (even tagged ones)
docker image prune -a -f

# Remove build cache
docker builder prune -a -f

# Remove unused volumes
docker volume prune -a -f

# Verify what's left
docker system df
```

**Expected:** Significant space freed inside Docker (100MB - 5GB depending on usage)

---

### Step 2: Stop Docker Desktop

```powershell
# Force stop Docker Desktop
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue

# Wait 3 seconds
Start-Sleep -Seconds 3

# Shutdown WSL completely
wsl --shutdown
```

---

### Step 3: Export the Distribution (Compact VHD)

This is the KEY step that actually compacts the VHD and returns space to Windows.

```powershell
# Export docker-desktop (this may take 3-10 minutes)
wsl --export docker-desktop "D:\docker-desktop-backup.tar"
```

**Result:** Creates a TAR backup that only contains used space (much smaller than VHD)

---

### Step 4: Unregister and Delete VHD

```powershell
# Unregister the distribution
wsl --unregister docker-desktop
```

Then open admin PowerShell to delete locked VHD files:

```powershell
# Run as Administrator
Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-Command", `
  "Stop-Process -Name vmmemWSL, wslservice -Force -ErrorAction SilentlyContinue; " + `
  "Remove-Item 'D:\Docker\wsl\DockerDesktopWSL\*.vhdx' -Force; " + `
  "Write-Host 'VHD files deleted. Close this window.'"
```

**Why admin?** The VHD files are locked by Docker Desktop processes and require elevated privileges to delete.

---

### Step 5: Re-import the Distribution

```powershell
# Re-import from the TAR backup (smaller, compacted)
wsl --import docker-desktop "D:\Docker\wsl\DockerDesktopWSL" `
  "D:\docker-desktop-backup.tar" --version 2
```

**Result:** Recreates the distribution with only used space (much smaller VHD)

---

### Step 6: Cleanup and Restart

```powershell
# Delete the backup TAR (no longer needed)
Remove-Item "D:\docker-desktop-backup.tar" -Force

# Start Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait for it to start
Start-Sleep -Seconds 20

# Verify the new smaller VHD
Get-ChildItem "D:\Docker\wsl\DockerDesktopWSL" -Recurse -File |
  Where-Object {$_.Name -like "*.vhdx"} |
  Select-Object Name, @{Name="Size GB";Expression={[math]::Round($_.Length/1GB, 2)}}

# Check D: drive space
Get-PSDrive D | Select-Object `
  @{Name="Used GB";Expression={[math]::Round($_.Used/1GB, 2)}}, `
  @{Name="Free GB";Expression={[math]::Round($_.Free/1GB, 2)}}
```

---

## Additional Cleanup: Disable Kubernetes (Optional)

If you're not using Kubernetes, it adds 600MB+ of images that can be removed:

### Option A: Disable via Docker Desktop UI

1. Open Docker Desktop
2. Go to **Settings** ⚙️
3. Navigate to **Kubernetes**
4. Uncheck **"Enable Kubernetes"**
5. Click **Apply & Restart**

### Option B: Disable via Settings File

```powershell
# Stop Docker
Stop-Process -Name "Docker Desktop" -Force

# Edit settings file
$file = "$env:APPDATA\Docker\settings-store.json"
(Get-Content $file -Raw) `
  -replace '"kubernetesEnabled":\s*true', '"kubernetesEnabled":false' | `
  Set-Content $file

# Restart Docker
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

### Delete Kubernetes Images

```powershell
# After Docker starts, remove K8s images
docker images -q | ForEach-Object { docker rmi -f $_ }

# Verify
docker images
docker system df
```

---

## Complete Cleanup Script

Save as `docker-cleanup.ps1` for quick re-use:

```powershell
# ===== Docker Storage Cleanup Script =====
Write-Host "Step 1: Cleaning Docker cache..." -ForegroundColor Green
docker container prune -f
docker image prune -a -f
docker builder prune -a -f
docker volume prune -a -f

Write-Host "`nStep 2: Stopping Docker..." -ForegroundColor Green
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
wsl --shutdown

Write-Host "`nStep 3: Exporting distribution..." -ForegroundColor Green
wsl --export docker-desktop "D:\docker-desktop-backup.tar"

Write-Host "`nStep 4: Unregistering..." -ForegroundColor Green
wsl --unregister docker-desktop

Write-Host "`nStep 5: Deleting VHD (opening admin window)..." -ForegroundColor Green
Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-Command", `
  "Stop-Process -Name vmmemWSL, wslservice -Force -ErrorAction SilentlyContinue; " + `
  "Remove-Item 'D:\Docker\wsl\DockerDesktopWSL\*.vhdx' -Force; " + `
  "Write-Host 'VHD deleted. Close this window.'"

Read-Host "`nPress Enter after closing admin window"

Write-Host "`nStep 6: Re-importing..." -ForegroundColor Green
wsl --import docker-desktop "D:\Docker\wsl\DockerDesktopWSL" `
  "D:\docker-desktop-backup.tar" --version 2

Remove-Item "D:\docker-desktop-backup.tar" -Force
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Start-Sleep -Seconds 20

Write-Host "`n✅ Cleanup Complete!`n" -ForegroundColor Green
Write-Host "--- VHD Size ---"
Get-ChildItem "D:\Docker\wsl\DockerDesktopWSL" -Recurse -File |
  Where-Object {$_.Name -like "*.vhdx"} |
  Select-Object Name, @{Name="Size GB";Expression={[math]::Round($_.Length/1GB, 2)}}

Write-Host "`n--- D: Drive Space ---"
Get-PSDrive D | Select-Object `
  @{Name="Used GB";Expression={[math]::Round($_.Used/1GB, 2)}}, `
  @{Name="Free GB";Expression={[math]::Round($_.Free/1GB, 2)}}
```

Run it with:

```powershell
.\docker-cleanup.ps1
```

---

## Key Takeaways

| Problem                       | Solution                                                   |
| ----------------------------- | ---------------------------------------------------------- |
| VHD won't shrink              | Export/Import the distribution                             |
| Build cache grows             | Run `docker builder prune -a -f` regularly                 |
| Old images remain             | Run `docker image prune -a -f`                             |
| Kubernetes overhead           | Disable if not needed                                      |
| Containers consume space      | Remove stopped containers with `docker container prune -f` |
| Space not returned to Windows | Only export/import actually returns space to OS            |

---

## Prevention Tips

1. **Schedule Regular Cleanup**
   - Run cleanup weekly during light usage periods
   - Each cycle takes 10-15 minutes

2. **Limit Docker Data Directory Size**
   - Consider setting max size limits in Docker settings
   - Prevents unlimited VHD growth

3. **Use Docker Compose Cleanup**
   - `docker-compose down -v` removes containers AND volumes
   - Prevents volume accumulation

4. **Monitor Disk Usage**
   - Regularly run `docker system df`
   - Watch VHD size with PowerShell script above

5. **Keep Docker Updated**
   - Newer versions have better disk management
   - Check Docker Desktop for updates monthly

---

## Troubleshooting

**Q: "VHD still locked after shutdown"**

- A: Run the admin PowerShell script to kill `vmmemWSL` and `wslservice` processes

**Q: "wsl --import fails with 'already exists'"**

- A: Run `wsl --unregister docker-desktop` again, then import

**Q: "Docker won't start after import"**

- A: Check if vmmemWSL process is running: `Get-Process vmmemWSL`
- Restart computer if necessary

**Q: "How much space will I save?"**

- A: Typically 40-90% of VHD size, depending on images/containers
- Example: 28GB VHD → 0.14GB after cleanup = **27.86GB freed**

---

## References

- [Docker System Prune Documentation](https://docs.docker.com/config/pruning/)
- [Windows Subsystem for Linux 2 (WSL2)](https://docs.microsoft.com/en-us/windows/wsl/)
- [Docker Desktop Settings](https://docs.docker.com/desktop/settings/windows/)
