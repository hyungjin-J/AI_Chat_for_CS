package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.application.UsageRollupService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.billing.persistence.mode=memory"
})
class BillingParityMemoryModeTest {

    @Autowired
    private GenerationLogRepository generationLogRepository;

    @Autowired
    private RateCardRepository rateCardRepository;

    @Autowired
    private TenantUsageDailyRepository tenantUsageDailyRepository;

    @Autowired
    private TenantUsageMonthlyRepository tenantUsageMonthlyRepository;

    @Autowired
    private UsageRollupService usageRollupService;

    @AfterEach
    void cleanup() {
        BillingParityScenarioRunner.clear(
            generationLogRepository,
            rateCardRepository,
            tenantUsageDailyRepository,
            tenantUsageMonthlyRepository
        );
    }

    @Test
    void shouldProduceDeterministicParitySnapshotInMemoryMode() {
        BillingParityScenarioRunner.Snapshot snapshot = BillingParityScenarioRunner.run(
            generationLogRepository,
            rateCardRepository,
            tenantUsageDailyRepository,
            tenantUsageMonthlyRepository,
            usageRollupService
        );
        assertThat(snapshot).isEqualTo(BillingParityScenarioRunner.expected());
    }
}
