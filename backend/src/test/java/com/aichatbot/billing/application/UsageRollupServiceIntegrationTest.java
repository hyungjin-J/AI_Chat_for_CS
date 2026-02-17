package com.aichatbot.billing.application;

import com.aichatbot.billing.domain.model.CostRateCard;
import com.aichatbot.billing.domain.model.GenerationLogEntry;
import com.aichatbot.billing.domain.model.TenantDailyUsage;
import com.aichatbot.billing.domain.model.TenantMonthlyUsage;
import com.aichatbot.billing.infrastructure.GenerationLogRepository;
import com.aichatbot.billing.infrastructure.RateCardRepository;
import com.aichatbot.billing.infrastructure.TenantUsageDailyRepository;
import com.aichatbot.billing.infrastructure.TenantUsageMonthlyRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(properties = "spring.task.scheduling.enabled=false")
class UsageRollupServiceIntegrationTest {

    @Autowired
    private UsageRollupService usageRollupService;

    @Autowired
    private GenerationLogRepository generationLogRepository;

    @Autowired
    private RateCardRepository rateCardRepository;

    @Autowired
    private TenantUsageDailyRepository tenantUsageDailyRepository;

    @Autowired
    private TenantUsageMonthlyRepository tenantUsageMonthlyRepository;

    @BeforeEach
    void setUp() {
        generationLogRepository.clear();
        rateCardRepository.clear();
        tenantUsageDailyRepository.clear();
        tenantUsageMonthlyRepository.clear();

        rateCardRepository.save(new CostRateCard(
            "rate-1",
            "provider-default",
            "model-default",
            new BigDecimal("0.001"),
            new BigDecimal("0.002"),
            new BigDecimal("0.010"),
            Instant.parse("2026-01-01T00:00:00Z"),
            null
        ));
    }

    @Test
    void shouldAggregateDailyAndMonthlyUsageWithRateCardJoin() {
        generationLogRepository.save(new GenerationLogEntry(
            "g1",
            "tenant-a",
            "msg-1",
            "provider-default",
            "model-default",
            1000,
            500,
            1,
            "masked",
            "trace-a1",
            Instant.parse("2026-02-17T01:00:00Z")
        ));
        generationLogRepository.save(new GenerationLogEntry(
            "g2",
            "tenant-a",
            "msg-2",
            "provider-default",
            "model-default",
            2000,
            1000,
            2,
            "masked",
            "trace-a2",
            Instant.parse("2026-02-17T06:00:00Z")
        ));
        generationLogRepository.save(new GenerationLogEntry(
            "g3",
            "tenant-a",
            "msg-3",
            "provider-default",
            "model-default",
            1500,
            500,
            1,
            "masked",
            "trace-a3",
            Instant.parse("2026-02-18T06:00:00Z")
        ));

        usageRollupService.rollupDaily(LocalDate.of(2026, 2, 17), "trace-rollup-d1");
        usageRollupService.rollupDaily(LocalDate.of(2026, 2, 18), "trace-rollup-d2");
        usageRollupService.rollupMonthly(YearMonth.of(2026, 2), "trace-rollup-m1");

        TenantDailyUsage day1 = tenantUsageDailyRepository.findOne("tenant-a", LocalDate.of(2026, 2, 17));
        TenantDailyUsage day2 = tenantUsageDailyRepository.findOne("tenant-a", LocalDate.of(2026, 2, 18));
        TenantMonthlyUsage month = tenantUsageMonthlyRepository.findOne("tenant-a", YearMonth.of(2026, 2));

        assertThat(day1).isNotNull();
        assertThat(day1.requestCount()).isEqualTo(2);
        assertThat(day1.inputTokens()).isEqualTo(3000);
        assertThat(day1.outputTokens()).isEqualTo(1500);
        assertThat(day1.toolCalls()).isEqualTo(3);
        assertThat(day1.estimatedCost()).isEqualByComparingTo(new BigDecimal("0.036000"));
        assertThat(day1.traceId()).isEqualTo("trace-rollup-d1");

        assertThat(day2).isNotNull();
        assertThat(day2.requestCount()).isEqualTo(1);
        assertThat(day2.inputTokens()).isEqualTo(1500);
        assertThat(day2.outputTokens()).isEqualTo(500);
        assertThat(day2.toolCalls()).isEqualTo(1);
        assertThat(day2.estimatedCost()).isEqualByComparingTo(new BigDecimal("0.012500"));
        assertThat(day2.traceId()).isEqualTo("trace-rollup-d2");

        assertThat(month).isNotNull();
        assertThat(month.requestCount()).isEqualTo(3);
        assertThat(month.inputTokens()).isEqualTo(4500);
        assertThat(month.outputTokens()).isEqualTo(2000);
        assertThat(month.toolCalls()).isEqualTo(4);
        assertThat(month.estimatedCost()).isEqualByComparingTo(new BigDecimal("0.048500"));
        assertThat(month.traceId()).isEqualTo("trace-rollup-m1");
    }
}

