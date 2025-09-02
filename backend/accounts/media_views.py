"""
Secure media serving views that require authentication
"""
import os
import boto3
from django.http import HttpResponse, Http404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views import View
import mimetypes
import logging

logger = logging.getLogger(__name__)


@method_decorator([login_required, require_GET], name='dispatch')
class SecureMediaView(View):
    """
    Serve media files directly to authenticated users (like homepage access)
    """
    
    def get(self, request, file_path):
        # Security check: only allow avatar files
        if not file_path.startswith('avatars/'):
            raise Http404("File not found")
        
        # If using cloud storage, stream from S3
        if settings.USE_CLOUD_STORAGE:
            try:
                # Create S3 client
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                
                # Get the object from S3
                s3_object = s3_client.get_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=file_path
                )
                
                # Get content type from S3 or guess from filename
                content_type = s3_object.get('ContentType')
                if not content_type:
                    content_type, _ = mimetypes.guess_type(file_path)
                    if not content_type:
                        content_type = 'application/octet-stream'
                
                # Stream the file content
                file_content = s3_object['Body'].read()
                response = HttpResponse(file_content, content_type=content_type)
                
                # Add cache headers for better performance (private to authenticated users)
                response['Cache-Control'] = 'private, max-age=3600'  # 1 hour cache
                response['Content-Length'] = len(file_content)
                
                logger.debug(f"Served {file_path} from S3 to authenticated user")
                return response
                
            except Exception as e:
                logger.error(f"Error serving file {file_path} from S3: {str(e)}")
                raise Http404("File not found")
        
        # Fallback to local file serving
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