$port = 8080
$path = $PSScriptRoot

Write-Host "Starting DOOM CLONE Server at http://localhost:$port"
Write-Host "Press Ctrl+C to stop."

$http = [System.Net.HttpListener]::new() 
$http.Prefixes.Add("http://localhost:$($port)/") 
$http.Start() 

if ($http.IsListening) {
    Start-Process "http://localhost:$port"
}

try {
    while ($http.IsListening) { 
        $context = $http.GetContext() 
        $request = $context.Request 
        $response = $context.Response 
        
        $localPath = Join-Path $path $request.Url.LocalPath.TrimStart('/')
        
        # Default to index.html
        if ((Get-Item -Path $localPath -ErrorAction SilentlyContinue).PSIsContainer) {
            $localPath = Join-Path $localPath "index.html"
        }

        if (Test-Path $localPath) {
             # Basic MIME types
            $extension = [System.IO.Path]::GetExtension($localPath)
            switch ($extension) {
                ".html" { $contentType = "text/html" }
                ".js"   { $contentType = "application/javascript" }
                ".css"  { $contentType = "text/css" }
                default { $contentType = "application/octet-stream" }
            }
            
            $content = [System.IO.File]::ReadAllBytes($localPath)
            $response.ContentType = $contentType
            $response.ContentLength64 = $content.Length
            $response.OutputStream.Write($content, 0, $content.Length)
        } else {
            $response.StatusCode = 404
        }
        $response.Close() 
    }
} catch {
    Write-Host "Server stopped."
} finally {
    $http.Stop()
}
