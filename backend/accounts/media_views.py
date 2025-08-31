"""
Secure media serving views that require authentication
"""
import os
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views import View
import mimetypes


@method_decorator([login_required, require_GET], name='dispatch')
class SecureMediaView(View):
    """
    Serve media files only to authenticated users
    """
    
    def get(self, request, file_path):
        # Security check: only allow avatar files
        if not file_path.startswith('avatars/'):
            raise Http404("File not found")
        
        # Construct full file path
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # Security check: prevent directory traversal
        if not full_path.startswith(settings.MEDIA_ROOT):
            raise Http404("File not found")
        
        # Check if file exists
        if not os.path.exists(full_path):
            raise Http404("File not found")
        
        # Get content type
        content_type, _ = mimetypes.guess_type(full_path)
        if not content_type:
            content_type = 'application/octet-stream'
        
        # Serve the file
        try:
            with open(full_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type=content_type)
                # Add cache headers for better performance
                response['Cache-Control'] = 'private, max-age=3600'  # 1 hour cache
                return response
        except IOError:
            raise Http404("File not found")


# Function-based view alternative
@login_required
@require_GET 
def serve_avatar(request, file_path):
    """
    Alternative function-based view for serving avatars
    """
    # Only allow avatar files
    if not file_path.startswith('avatars/'):
        raise Http404("File not found")
    
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    
    # Security checks
    if not full_path.startswith(settings.MEDIA_ROOT) or not os.path.exists(full_path):
        raise Http404("File not found")
    
    # Serve file with proper content type
    content_type, _ = mimetypes.guess_type(full_path)
    
    try:
        with open(full_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type=content_type or 'application/octet-stream')
            response['Cache-Control'] = 'private, max-age=3600'
            return response
    except IOError:
        raise Http404("File not found")