# Sample output
```
2021-07-30 14:20:43,662 - healthcheck.git-api - DEBUG - Loading healthcheck for git-api
2021-07-30 14:20:43,662 - healthcheck.git-api - DEBUG - Running check against http://127.0.0.1:5050/status
2021-07-30 14:20:43,664 - urllib3.connectionpool - DEBUG - Starting new HTTP connection (1): 127.0.0.1:5050
2021-07-30 14:20:43,666 - urllib3.connectionpool - DEBUG - http://127.0.0.1:5050 "GET /status HTTP/1.1" 200 356
2021-07-30 14:20:43,666 - healthcheck.git-api - INFO - {"detailed": false, "reasons": [{"class": "git_cli", "details": "git CLI available", "reason": true}, {"class": "up_gerrit", "details": "Upstream Gerrit OK", "reason": true}, {"class": "down_gerrit", "details": "Downstream Gerrit OK", "reason": true}]}
```
