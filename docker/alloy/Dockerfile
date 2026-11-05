# Pin to a specific release; update intentionally after testing.
FROM grafana/alloy:v1.4.3
COPY config.alloy /etc/alloy/config.alloy
# Port 12345 is Alloy's admin/health UI. Railway needs 0.0.0.0 for internal
# health checks, but do NOT assign a public Railway domain to this service.
EXPOSE 12345
ENTRYPOINT ["alloy", "run", "/etc/alloy/config.alloy", "--server.http.listen-addr=0.0.0.0:12345"]
