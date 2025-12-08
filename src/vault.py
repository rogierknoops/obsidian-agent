"""
Vault operations module for reading and modifying Obsidian files.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import pathspec


@dataclass
class VaultFile:
    """Represents a file in the Obsidian vault."""
    path: Path
    relative_path: str
    content: str
    
    @property
    def name(self) -> str:
        return self.path.stem
    
    @property
    def extension(self) -> str:
        return self.path.suffix


class VaultManager:
    """Manages access to an Obsidian vault."""
    
    MARKDOWN_EXTENSIONS = {'.md', '.markdown'}
    IGNORE_DIRS = {'.obsidian', '.git', '.trash', 'node_modules'}
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).expanduser().resolve()
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")
        if not self.vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {self.vault_path}")
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        parts = path.relative_to(self.vault_path).parts
        return any(part in self.IGNORE_DIRS for part in parts)
    
    def list_files(self, pattern: Optional[str] = None) -> list[VaultFile]:
        """List all markdown files in the vault, optionally filtered by pattern."""
        files = []
        
        for file_path in self.vault_path.rglob('*'):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in self.MARKDOWN_EXTENSIONS:
                continue
            if self._should_ignore(file_path):
                continue
            
            relative = str(file_path.relative_to(self.vault_path))
            
            if pattern:
                spec = pathspec.PathSpec.from_lines('gitwildmatch', [pattern])
                if not spec.match_file(relative):
                    continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                files.append(VaultFile(
                    path=file_path,
                    relative_path=relative,
                    content=content
                ))
            except Exception:
                continue
        
        return sorted(files, key=lambda f: f.relative_path)
    
    def read_file(self, relative_path: str) -> Optional[VaultFile]:
        """Read a specific file from the vault."""
        file_path = self.vault_path / relative_path
        
        if not file_path.exists():
            return None
        if not file_path.is_file():
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
            return VaultFile(
                path=file_path,
                relative_path=relative_path,
                content=content
            )
        except Exception:
            return None
    
    def write_file(self, relative_path: str, content: str) -> bool:
        """Write content to a file in the vault."""
        file_path = self.vault_path / relative_path
        
        # Ensure parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            file_path.write_text(content, encoding='utf-8')
            return True
        except Exception:
            return False
    
    def search_content(self, query: str, case_sensitive: bool = False) -> list[VaultFile]:
        """Search for files containing a specific string."""
        results = []
        search_query = query if case_sensitive else query.lower()
        
        for vault_file in self.list_files():
            content = vault_file.content if case_sensitive else vault_file.content.lower()
            if search_query in content:
                results.append(vault_file)
        
        return results
    
    def get_file_tree(self, max_depth: int = 3) -> str:
        """Get a tree representation of the vault structure."""
        lines = [f"📁 {self.vault_path.name}/"]
        
        def add_directory(dir_path: Path, prefix: str = "", depth: int = 0):
            if depth >= max_depth:
                return
            
            try:
                items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                return
            
            # Filter out ignored directories and non-markdown files
            filtered_items = []
            for item in items:
                if item.is_dir():
                    if item.name not in self.IGNORE_DIRS and not item.name.startswith('.'):
                        filtered_items.append(item)
                elif item.suffix.lower() in self.MARKDOWN_EXTENSIONS:
                    filtered_items.append(item)
            
            for i, item in enumerate(filtered_items):
                is_last = i == len(filtered_items) - 1
                connector = "└── " if is_last else "├── "
                
                if item.is_dir():
                    lines.append(f"{prefix}{connector}📁 {item.name}/")
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    add_directory(item, new_prefix, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}📄 {item.name}")
        
        add_directory(self.vault_path)
        return "\n".join(lines)

