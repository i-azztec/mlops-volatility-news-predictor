"""
Simple S3 Browser Web Interface for LocalStack
Using built-in HTTP server with HTML interface
"""

import http.server
import socketserver
import json
import boto3
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime

class S3BrowserHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/' or path == '/index.html':
            self.serve_index()
        elif path == '/api/buckets':
            self.serve_buckets()
        elif path.startswith('/api/objects/'):
            bucket_name = path.split('/')[-1]
            self.serve_objects(bucket_name)
        else:
            self.send_error(404)
    
    def serve_index(self):
        """Serve the main HTML page"""
        html = '''
<!DOCTYPE html>
<html>
<head>
    <title>LocalStack S3 Browser</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .bucket { background: #f5f5f5; padding: 10px; margin: 5px 0; border-radius: 5px; }
        .object { background: #e9e9e9; padding: 8px; margin: 3px 0; border-radius: 3px; }
        .header { background: #007bff; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .status { background: #28a745; color: white; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .error { background: #dc3545; color: white; padding: 10px; border-radius: 5px; margin: 10px 0; }
        button { background: #007bff; color: white; border: none; padding: 10px 15px; border-radius: 3px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 LocalStack S3 Browser</h1>
            <p>Web interface for browsing S3 buckets and objects</p>
        </div>
        
        <div id="status" class="status">
            ✅ Connected to LocalStack S3 (localhost:4566)
        </div>
        
        <div>
            <button onclick="loadBuckets()">🔄 Refresh Buckets</button>
        </div>
        
        <div id="content">
            <p>Loading buckets...</p>
        </div>
    </div>

    <script>
        async function loadBuckets() {
            try {
                const response = await fetch('/api/buckets');
                const buckets = await response.json();
                
                let html = '<h2>🗂️ S3 Buckets</h2>';
                
                if (buckets.length === 0) {
                    html += '<p>No buckets found. Create buckets using AWS CLI:</p>';
                    html += '<pre>aws --endpoint-url=http://localhost:4566 s3 mb s3://my-bucket</pre>';
                } else {
                    for (const bucket of buckets) {
                        html += `<div class="bucket">
                            <h3>📂 ${bucket}</h3>
                            <button onclick="loadObjects('${bucket}')">📄 View Objects</button>
                            <div id="objects-${bucket}"></div>
                        </div>`;
                    }
                }
                
                document.getElementById('content').innerHTML = html;
            } catch (error) {
                document.getElementById('content').innerHTML = 
                    '<div class="error">❌ Error loading buckets: ' + error.message + '</div>';
            }
        }
        
        async function loadObjects(bucket) {
            try {
                const response = await fetch(`/api/objects/${bucket}`);
                const objects = await response.json();
                
                let html = '<h4>Objects:</h4>';
                
                if (objects.length === 0) {
                    html += '<p>No objects found in this bucket.</p>';
                } else {
                    for (const obj of objects) {
                        const sizeKB = (obj.Size / 1024).toFixed(2);
                        const icon = getFileIcon(obj.Key);
                        html += `<div class="object">
                            ${icon} <strong>${obj.Key}</strong> 
                            <span style="color: #666;">(${sizeKB} KB, ${obj.LastModified})</span>
                        </div>`;
                    }
                }
                
                document.getElementById(`objects-${bucket}`).innerHTML = html;
            } catch (error) {
                document.getElementById(`objects-${bucket}`).innerHTML = 
                    '<div class="error">❌ Error loading objects: ' + error.message + '</div>';
            }
        }
        
        function getFileIcon(filename) {
            if (filename.endsWith('.parquet')) return '📊';
            if (filename.endsWith('.csv')) return '📈';
            if (filename.endsWith('.pkl')) return '�';
            if (filename.endsWith('/')) return '📁';
            return '📄';
        }
        
        // Auto-load buckets on page load
        loadBuckets();
    </script>
</body>
</html>
        '''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_buckets(self):
        """API endpoint to list buckets"""
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=os.getenv('S3_ENDPOINT_URL', 'http://localhost:4566'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )
            
            response = s3_client.list_buckets()
            buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(buckets).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def serve_objects(self, bucket_name):
        """API endpoint to list objects in bucket"""
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=os.getenv('S3_ENDPOINT_URL', 'http://localhost:4566'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )
            
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name)
            
            objects = []
            for page in pages:
                for obj in page.get('Contents', []):
                    objects.append({
                        'Key': obj['Key'],
                        'Size': obj['Size'],
                        'LastModified': obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S'),
                        'StorageClass': obj.get('StorageClass', 'STANDARD')
                    })
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(objects).encode())
            
        except Exception as e:
            self.send_error(500, str(e))

def main():
    """Start the S3 Browser server"""
    PORT = 8090
    
    with socketserver.TCPServer(("", PORT), S3BrowserHandler) as httpd:
        print(f"📁 S3 Browser starting on port {PORT}")
        print(f"🌐 Open http://localhost:{PORT} in your browser")
        print("🔧 LocalStack endpoint:", os.getenv('S3_ENDPOINT_URL', 'http://localhost:4566'))
        httpd.serve_forever()

if __name__ == "__main__":
    main()
