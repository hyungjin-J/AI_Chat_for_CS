package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.application.UsageRollupService;
import com.aichatbot.contexts.billing.domain.mapper.TenantUsageDailyMapper;
import com.aichatbot.contexts.billing.domain.model.CostRateCard;
import com.aichatbot.contexts.billing.domain.model.GenerationLogEntry;
import com.aichatbot.contexts.billing.domain.model.TenantDailyUsage;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
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
class BillingMapperPersistenceIntegrationTest {

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
    private UsageRollupService usageRollupService;

    @Autowired
    private TenantUsageDailyMapper tenantUsageDailyMapper;

    @AfterEach
    void cleanup() {
        tenantUsageDailyRepository.clear();
        generationLogRepository.clear();
        rateCardRepository.clear();
    }

    @Test
    void shouldPersistUsageAcrossRepositoryInstancesInMybatisMode() {
        rateCardRepository.save(new CostRateCard(
            "rate-it-1",
            "provider-default",
            "model-default",
            new BigDecimal("0.001"),
            new BigDecimal("0.002"),
            new BigDecimal("0.010"),
            Instant.parse("2026-01-01T00:00:00Z"),
            null
        ));
        generationLogRepository.save(new GenerationLogEntry(
            "it-g1",
            "tenant-a",
            "msg-1",
            "provider-default",
            "model-default",
            1000,
            500,
            1,
            "masked",
            "trace-it-1",
            Instant.parse("2026-02-17T05:00:00Z")
        ));

        LocalDate usageDate = LocalDate.of(2026, 2, 17);
        usageRollupService.rollupDaily(usageDate, "trace-rollup-it");

        TenantDailyUsage persisted = tenantUsageDailyRepository.findOne("tenant-a", usageDate);
        assertThat(persisted).isNotNull();
        assertThat(persisted.requestCount()).isEqualTo(1);

        // Why: another repository instance with the same mapper must read the same DB state (restart/multi-instance assumption).
        TenantUsageDailyRepository secondInstance = new TenantUsageDailyRepository(tenantUsageDailyMapper, "mybatis");
        TenantDailyUsage fromSecondInstance = secondInstance.findOne("tenant-a", usageDate);

        assertThat(fromSecondInstance).isNotNull();
        assertThat(fromSecondInstance.requestCount()).isEqualTo(1);
        assertThat(fromSecondInstance.inputTokens()).isEqualTo(1000);
        assertThat(fromSecondInstance.outputTokens()).isEqualTo(500);
    }
}
