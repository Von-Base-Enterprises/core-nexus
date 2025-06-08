FROM prom/prometheus:latest

# Copy Prometheus configuration
COPY prometheus.yml /etc/prometheus/
COPY alerts.yml /etc/prometheus/

# Expose port
EXPOSE 9090

# Use environment variable for target URL
ENTRYPOINT ["sh", "-c", "sed -i 's|CORE_NEXUS_URL|'${CORE_NEXUS_URL}'|g' /etc/prometheus/prometheus.yml && /bin/prometheus --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus --web.console.libraries=/etc/prometheus/console_libraries --web.console.templates=/etc/prometheus/consoles --web.enable-lifecycle"]