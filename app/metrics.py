from prometheus_client import Counter, Histogram


login_counter = Counter("app_logins_total", "Total number of successful logins")

login_failure_counter = Counter(
    "app_login_failures_total", "Total number of failed login attempts"
)

registration_success_counter = Counter(
    "app_registrations_total", "Total successful user registrations"
)

registration_failure_counter = Counter(
    "app_registrations_failures_total", "Total failed user registrations"
)

endpoint_latency = Histogram(
    "app_request_latency_seconds", "Latency for specific endpoints", ["endpoint"]
)

email_confirmation_failure_counter = Counter(
    "app_email_confirmation_failures_total", "Total Failed email confirmations"
)

email_confirmation_success_counter = Counter(
    "app_email_confirmation_success_total", "Total Success email confirmations"
)

email_confirmation_sends_failure_counter = Counter(
    "app_email_confirmation_sends_failures_total",
    "Total Failed email confirmations sends",
)

email_confirmation_sends_success_counter = Counter(
    "app_email_confirmation_sends_success_total",
    "Total Success email confirmations sends",
)
