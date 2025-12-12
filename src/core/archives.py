"""
Archive Manager for ZIP and RAR files.

Features:
- Extract ZIP/RAR archives
- Create ZIP archives
- List archive contents without extraction
"""
import zipfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

try:
    import rarfile
    HAS_RARFILE = True
except ImportError:
    HAS_RARFILE = False


@dataclass
class ArchiveEntry:
    """Entry in an archive."""
    name: str
    size: int
    compressed_size: int
    is_dir: bool


class ArchiveManager:
    """
    Manages ZIP and RAR archives.
    
    RAR support requires:
    - rarfile package
    - UnRAR.exe in PATH or set via rarfile.UNRAR_TOOL
    """
    
    def __init__(self):
        if HAS_RARFILE:
            # Try to find UnRAR
            import shutil
            unrar = shutil.which("UnRAR") or shutil.which("unrar")
            if unrar:
                rarfile.UNRAR_TOOL = unrar
    
    def _is_safe_path(self, dest: Path, member_path: str) -> bool:
        """
        Check if extracted path stays within destination.
        
        Prevents path traversal attacks like ../../etc/passwd.
        
        Args:
            dest: Destination directory
            member_path: Path from archive member
            
        Returns:
            True if path is safe, False if it escapes destination
        """
        try:
            target = (dest / member_path).resolve()
            dest_resolved = dest.resolve()
            return target.is_relative_to(dest_resolved)
        except (ValueError, RuntimeError):
            return False
    
    def is_supported(self, archive_path: str) -> bool:
        """Check if archive format is supported."""
        path = Path(archive_path)
        suffix = path.suffix.lower()
        
        if suffix == ".zip":
            return True
        if suffix == ".rar":
            return HAS_RARFILE
        return False
    
    def list_contents(self, archive_path: str) -> list[ArchiveEntry]:
        """
        List contents of an archive without extracting.
        
        Args:
            archive_path: Path to archive file
            
        Returns:
            List of archive entries
        """
        path = Path(archive_path)
        suffix = path.suffix.lower()
        
        entries = []
        
        if suffix == ".zip":
            with zipfile.ZipFile(path, 'r') as zf:
                for info in zf.infolist():
                    entries.append(ArchiveEntry(
                        name=info.filename,
                        size=info.file_size,
                        compressed_size=info.compress_size,
                        is_dir=info.is_dir()
                    ))
        
        elif suffix == ".rar" and HAS_RARFILE:
            with rarfile.RarFile(path, 'r') as rf:
                for info in rf.infolist():
                    entries.append(ArchiveEntry(
                        name=info.filename,
                        size=info.file_size,
                        compressed_size=info.compress_size,
                        is_dir=info.is_dir()
                    ))
        else:
            raise ValueError(f"Unsupported archive format: {suffix}")
        
        return entries
    
    def extract(
        self, 
        archive_path: str, 
        destination: Optional[str] = None,
        members: Optional[list[str]] = None
    ) -> list[str]:
        """
        Extract archive contents.
        
        Args:
            archive_path: Path to archive
            destination: Destination directory (default: same as archive)
            members: Specific members to extract (default: all)
            
        Returns:
            List of extracted file paths
        """
        path = Path(archive_path)
        suffix = path.suffix.lower()
        
        if destination:
            dest = Path(destination)
        else:
            dest = path.parent / path.stem
        
        dest.mkdir(parents=True, exist_ok=True)
        
        extracted = []
        
        if suffix == ".zip":
            with zipfile.ZipFile(path, 'r') as zf:
                # P0 Security: Validate all paths before extraction
                for info in zf.infolist():
                    if not self._is_safe_path(dest, info.filename):
                        raise ValueError(f"Unsafe path in archive: {info.filename}")
                
                if members:
                    for member in members:
                        if not self._is_safe_path(dest, member):
                            raise ValueError(f"Unsafe path: {member}")
                        zf.extract(member, dest)
                        extracted.append(str(dest / member))
                else:
                    zf.extractall(dest)
                    extracted = [str(dest / name) for name in zf.namelist()]
        
        elif suffix == ".rar" and HAS_RARFILE:
            with rarfile.RarFile(path, 'r') as rf:
                # P0 Security: Validate all paths before extraction
                for info in rf.infolist():
                    if not self._is_safe_path(dest, info.filename):
                        raise ValueError(f"Unsafe path in archive: {info.filename}")
                
                if members:
                    for member in members:
                        if not self._is_safe_path(dest, member):
                            raise ValueError(f"Unsafe path: {member}")
                        rf.extract(member, dest)
                        extracted.append(str(dest / member))
                else:
                    rf.extractall(dest)
                    extracted = [str(dest / name) for name in rf.namelist()]
        else:
            raise ValueError(f"Unsupported archive format: {suffix}")
        
        return extracted
    
    def create_zip(
        self,
        output_path: str,
        files: list[str],
        compression: int = zipfile.ZIP_DEFLATED
    ) -> str:
        """
        Create a ZIP archive.
        
        Args:
            output_path: Output ZIP file path
            files: List of files/directories to include
            compression: Compression method
            
        Returns:
            Path to created archive
        """
        output = Path(output_path)
        if not output.suffix:
            output = output.with_suffix(".zip")
        
        with zipfile.ZipFile(output, 'w', compression) as zf:
            for file_path in files:
                path = Path(file_path)
                if path.is_file():
                    zf.write(path, path.name)
                elif path.is_dir():
                    for child in path.rglob("*"):
                        if child.is_file():
                            arcname = child.relative_to(path.parent)
                            zf.write(child, arcname)
        
        return str(output)
    
    def get_archive_info(self, archive_path: str) -> dict:
        """Get summary information about an archive."""
        entries = self.list_contents(archive_path)
        
        total_size = sum(e.size for e in entries)
        compressed_size = sum(e.compressed_size for e in entries)
        files = [e for e in entries if not e.is_dir]
        dirs = [e for e in entries if e.is_dir]
        
        return {
            "path": archive_path,
            "total_files": len(files),
            "total_dirs": len(dirs),
            "total_size": total_size,
            "compressed_size": compressed_size,
            "compression_ratio": f"{(1 - compressed_size/total_size)*100:.1f}%" if total_size > 0 else "0%"
        }


# Global archive manager
archives = ArchiveManager()
