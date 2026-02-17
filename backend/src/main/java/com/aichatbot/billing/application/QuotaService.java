package com.aichatbot.billing.application;

import com.aichatbot.billing.domain.model.AuditLogEntry;
import com.aichatbot.billing.domain.model.BreachAction;
import com.aichatbot.billing.domain.model.TenantQuota;
import com.aichatbot.billing.infrastructure.AuditLogRepository;
import com.aichatbot.billing.infrastructure.TenantQuotaRepository;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.observability.TraceContext;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.util.Locale;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class QuotaService {

    private final TenantQuotaRepository tenantQuotaRepository;
    private final AuditLogRepository auditLogRepository;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Autowired
    public QuotaService(
        TenantQuotaRepository tenantQuotaRepository,
        AuditLogRepository auditLogRepository,
        ObjectMapper objectMapper
    ) {
        this(tenantQuotaRepository, auditLogRepository, objectMapper, Clock.systemUTC());
    }

    QuotaService(
        TenantQuotaRepository tenantQuotaRepository,
        AuditLogRepository auditLogRepository,
        ObjectMapper objectMapper,
        Clock clock
    ) {
        this.tenantQuotaRepository = tenantQuotaRepository;
        this.auditLogRepository = auditLogRepository;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    public QuotaUpsertResult upsertQuota(String tenantId, QuotaUpsertCommand command) {
        validateCommand(command);
        String traceId = requireTraceId();

        TenantQuota before = tenantQuotaRepository.findActive(tenantId, Instant.now(clock))
            .orElseGet(() -> tenantQuotaRepository.findLatest(tenantId).orElse(null));
        TenantQuota after = new TenantQuota(
            tenantId,
            command.maxQps(),
            command.maxDailyTokens(),
            command.maxMonthlyCost(),
            command.effectiveFrom(),
            command.effectiveTo(),
            command.breachAction(),
            command.actorUserId(),
            traceId,
            Instant.now(clock)
        );
        tenantQuotaRepository.upsert(after);

        AuditLogEntry auditLogEntry = new AuditLogEntry(
            UUID.randomUUID().toString(),
            tenantId,
            command.actorUserId(),
            command.actorRole(),
            "TENANT_QUOTA_UPSERT",
            "TENANT_QUOTA",
            tenantId,
            traceId,
            toJsonSafe(before),
            toJsonSafe(after),
            Instant.now(clock)
        );
        auditLogRepository.save(auditLogEntry);

        return new QuotaUpsertResult("updated", tenantId, traceId);
    }

    public BreachAction parseBreachAction(String value) {
        if (value == null || value.isBlank()) {
            return BreachAction.THROTTLE_429;
        }
        String normalized = value.trim().toUpperCase(Locale.ROOT);
        if ("BLOCK_403".equals(normalized)) {
            return BreachAction.BLOCK_403;
        }
        if ("THROTTLE_429".equals(normalized)) {
            return BreachAction.THROTTLE_429;
        }
        throw new ApiException(
            HttpStatus.UNPROCESSABLE_ENTITY,
            "OPS-102-INVALID_QUOTA",
            "Invalid breach action value"
        );
    }

    private void validateCommand(QuotaUpsertCommand command) {
        if (command.maxQps() < 0 || command.maxDailyTokens() < 0) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "OPS-102-INVALID_QUOTA",
                "Quota values must be non-negative"
            );
        }
        if (command.maxMonthlyCost() == null || command.maxMonthlyCost().compareTo(BigDecimal.ZERO) < 0) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "OPS-102-INVALID_QUOTA",
                "max_monthly_cost must be non-negative"
            );
        }
        if (command.effectiveTo() != null && !command.effectiveTo().isAfter(command.effectiveFrom())) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "OPS-102-INVALID_QUOTA",
                "effective_to must be after effective_from"
            );
        }
    }

    private String requireTraceId() {
        String traceId = TraceContext.getTraceId();
        if (traceId == null || traceId.isBlank()) {
            throw new ApiException(HttpStatus.CONFLICT, "SYS-004-409-TRACE", "trace_id is required");
        }
        return traceId;
    }

    private String toJsonSafe(Object value) {
        if (value == null) {
            return "{}";
        }
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            return "{\"serialization\":\"failed\"}";
        }
    }

    public record QuotaUpsertCommand(
        int maxQps,
        long maxDailyTokens,
        BigDecimal maxMonthlyCost,
        Instant effectiveFrom,
        Instant effectiveTo,
        BreachAction breachAction,
        String actorUserId,
        String actorRole
    ) {
    }

    public record QuotaUpsertResult(
        String result,
        String tenantId,
        String traceId
    ) {
    }
}
