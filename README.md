# Centralized Logging & Monitoring Platform

This is a microservice-based platform designed for centralized logging, monitoring, and alerting. It collects logs from various microservices, stores them, and provides a user-friendly interface for querying and visualizing logs. Real-time monitoring and alerting are integrated to notify users about system anomalies.

### **Key Features:**
- **Log Collection:** Aggregate logs from various microservices via an API.
- **Log Storage:** Efficient log storage using **Loki** or **Elasticsearch**.
- **Log Querying:** Query logs based on various filters (e.g., timestamps, service name, log severity).
- **Metrics Collection:** Collect and store system metrics with **Prometheus**.
- **Alerting:** Notify users of anomalies via **Prometheus Alertmanager** (Slack/email alerts).
- **Visualization:** Use **Grafana** for visualizing logs and metrics in real-time.

### **Technologies Used:**
- **Flask**: For developing backend microservices.
- **OpenTelemetry**: For collecting traces and metrics.
- **Loki/Elasticsearch**: For log storage.
- **Prometheus**: For metrics collection.
- **Grafana**: For data visualization.
- **GitHub Actions**: For CI/CD automation.
- **Docker & Kubernetes**: For containerized deployment.
- **JWT Authentication**: For secure API access.

| Service       | Port  | Description                           |
|---------------|-------|---------------------------------------|
| Flask App     | 5050  | Main application                      |
| PostgreSQL    | 5432  | Database for the app                  |
| PGAdmin       | 8080  | GUI for PostgreSQL                    |
| Prometheus    | 9090  | Time-series metrics                   |
| Node Exporter | 9100  | Host-level metrics                    |
| Grafana       | 3000  | Dashboards for metrics visualization  |
| Elasticsearch | 9200  | Log storage/search                    |
| Kibana        | 5601  | Visualization for logs                |
| Fluentd       | —     | Log collector, sends to Elasticsearch |

### **How to Use:**
1. Clone the repository: `git clone <repo_url>`
2. Build and run using Docker: `docker-compose up`
3. Access the dashboard via `http://localhost:3000` (Grafana).

