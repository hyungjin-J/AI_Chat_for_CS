package com.aichatbot.auth.presentation;

import com.aichatbot.auth.application.AuthRateLimitService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock"
})
@AutoConfigureMockMvc
class AuthRateLimitPriorityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AuthRateLimitService authRateLimitService;

    @BeforeEach
    void setUp() {
        Mockito.when(authRateLimitService.consumeLoginAttempt(Mockito.anyString(), Mockito.anyString()))
            .thenReturn(new AuthRateLimitService.RateLimitDecision(
                false,
                1L,
                0L,
                9999999999L,
                30L
            ));
    }

    @Test
    void shouldReturnAuthRateLimitedBeforeLockoutEvaluation() throws Exception {
        mockMvc.perform(post("/v1/auth/login")
                .header("X-Trace-Id", "84000000-0000-4000-8000-000000000001")
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-rate-priority")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "login_id":"agent1",
                      "password":"wrong-pass",
                      "client_type":"web",
                      "client_nonce":"nonce-rate"
                    }
                    """))
            .andExpect(status().isTooManyRequests())
            .andExpect(jsonPath("$.error_code").value("AUTH_RATE_LIMITED"))
            .andExpect(header().string("Retry-After", "30"));
    }
}

