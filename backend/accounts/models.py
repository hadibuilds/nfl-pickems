from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image
from django.core.files.storage import default_storage
from django.conf import settings
import io

class CustomUser(AbstractUser):
    # Profile fields
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True) 
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Resize avatar if it exists - works with both local and S3 storage
        if self.avatar and hasattr(self.avatar, 'file'):
            try:
                # Open the image from storage
                self.avatar.file.seek(0)  # Reset file pointer
                img = Image.open(self.avatar.file)
                
                # Convert RGBA to RGB if necessary
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                
                # Resize to max 400x400 to keep file sizes reasonable
                if img.height > 400 or img.width > 400:
                    output_size = (400, 400)
                    img.thumbnail(output_size, Image.Resampling.LANCZOS)
                    
                    # Save resized image to bytes buffer
                    output = io.BytesIO()
                    img.save(output, format='JPEG', optimize=True, quality=85)
                    output.seek(0)
                    
                    # Save back to storage (works with both local and S3)
                    self.avatar.save(
                        self.avatar.name,
                        output,
                        save=False  # Prevent recursive save calls
                    )
            except Exception as e:
                # Log the error but don't break the save process
                print(f"Avatar resize error for user {self.username}: {e}")
                pass

    @property
    def display_name(self):
        """Return the best available display name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username
            
    def __str__(self):
        return f"{self.username} ({self.display_name})"
