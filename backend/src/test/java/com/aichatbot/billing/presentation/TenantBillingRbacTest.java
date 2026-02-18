package com.aichatbot.billing.presentation;

import com.aichatbot.billing.domain.model.BreachAction;
import com.aichatbot.billing.domain.model.TenantDailyUsage;
import com.aichatbot.billing.domain.model.TenantMonthlyUsage;
import com.aichatbot.billing.infrastructure.AuditLogRepository;
import com.aichatbot.billing.infrastructure.TenantQuotaRepository;
import com.aichatbot.billing.infrastructure.TenantUsageDailyRepository;
import com.aichatbot.billing.infrastructure.TenantUsageMonthlyRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "spring.task.scheduling.enabled=false")
@AutoConfigureMockMvc
class TenantBillingRbacTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private TenantUsageDailyRepository tenantUsageDailyRepository;

    @Autowired
    private TenantUsageMonthlyRepository tenantUsageMonthlyRepository;

    @Autowired
    private TenantQuotaRepository tenantQuotaRepository;

    @Autowired
    private AuditLogRepository auditLogRepository;

    @BeforeEach
    void setUp() {
        tenantUsageDailyRepository.clear();
        tenantUsageMonthlyRepository.clear();
        tenantQuotaRepository.clear();
        auditLogRepository.clear();

        tenantUsageDailyRepository.save(new TenantDailyUsage(
            "tenant-a",
            LocalDate.of(2026, 2, 17),
            10L,
            1000L,
            800L,
            3L,
            new BigDecimal("1.230000"),
            "99999999-9999-4999-8999-999999999999",
            Instant.parse("2026-02-17T10:00:00Z")
        ));
        tenantUsageMonthlyRepository.save(new TenantMonthlyUsage(
            "tenant-a",
            YearMonth.of(2026, 2),
            40L,
            7000L,
            5000L,
            20L,
            new BigDecimal("8.990000"),
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            Instant.parse("2026-02-17T10:00:00Z")
        ));
    }

    @Test
    void opsCanReadUsageReport() throws Exception {
        String traceReadOps = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
        mockMvc.perform(get("/v1/admin/tenants/tenant-a/usage-report")
                .header("X-Trace-Id", traceReadOps)
                .header("X-Tenant-Key", "tenant-a")
                .header("X-User-Id", "ops-user")
                .header("X-User-Role", "OPS"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.tenant_id").value("tenant-a"))
            .andExpect(jsonPath("$.trace_id").value(traceReadOps));
    }

    @Test
    void opsCannotUpsertQuota() throws Exception {
        String traceWriteOps = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
        String body = """
            {
              "max_qps": 20,
              "max_daily_tokens": 100000,
              "max_monthly_cost": 500.0,
              "effective_from": "2026-03-01T00:00:00Z",
              "breach_action": "THROTTLE_429"
            }
            """;
        mockMvc.perform(put("/v1/admin/tenants/tenant-a/quota")
                .header("X-Trace-Id", traceWriteOps)
                .header("X-Tenant-Key", "tenant-a")
                .header("X-User-Id", "ops-user")
                .header("X-User-Role", "OPS")
                .header("Idempotency-Key", "idem-ops")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.error_code").value("SEC-002-403"));
    }

    @Test
    void adminCanUpsertQuotaAndAuditIsWritten() throws Exception {
        String traceWriteAdmin = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
        String body = """
            {
              "max_qps": 50,
              "max_daily_tokens": 200000,
              "max_monthly_cost": 900.5,
              "effective_from": "2026-03-01T00:00:00Z",
              "breach_action": "BLOCK_403"
            }
            """;
        mockMvc.perform(put("/v1/admin/tenants/tenant-a/quota")
                .header("X-Trace-Id", traceWriteAdmin)
                .header("X-Tenant-Key", "tenant-a")
                .header("X-User-Id", "admin-user")
                .header("X-User-Role", "ADMIN")
                .header("Idempotency-Key", "idem-admin")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body))
            .andExpect(status().isOk())
            .andExpect(header().string("X-Trace-Id", traceWriteAdmin))
            .andExpect(jsonPath("$.result").value("updated"))
            .andExpect(jsonPath("$.tenant_id").value("tenant-a"))
            .andExpect(jsonPath("$.trace_id").value(traceWriteAdmin));

        assertThat(tenantQuotaRepository.findLatest("tenant-a")).isPresent();
        assertThat(tenantQuotaRepository.findLatest("tenant-a").get().breachAction()).isEqualTo(BreachAction.BLOCK_403);
        assertThat(auditLogRepository.findByTenant("tenant-a")).hasSize(1);
        assertThat(auditLogRepository.findByTenant("tenant-a").get(0).actorUserId()).isEqualTo("admin-user");
        assertThat(auditLogRepository.findByTenant("tenant-a").get(0).traceId()).isEqualTo(traceWriteAdmin);
    }
}
