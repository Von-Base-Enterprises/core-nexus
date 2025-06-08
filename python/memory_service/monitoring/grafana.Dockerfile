FROM grafana/grafana:latest

# Copy provisioning configs and dashboards
COPY grafana/provisioning /etc/grafana/provisioning
COPY grafana/dashboards /var/lib/grafana/dashboards

# Set permissions
USER root
RUN chown -R grafana:grafana /etc/grafana/provisioning /var/lib/grafana/dashboards
USER grafana

# Expose port
EXPOSE 3000

# Environment variables
ENV GF_SECURITY_ADMIN_USER=admin
ENV GF_SECURITY_ADMIN_PASSWORD=admin123
ENV GF_USERS_ALLOW_SIGN_UP=false