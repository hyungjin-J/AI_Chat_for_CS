package com.aichatbot.global.privacy;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class PiiMaskingServiceTest {

    private final PiiMaskingService piiMaskingService = new PiiMaskingService();

    @Test
    void shouldMaskEmailPhoneAndOrder() {
        String raw = "email test@example.com, phone 010-1234-5678, order ORD-123456";

        String masked = piiMaskingService.mask(raw);

        assertThat(masked).doesNotContain("test@example.com");
        assertThat(masked).doesNotContain("010-1234-5678");
        assertThat(masked).doesNotContain("ORD-123456");
        assertThat(masked).contains("***@***");
        assertThat(masked).contains("***-****");
        assertThat(masked).contains("ORDER-***");
    }
}
