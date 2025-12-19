"""
Backup Verification Script for MAX Project
Validates backup integrity by checking file count and size.
"""
import zipfile
import json
from pathlib import Path
from datetime import datetime
import hashlib


def verify_backup(backup_path: Path) -> dict:
    """
    Verify backup archive integrity.
    
    Returns:
        dict: Verification results with status and details
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "backup_file": str(backup_path),
        "status": "unknown",
        "checks": {}
    }
    
    # Check 1: File exists
    if not backup_path.exists():
        results["status"] = "FAILED"
        results["error"] = "Backup file not found"
        return results
    
    results["checks"]["file_exists"] = True
    results["backup_size_mb"] = round(backup_path.stat().st_size / 1024 / 1024, 2)
    
    # Check 2: Valid ZIP
    try:
        with zipfile.ZipFile(backup_path, 'r') as zip_ref:
            # Test ZIP integrity
            test_result = zip_ref.testzip()
            if test_result is not None:
                results["status"] = "FAILED"
                results["error"] = f"Corrupted file in archive: {test_result}"
                return results
            
            results["checks"]["zip_valid"] = True
            
            # Count files
            file_list = zip_ref.namelist()
            results["file_count"] = len(file_list)
            results["checks"]["has_files"] = len(file_list) > 0
            
            # Check for critical files
            critical_files = [
                "src/api/app.py",
                "src/core/memory.py",
                "data/soul.json",
                "MASTER_PLAN.md"
            ]
            
            missing_critical = []
            for critical in critical_files:
                # ZIP uses forward slashes
                zip_path = critical.replace("\\", "/")
                if not any(zip_path in f for f in file_list):
                    missing_critical.append(critical)
            
            if missing_critical:
                results["checks"]["critical_files"] = False
                results["missing_critical"] = missing_critical
            else:
                results["checks"]["critical_files"] = True
        
        # All checks passed
        if all(results["checks"].values()):
            results["status"] = "SUCCESS"
        else:
            results["status"] = "WARNING"
    
    except zipfile.BadZipFile:
        results["status"] = "FAILED"
        results["error"] = "Invalid ZIP file"
    except Exception as e:
        results["status"] = "FAILED"
        results["error"] = str(e)
    
    return results


def save_verification_log(results: dict, log_path: Path):
    """Save verification results to JSON log."""
    log_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )


def print_results(results: dict):
    """Print verification results in readable format."""
    print("\n" + "="*60)
    print("BACKUP VERIFICATION RESULTS")
    print("="*60)
    print(f"Backup File: {results['backup_file']}")
    print(f"Status: {results['status']}")
    print(f"Size: {results.get('backup_size_mb', 0)} MB")
    print(f"Files: {results.get('file_count', 0)}")
    
    print("\nChecks:")
    for check, passed in results.get('checks', {}).items():
        status = "[+]" if passed else "[X]"
        print(f"  {status} {check}")
    
    if "error" in results:
        print(f"\nError: {results['error']}")
    
    if "missing_critical" in results:
        print(f"\nMissing critical files:")
        for f in results['missing_critical']:
            print(f"  - {f}")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python verify_backup.py <backup_file.zip>")
        sys.exit(1)
    
    backup_file = Path(sys.argv[1])
    results = verify_backup(backup_file)
    
    print_results(results)
    
    # Save log
    log_file = backup_file.with_suffix('.verification.json')
    save_verification_log(results, log_file)
    print(f"Verification log saved: {log_file}")
    
    # Exit code
    sys.exit(0 if results["status"] == "SUCCESS" else 1)
