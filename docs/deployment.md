# Deployment Guide

Production deployment guide for SPARQL Agent.

## Deployment Options

1. **Docker** - Recommended for most deployments
2. **Kubernetes** - For scalable, cloud-native deployments
3. **Systemd** - For bare-metal Linux servers
4. **Cloud Platforms** - AWS, GCP, Azure

## Docker Deployment

### Single Container

```bash
# Build image
docker build -t sparql-agent:latest .

# Run web server
docker run -d \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
  --name sparql-agent-web \
  sparql-agent:latest \
  sparql-agent-server

# Run MCP server
docker run -d \
  -p 3000:3000 \
  -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
  --name sparql-agent-mcp \
  sparql-agent:latest \
  sparql-agent-mcp
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    image: sparql-agent:latest
    command: sparql-agent-server --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped

  mcp:
    image: sparql-agent:latest
    command: sparql-agent-mcp --host 0.0.0.0 --port 3000
    ports:
      - "3000:3000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./config:/app/config
    restart: unless-stopped

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  redis-data:
  prometheus-data:
  grafana-data:
```

Deploy:

```bash
docker-compose up -d
```

## Kubernetes Deployment

### Deployment Manifest

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sparql-agent-web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sparql-agent-web
  template:
    metadata:
      labels:
        app: sparql-agent-web
    spec:
      containers:
      - name: sparql-agent
        image: david4096/sparql-agent:latest
        command: ["sparql-agent-server"]
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: sparql-agent-secrets
              key: anthropic-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: sparql-agent-service
spec:
  selector:
    app: sparql-agent-web
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sparql-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sparql-agent-web
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

Deploy:

```bash
kubectl apply -f k8s/
```

## Environment Configuration

### Production Config

```yaml
# config/production.yaml
llm:
  provider: anthropic
  model: claude-3-5-sonnet-20241022
  temperature: 0.0

endpoints:
  default: https://sparql.uniprot.org/sparql

cache:
  enabled: true
  backend: redis
  redis:
    host: redis
    port: 6379

logging:
  level: INFO
  format: json
  output: /app/logs/sparql-agent.log

web:
  workers: 4
  rate_limit:
    enabled: true
    requests_per_minute: 100

security:
  validate_queries: true
```

## Monitoring

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'sparql-agent'
    static_configs:
      - targets: ['web:8000']
```

### Grafana Dashboard

Import dashboard from `monitoring/grafana-dashboard.json`

## Load Balancing

### Nginx

```nginx
# nginx.conf
upstream sparql_agent {
    least_conn;
    server web1:8000;
    server web2:8000;
    server web3:8000;
}

server {
    listen 80;
    server_name sparql-agent.example.com;

    location / {
        proxy_pass http://sparql_agent;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## SSL/TLS

### Let's Encrypt

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d sparql-agent.example.com
```

## Backup & Recovery

### Backup Strategy

```bash
# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/

# Backup Redis data
redis-cli --rdb /backup/dump.rdb

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

## Security Checklist

- [ ] API keys in secrets, not environment
- [ ] Enable rate limiting
- [ ] Configure CORS properly
- [ ] Use HTTPS only
- [ ] Enable query validation
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Monitor for anomalies

## Performance Tuning

### Application Settings

```yaml
query:
  timeout: 60
  max_results: 1000

cache:
  ttl: 3600

web:
  workers: 4
  max_connections: 1000
```

### Database Tuning

```bash
# Redis
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Scaling

### Horizontal Scaling

```bash
# Docker Compose
docker-compose up --scale web=3

# Kubernetes
kubectl scale deployment sparql-agent-web --replicas=5
```

### Vertical Scaling

```yaml
# Increase resources
resources:
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

## Maintenance

### Rolling Updates

```bash
# Kubernetes
kubectl rollout status deployment/sparql-agent-web
kubectl rollout history deployment/sparql-agent-web
kubectl rollout undo deployment/sparql-agent-web
```

### Health Checks

```bash
# Check health
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**: Increase limits, enable caching
2. **Slow Queries**: Optimize timeouts, use connection pooling
3. **API Rate Limits**: Implement backoff, cache results
4. **Connection Errors**: Check network, firewall rules

### Log Analysis

```bash
# View logs
docker-compose logs -f web

# Search errors
docker-compose logs web | grep ERROR

# Kubernetes logs
kubectl logs -f deployment/sparql-agent-web
```

## Next Steps

- [Monitoring Guide](best-practices/monitoring.md)
- [Security Best Practices](best-practices/security.md)
- [Troubleshooting](troubleshooting.md)
