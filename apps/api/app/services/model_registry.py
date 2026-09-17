"""
Model Registry Service for managing ML model versioning and remote storage.

Supports loading models from:
- Local filesystem
- Supabase Storage buckets
- AWS S3 buckets
- HTTP/HTTPS URLs

Models are cached locally after download for faster subsequent loads.
"""

import os
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import shutil

import httpx

# Optional S3 support - only import if available
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    boto3 = None
    ClientError = Exception  # Fallback for type hints

from app.config import settings


class StorageBackend(str, Enum):
    """Supported storage backends for model files"""
    LOCAL = "local"
    SUPABASE = "supabase"
    S3 = "s3"
    HTTP = "http"


@dataclass
class ModelMetadata:
    """Metadata for a registered model version"""
    name: str
    version: str
    backend: StorageBackend
    path: str  # Path within the storage backend
    checksum: Optional[str] = None  # SHA256 checksum for validation
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)  # Training metrics
    tags: Dict[str, str] = field(default_factory=dict)  # Custom tags
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "backend": self.backend.value,
            "path": self.path,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "description": self.description,
            "metrics": self.metrics,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        return cls(
            name=data["name"],
            version=data["version"],
            backend=StorageBackend(data["backend"]),
            path=data["path"],
            checksum=data.get("checksum"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            description=data.get("description"),
            metrics=data.get("metrics", {}),
            tags=data.get("tags", {}),
        )


class ModelRegistry:
    """
    Centralized model registry for managing ML model versions.
    
    Features:
    - Multi-backend support (local, Supabase, S3, HTTP)
    - Local caching for downloaded models
    - Version management and rollback capability
    - Checksum validation for integrity
    
    Example usage:
        registry = ModelRegistry()
        
        # Register a model from S3
        registry.register_model(
            name="pollution_yolo",
            version="1.0.0",
            backend=StorageBackend.S3,
            path="models/pollution_yolo_v1.pt",
            description="YOLOv8 pollution detection model"
        )
        
        # Load the model
        model_path = registry.get_model("pollution_yolo", version="1.0.0")
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        registry_file: Optional[str] = None
    ):
        """
        Initialize the model registry.
        
        Args:
            cache_dir: Local directory for caching downloaded models.
                      Defaults to ~/.samudrasense/models
            registry_file: Path to the JSON registry file.
                          Defaults to cache_dir/registry.json
        """
        self.cache_dir = Path(cache_dir or os.path.expanduser("~/.samudrasense/models"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry_file = Path(registry_file or self.cache_dir / "registry.json")
        self._registry: Dict[str, Dict[str, ModelMetadata]] = {}
        
        self._load_registry()
        
        # Initialize storage clients lazily
        self._s3_client = None
        self._supabase_client = None
    
    def _load_registry(self):
        """Load the model registry from disk"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    for name, versions in data.items():
                        self._registry[name] = {
                            v: ModelMetadata.from_dict(meta)
                            for v, meta in versions.items()
                        }
            except Exception as e:
                print(f"Warning: Could not load model registry: {e}")
                self._registry = {}
    
    def _save_registry(self):
        """Save the model registry to disk"""
        data = {
            name: {v: meta.to_dict() for v, meta in versions.items()}
            for name, versions in self._registry.items()
        }
        with open(self.registry_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    @property
    def s3_client(self):
        """Lazy initialization of S3 client"""
        if not HAS_BOTO3:
            raise RuntimeError(
                "boto3 is required for S3 storage backend. "
                "Install it with: pip install boto3"
            )
        if self._s3_client is None:
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                region_name=getattr(settings, 'AWS_REGION', 'us-east-1')
            )
        return self._s3_client
    
    @property
    def supabase_client(self):
        """Lazy initialization of Supabase client"""
        if self._supabase_client is None:
            from app.supabase_client import get_supabase_client
            self._supabase_client = get_supabase_client()
        return self._supabase_client
    
    def register_model(
        self,
        name: str,
        version: str,
        backend: StorageBackend,
        path: str,
        checksum: Optional[str] = None,
        description: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> ModelMetadata:
        """
        Register a new model version in the registry.
        
        Args:
            name: Model name (e.g., "pollution_yolo", "route_lstm")
            version: Semantic version string (e.g., "1.0.0")
            backend: Storage backend where the model is stored
            path: Path within the storage backend
            checksum: Optional SHA256 checksum for validation
            description: Human-readable description
            metrics: Training/evaluation metrics
            tags: Custom key-value tags
            
        Returns:
            The registered ModelMetadata
        """
        metadata = ModelMetadata(
            name=name,
            version=version,
            backend=backend,
            path=path,
            checksum=checksum,
            created_at=datetime.utcnow(),
            description=description,
            metrics=metrics or {},
            tags=tags or {},
        )
        
        if name not in self._registry:
            self._registry[name] = {}
        
        self._registry[name][version] = metadata
        self._save_registry()
        
        print(f"Registered model: {name} v{version} ({backend.value}:{path})")
        return metadata
    
    def get_model_metadata(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Optional[ModelMetadata]:
        """
        Get metadata for a registered model.
        
        Args:
            name: Model name
            version: Specific version, or None for latest
            
        Returns:
            ModelMetadata or None if not found
        """
        if name not in self._registry:
            return None
        
        versions = self._registry[name]
        if version:
            return versions.get(version)
        
        # Return the latest version (highest semantic version)
        if versions:
            latest_version = max(versions.keys())
            return versions[latest_version]
        
        return None
    
    def list_models(self) -> Dict[str, list]:
        """List all registered models and their versions"""
        return {
            name: list(versions.keys())
            for name, versions in self._registry.items()
        }
    
    def get_model(
        self,
        name: str,
        version: Optional[str] = None,
        force_download: bool = False
    ) -> Optional[str]:
        """
        Get the local path to a model, downloading if necessary.
        
        Args:
            name: Model name
            version: Specific version, or None for latest
            force_download: Re-download even if cached
            
        Returns:
            Local file path to the model, or None if not found
        """
        metadata = self.get_model_metadata(name, version)
        if metadata is None:
            print(f"Model not found in registry: {name} v{version}")
            return None
        
        # Check for cached version
        cache_path = self._get_cache_path(metadata)
        
        if cache_path.exists() and not force_download:
            # Validate checksum if available
            if metadata.checksum:
                actual_checksum = self._compute_checksum(cache_path)
                if actual_checksum != metadata.checksum:
                    print(f"Checksum mismatch for {name}, re-downloading...")
                else:
                    return str(cache_path)
            else:
                return str(cache_path)
        
        # Download from remote storage
        print(f"Downloading model: {name} v{metadata.version} from {metadata.backend.value}")
        
        try:
            self._download_model(metadata, cache_path)
            
            # Validate checksum after download
            if metadata.checksum:
                actual_checksum = self._compute_checksum(cache_path)
                if actual_checksum != metadata.checksum:
                    raise ValueError(f"Downloaded model checksum mismatch")
            
            return str(cache_path)
            
        except Exception as e:
            print(f"Failed to download model {name}: {e}")
            return None
    
    def _get_cache_path(self, metadata: ModelMetadata) -> Path:
        """Get the local cache path for a model"""
        # Use name/version/filename structure
        filename = Path(metadata.path).name
        return self.cache_dir / metadata.name / metadata.version / filename
    
    def _compute_checksum(self, filepath: Path) -> str:
        """Compute SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _download_model(self, metadata: ModelMetadata, dest_path: Path):
        """Download a model from remote storage"""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if metadata.backend == StorageBackend.LOCAL:
            # Just copy from local path
            shutil.copy2(metadata.path, dest_path)
            
        elif metadata.backend == StorageBackend.S3:
            self._download_from_s3(metadata.path, dest_path)
            
        elif metadata.backend == StorageBackend.SUPABASE:
            self._download_from_supabase(metadata.path, dest_path)
            
        elif metadata.backend == StorageBackend.HTTP:
            self._download_from_http(metadata.path, dest_path)
        
        else:
            raise ValueError(f"Unsupported backend: {metadata.backend}")
    
    def _download_from_s3(self, s3_path: str, dest_path: Path):
        """Download model from S3"""
        # Parse bucket and key from path (format: bucket/key/to/file.pt)
        parts = s3_path.split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 path format: {s3_path}. Expected: bucket/key")
        
        bucket, key = parts
        
        try:
            self.s3_client.download_file(bucket, key, str(dest_path))
        except ClientError as e:
            raise RuntimeError(f"Failed to download from S3: {e}")
    
    def _download_from_supabase(self, storage_path: str, dest_path: Path):
        """Download model from Supabase Storage"""
        # Parse bucket and path (format: bucket/path/to/file.pt)
        parts = storage_path.split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid Supabase path format: {storage_path}. Expected: bucket/path")
        
        bucket, file_path = parts
        
        try:
            # Download using Supabase storage API
            response = self.supabase_client.storage.from_(bucket).download(file_path)
            with open(dest_path, 'wb') as f:
                f.write(response)
        except Exception as e:
            raise RuntimeError(f"Failed to download from Supabase: {e}")
    
    def _download_from_http(self, url: str, dest_path: Path):
        """Download model from HTTP/HTTPS URL"""
        try:
            with httpx.Client(timeout=300.0) as client:  # 5 minute timeout for large models
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(dest_path, 'wb') as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
        except Exception as e:
            raise RuntimeError(f"Failed to download from HTTP: {e}")
    
    def upload_model(
        self,
        local_path: str,
        name: str,
        version: str,
        backend: StorageBackend,
        remote_path: str,
        description: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> ModelMetadata:
        """
        Upload a local model file to remote storage and register it.
        
        Args:
            local_path: Path to the local model file
            name: Model name for registration
            version: Version string
            backend: Target storage backend
            remote_path: Destination path in remote storage
            description: Model description
            metrics: Training metrics
            tags: Custom tags
            
        Returns:
            The registered ModelMetadata
        """
        local_file = Path(local_path)
        if not local_file.exists():
            raise FileNotFoundError(f"Local model file not found: {local_path}")
        
        # Compute checksum before upload
        checksum = self._compute_checksum(local_file)
        
        # Upload based on backend
        if backend == StorageBackend.S3:
            self._upload_to_s3(local_file, remote_path)
        elif backend == StorageBackend.SUPABASE:
            self._upload_to_supabase(local_file, remote_path)
        elif backend == StorageBackend.LOCAL:
            # For local, just copy to the remote_path
            dest = Path(remote_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_file, dest)
        else:
            raise ValueError(f"Upload not supported for backend: {backend}")
        
        # Register the model
        return self.register_model(
            name=name,
            version=version,
            backend=backend,
            path=remote_path,
            checksum=checksum,
            description=description,
            metrics=metrics,
            tags=tags,
        )
    
    def _upload_to_s3(self, local_file: Path, s3_path: str):
        """Upload model to S3"""
        parts = s3_path.split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 path format: {s3_path}")
        
        bucket, key = parts
        self.s3_client.upload_file(str(local_file), bucket, key)
    
    def _upload_to_supabase(self, local_file: Path, storage_path: str):
        """Upload model to Supabase Storage"""
        parts = storage_path.split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid Supabase path format: {storage_path}")
        
        bucket, file_path = parts
        
        with open(local_file, 'rb') as f:
            self.supabase_client.storage.from_(bucket).upload(file_path, f)
    
    def delete_model(self, name: str, version: Optional[str] = None):
        """
        Delete a model from the registry (and optionally from cache).
        
        Args:
            name: Model name
            version: Specific version to delete, or None to delete all versions
        """
        if name not in self._registry:
            return
        
        if version:
            if version in self._registry[name]:
                metadata = self._registry[name].pop(version)
                # Remove from cache
                cache_path = self._get_cache_path(metadata)
                if cache_path.exists():
                    cache_path.unlink()
                print(f"Deleted model: {name} v{version}")
        else:
            # Delete all versions
            for v, metadata in self._registry[name].items():
                cache_path = self._get_cache_path(metadata)
                if cache_path.exists():
                    cache_path.unlink()
            del self._registry[name]
            print(f"Deleted all versions of model: {name}")
        
        self._save_registry()


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get the global model registry instance"""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
