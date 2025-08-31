from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image
import os

class CustomUser(AbstractUser):
    # Profile fields
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True) 
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Resize avatar if it exists
        if self.avatar:
            img_path = self.avatar.path
            if os.path.exists(img_path):
                with Image.open(img_path) as img:
                    # Convert RGBA to RGB if necessary
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                    
                    # Resize to max 400x400 to keep file sizes reasonable
                    if img.height > 400 or img.width > 400:
                        output_size = (400, 400)
                        img.thumbnail(output_size, Image.Resampling.LANCZOS)
                        img.save(img_path, optimize=True, quality=85)

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
