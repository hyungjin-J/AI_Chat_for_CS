package com.aichatbot.contexts.operations.application;

import java.util.Map;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class OpsDimensionsSanitizerTest {

    private final OpsDimensionsSanitizer sanitizer = new OpsDimensionsSanitizer();

    @Test
    void shouldHashSensitiveDimensionKeys() {
        Map<String, Object> input = Map.of(
            "login_id", "agent1",
            "ip", "10.20.30.40",
            "tenant_key", "demo-tenant",
            "metric_key", "auth_login_failed"
        );

        Map<String, Object> sanitized = sanitizer.sanitize(input);

        assertThat(sanitized.get("login_id").toString()).startsWith("sha256:");
        assertThat(sanitized.get("ip").toString()).startsWith("sha256:");
        assertThat(sanitized.get("tenant_key").toString()).startsWith("sha256:");
        assertThat(sanitized.get("login_id")).isNotEqualTo("agent1");
        assertThat(sanitized.get("metric_key")).isEqualTo("auth_login_failed");
    }

    @Test
    void shouldRedactFreeTextPiiInNonSensitiveField() {
        Map<String, Object> input = Map.of(
            "note",
            "contact me at agent1@example.com or +82 10-1234-5678 from 192.168.10.22"
        );

        Map<String, Object> sanitized = sanitizer.sanitize(input);

        assertThat(sanitized.get("note").toString()).doesNotContain("agent1@example.com");
        assertThat(sanitized.get("note").toString()).doesNotContain("10-1234-5678");
        assertThat(sanitized.get("note").toString()).doesNotContain("192.168.10.22");
        assertThat(sanitized.get("note").toString()).contains("<REDACTED>");
    }
}
