package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.application.UsageRollupService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.assertj.core.api.Assertions.assertThat;

@Testcontainers(disabledWithoutDocker = true)
@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.billing.persistence.mode=mybatis"
})
class BillingParityMybatisModeIntegrationTest {

    @Container
    static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void registerProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
        registry.add("spring.datasource.driver-class-name", () -> "org.postgresql.Driver");
    }

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
    void shouldProduceDeterministicParitySnapshotInMybatisMode() {
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
