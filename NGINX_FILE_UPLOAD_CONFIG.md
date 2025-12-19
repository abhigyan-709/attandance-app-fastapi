# Nginx Configuration for Large File Uploads

## Problem
Employee creation fails with `413 Content Too Large` error when uploading documents (resume, photos, aadhar cards).

## Solution

### 1. FastAPI Configuration (Already Done)
Updated `main.py` to allow 50MB request body size.

### 2. Nginx Configuration (Required on Production Server)

Add this to your nginx configuration file (usually `/etc/nginx/nginx.conf` or `/etc/nginx/sites-available/api.projectdevops.in`):

```nginx
server {
    listen 80;
    server_name api.projectdevops.in;
    
    # Increase client body size limit to 50MB for file uploads
    client_max_body_size 50M;
    
    # Increase buffer sizes for large requests
    client_body_buffer_size 50M;
    client_header_buffer_size 16k;
    large_client_header_buffers 4 32k;
    
    # Increase timeouts for large file uploads
    client_body_timeout 300s;
    client_header_timeout 300s;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase proxy timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### 3. Apply Changes

After editing nginx config:

```bash
# Test nginx configuration
sudo nginx -t

# Reload nginx if test passes
sudo systemctl reload nginx

# Or restart nginx
sudo systemctl restart nginx
```

### 4. Restart FastAPI Application

```bash
# If using systemd
sudo systemctl restart fastapi-app

# If using PM2
pm2 restart fastapi-app

# If using Docker
docker restart attendance-api
```

## Verification

Test with curl:
```bash
curl -X POST "https://api.projectdevops.in/employees" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -F "name=Test Employee" \
  -F "email=test@example.com" \
  -F "resume_pdf=@large_resume.pdf" \
  -F "passport_photo=@photo.jpg" \
  -F "aadhar_front=@aadhar_front.jpg" \
  -F "aadhar_back=@aadhar_back.jpg"
```

## File Size Limits

Current configuration allows:
- **Individual file**: Up to 50MB
- **Total request**: Up to 50MB (4 files combined)

If you need larger files, increase `client_max_body_size` in nginx and the uvicorn limit in `main.py`.

## Common Issues

1. **Still getting 413**: Check if there's another nginx/proxy in front (load balancer, CDN)
2. **Timeout errors**: Increase timeout values in nginx
3. **Memory issues**: Monitor server resources during large uploads
