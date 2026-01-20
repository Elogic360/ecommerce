"""
Upload Service
File upload handling with validation, thumbnail generation, and storage management.
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime
from io import BytesIO

from fastapi import UploadFile, HTTPException, status
from PIL import Image

from app.core.config import settings


# =============================================================================
# CONSTANTS
# =============================================================================

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}

# Size limits
MAX_FILE_SIZE = settings.MAX_FILE_SIZE  # 5MB default
MAX_IMAGES_PER_PRODUCT = 5

# Image dimensions
MAX_IMAGE_WIDTH = 2000
MAX_IMAGE_HEIGHT = 2000
THUMBNAIL_SIZE = (300, 300)
MEDIUM_SIZE = (800, 800)

# Upload directories
UPLOAD_BASE_DIR = Path(settings.UPLOAD_DIR).parent
PRODUCTS_DIR = Path(settings.UPLOAD_DIR)
THUMBNAILS_DIR = PRODUCTS_DIR / "thumbnails"
CATEGORIES_DIR = UPLOAD_BASE_DIR / "categories"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_upload_dirs():
    """Create upload directories if they don't exist"""
    for directory in [PRODUCTS_DIR, THUMBNAILS_DIR, CATEGORIES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """Get lowercase file extension from filename"""
    return Path(filename).suffix.lower()


def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """Generate a unique filename preserving the extension"""
    ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}{ext}"
    return f"{timestamp}_{unique_id}{ext}"


def get_image_dimensions(file_content: bytes) -> Tuple[int, int]:
    """Get image width and height"""
    with Image.open(BytesIO(file_content)) as img:
        return img.size


def validate_image_dimensions(width: int, height: int) -> bool:
    """Validate image is not too large"""
    return width <= MAX_IMAGE_WIDTH and height <= MAX_IMAGE_HEIGHT


# =============================================================================
# IMAGE PROCESSING
# =============================================================================

def create_thumbnail(
    image_content: bytes, 
    size: Tuple[int, int] = THUMBNAIL_SIZE,
    quality: int = 85
) -> bytes:
    """Create a thumbnail from image content"""
    with Image.open(BytesIO(image_content)) as img:
        # Convert to RGB if necessary (for PNG with transparency)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Create thumbnail maintaining aspect ratio
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()


def optimize_image(
    image_content: bytes,
    max_size: Tuple[int, int] = MEDIUM_SIZE,
    quality: int = 85
) -> Tuple[bytes, int, int]:
    """Optimize image for web: resize if too large and compress"""
    with Image.open(BytesIO(image_content)) as img:
        original_format = img.format or 'JPEG'
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            if original_format == 'PNG':
                # Keep transparency for PNG
                pass
            else:
                img = img.convert('RGB')
        
        # Resize if larger than max size
        if img.width > max_size[0] or img.height > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        width, height = img.size
        
        # Save optimized
        output = BytesIO()
        if original_format == 'PNG' and img.mode == 'RGBA':
            img.save(output, format='PNG', optimize=True)
        else:
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(output, format='JPEG', quality=quality, optimize=True)
        
        return output.getvalue(), width, height


# =============================================================================
# VALIDATION
# =============================================================================

async def validate_upload_file(
    file: UploadFile,
    allowed_extensions: set = ALLOWED_EXTENSIONS,
    max_size: int = MAX_FILE_SIZE
) -> bytes:
    """
    Validate uploaded file for extension, size, and content type.
    Returns file content if valid.
    """
    # Check file exists
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Check extension
    ext = get_file_extension(file.filename)
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check content type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type: {file.content_type}"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {max_size // (1024 * 1024)}MB"
        )
    
    # Validate it's actually an image
    try:
        with Image.open(BytesIO(content)) as img:
            img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file"
        )
    
    # Re-read since verify() consumes the file
    await file.seek(0)
    content = await file.read()
    
    # Check dimensions
    width, height = get_image_dimensions(content)
    if not validate_image_dimensions(width, height):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Maximum: {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT}px"
        )
    
    return content


# =============================================================================
# FILE STORAGE
# =============================================================================

class ImageUploadResult:
    """Result of an image upload operation"""
    def __init__(
        self,
        filename: str,
        image_url: str,
        thumbnail_url: str,
        file_size: int,
        width: int,
        height: int
    ):
        self.filename = filename
        self.image_url = image_url
        self.thumbnail_url = thumbnail_url
        self.file_size = file_size
        self.width = width
        self.height = height


async def save_product_image(
    file: UploadFile,
    product_id: Optional[int] = None,
    optimize: bool = True
) -> ImageUploadResult:
    """
    Save a product image with thumbnail generation.
    
    Args:
        file: The uploaded file
        product_id: Optional product ID for filename prefix
        optimize: Whether to optimize the image
        
    Returns:
        ImageUploadResult with URLs and metadata
    """
    ensure_upload_dirs()
    
    # Validate file
    content = await validate_upload_file(file)
    
    # Generate filename
    prefix = f"product_{product_id}" if product_id else "product"
    filename = generate_unique_filename(file.filename, prefix)
    
    # Optimize image if requested
    if optimize:
        content, width, height = optimize_image(content)
    else:
        width, height = get_image_dimensions(content)
    
    # Save main image
    image_path = PRODUCTS_DIR / filename
    with open(image_path, 'wb') as f:
        f.write(content)
    
    # Create and save thumbnail
    thumbnail_content = create_thumbnail(content)
    thumbnail_filename = f"thumb_{filename.rsplit('.', 1)[0]}.jpg"
    thumbnail_path = THUMBNAILS_DIR / thumbnail_filename
    with open(thumbnail_path, 'wb') as f:
        f.write(thumbnail_content)
    
    # Generate URLs (relative to static mount)
    image_url = f"/uploads/products/{filename}"
    thumbnail_url = f"/uploads/products/thumbnails/{thumbnail_filename}"
    
    return ImageUploadResult(
        filename=filename,
        image_url=image_url,
        thumbnail_url=thumbnail_url,
        file_size=len(content),
        width=width,
        height=height
    )


async def save_category_image(file: UploadFile, category_id: Optional[int] = None) -> str:
    """Save a category image and return the URL"""
    ensure_upload_dirs()
    
    content = await validate_upload_file(file)
    
    # Optimize for category images (smaller size)
    content, _, _ = optimize_image(content, max_size=(600, 600))
    
    prefix = f"category_{category_id}" if category_id else "category"
    filename = generate_unique_filename(file.filename, prefix)
    
    image_path = CATEGORIES_DIR / filename
    with open(image_path, 'wb') as f:
        f.write(content)
    
    return f"/uploads/categories/{filename}"


def delete_image(image_url: str) -> bool:
    """Delete an image file from storage"""
    if not image_url:
        return False
    
    try:
        # Convert URL to file path
        relative_path = image_url.lstrip('/')
        file_path = UPLOAD_BASE_DIR.parent / relative_path
        
        if file_path.exists():
            file_path.unlink()
            return True
    except Exception:
        pass
    
    return False


def delete_product_images(image_url: str, thumbnail_url: str = None) -> None:
    """Delete a product image and its thumbnail"""
    delete_image(image_url)
    if thumbnail_url:
        delete_image(thumbnail_url)


async def save_multiple_product_images(
    files: List[UploadFile],
    product_id: int,
    max_images: int = MAX_IMAGES_PER_PRODUCT
) -> List[ImageUploadResult]:
    """
    Save multiple product images with validation.
    
    Args:
        files: List of uploaded files
        product_id: The product ID
        max_images: Maximum number of images allowed
        
    Returns:
        List of ImageUploadResult objects
    """
    if len(files) > max_images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {max_images} images allowed per product"
        )
    
    results = []
    for file in files:
        result = await save_product_image(file, product_id)
        results.append(result)
    
    return results


# =============================================================================
# CLEANUP UTILITIES
# =============================================================================

def cleanup_orphaned_images(valid_urls: List[str]) -> int:
    """
    Remove images that are not in the valid_urls list.
    Use with caution - intended for maintenance tasks.
    
    Returns number of deleted files.
    """
    deleted_count = 0
    
    for directory in [PRODUCTS_DIR, THUMBNAILS_DIR]:
        if not directory.exists():
            continue
            
        for file_path in directory.iterdir():
            if file_path.is_file():
                relative_url = f"/uploads/products/{file_path.name}"
                if file_path.parent == THUMBNAILS_DIR:
                    relative_url = f"/uploads/products/thumbnails/{file_path.name}"
                
                if relative_url not in valid_urls:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception:
                        pass
    
    return deleted_count
