FROM grafana/alloy:latest
COPY config.alloy /etc/alloy/config.alloy
EXPOSE 12345
ENTRYPOINT ["alloy", "run", "/etc/alloy/config.alloy", "--server.http.listen-addr=0.0.0.0:12345"]
