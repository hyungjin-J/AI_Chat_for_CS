package com.aichatbot.ops.application;

import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.ops.infrastructure.OpsRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class OpsEventService {

    private static final Logger log = LoggerFactory.getLogger(OpsEventService.class);

    private static final Set<String> METRIC_KEY_ALLOWLIST = Set.of(
        "auth_login_success",
        "auth_login_failed",
        "auth_rate_limited",
        "auth_account_locked",
        "auth_account_unlocked",
        "auth_refresh_success",
        "auth_refresh_reuse_detected",
        "rbac_denied",
        "ops_block_applied",
        "audit_chain_verify_failed",
        "audit_export_requested",
        "audit_export_completed",
        "audit_export_failed",
        "audit_export_downloaded",
        "audit_export_expired",
        "scheduler_lock_recovered",
        "scheduler_lock_recovery_failed"
    );

    private final OpsRepository opsRepository;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Autowired
    public OpsEventService(OpsRepository opsRepository, ObjectMapper objectMapper) {
        this(opsRepository, objectMapper, Clock.systemUTC());
    }

    OpsEventService(OpsRepository opsRepository, ObjectMapper objectMapper, Clock clock) {
        this.opsRepository = opsRepository;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    public void append(UUID tenantId, String eventType, String metricKey, long metricValue, Map<String, Object> dimensions) {
        if (tenantId == null) {
            return;
        }
        UUID traceId = UUID.fromString(TraceGuard.requireTraceId());
        String dimensionsJson = serializeDimensions(dimensions);
        opsRepository.insertOpsEvent(
            UUID.randomUUID(),
            tenantId,
            traceId,
            Instant.now(clock),
            eventType,
            metricKey,
            metricValue,
            dimensionsJson
        );
    }

    public List<String> metricKeyAllowlist() {
        return METRIC_KEY_ALLOWLIST.stream().sorted().toList();
    }

    public boolean isAllowlistedMetricKey(String metricKey) {
        return METRIC_KEY_ALLOWLIST.contains(metricKey);
    }

    private String serializeDimensions(Map<String, Object> dimensions) {
        if (dimensions == null || dimensions.isEmpty()) {
            return "{}";
        }
        try {
            return objectMapper.writeValueAsString(dimensions);
        } catch (JsonProcessingException exception) {
            log.warn("failed to serialize ops dimensions trace_id={}", TraceGuard.requireTraceId(), exception);
            return "{}";
        }
    }
}
