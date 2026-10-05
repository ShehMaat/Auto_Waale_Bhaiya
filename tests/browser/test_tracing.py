from packages.browser.tracing import BrowserTracer


def test_tracer_redacts_sensitive_fields() -> None:
    tracer = BrowserTracer()

    metadata = {
        "normal_field": "hello",
        "password": "secret_password",
        "nested": {"otp_code": "123456", "safe_nested": "value"},
        "user_2fa_token": "token123",
    }

    redacted = tracer._redact_metadata(metadata)

    assert redacted["normal_field"] == "hello"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["nested"]["otp_code"] == "[REDACTED]"
    assert redacted["nested"]["safe_nested"] == "value"
    assert redacted["user_2fa_token"] == "[REDACTED]"
