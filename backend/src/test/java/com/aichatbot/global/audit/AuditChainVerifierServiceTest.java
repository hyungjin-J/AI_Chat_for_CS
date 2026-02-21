package com.aichatbot.global.audit;

import com.aichatbot.global.audit.domain.PersistentAuditLogEntry;
import com.aichatbot.global.observability.TraceContext;
import com.aichatbot.ops.application.OpsEventService;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AuditChainVerifierServiceTest {

    private final AuditLogService auditLogService = mock(AuditLogService.class);
    private final OpsEventService opsEventService = mock(OpsEventService.class);
    private final Clock clock = Clock.fixed(Instant.parse("2026-03-01T12:00:00Z"), ZoneOffset.UTC);

    private AuditChainVerifierService auditChainVerifierService;

    @BeforeEach
    void setUp() {
        auditChainVerifierService = new AuditChainVerifierService(auditLogService, opsEventService, clock);
        TraceContext.setTraceId("8a8e2f7d-8d6b-4f77-bc95-7d496ea98e2a");
    }

    @AfterEach
    void tearDown() {
        TraceContext.clear();
    }

    @Test
    void shouldPassWhenChainIsConsistent() {
        UUID tenantId = UUID.fromString("10000000-0000-4000-8000-000000000001");
        PersistentAuditLogEntry first = buildEntry(
            tenantId,
            UUID.fromString("20000000-0000-4000-8000-000000000001"),
            "AUTH_LOGIN_SUCCESS",
            1L,
            "GENESIS",
            Instant.parse("2026-03-01T10:00:00Z"),
            "{\"result\":\"ok\"}"
        );
        PersistentAuditLogEntry second = buildEntry(
            tenantId,
            UUID.fromString("20000000-0000-4000-8000-000000000002"),
            "AUTH_REFRESH_SUCCESS",
            2L,
            first.hashCurr(),
            Instant.parse("2026-03-01T10:10:00Z"),
            "{\"result\":\"ok\"}"
        );

        when(auditLogService.search(eq(tenantId), any(), any(), any(), any(), any(), anyInt(), eq(0)))
            .thenReturn(List.of(second, first));

        AuditChainVerifierService.AuditChainVerificationResult result = auditChainVerifierService.verify(
            tenantId,
            Instant.parse("2026-03-01T00:00:00Z"),
            Instant.parse("2026-03-01T23:59:59Z"),
            500
        );

        assertThat(result.passed()).isTrue();
        assertThat(result.failureCount()).isZero();
        assertThat(result.checkedRows()).isEqualTo(2);
        verify(opsEventService, never()).append(any(), any(), any(), anyLong(), any());
    }

    @Test
    void shouldReportFailureAndAppendOpsEventWhenHashTampered() {
        UUID tenantId = UUID.fromString("10000000-0000-4000-8000-000000000002");
        PersistentAuditLogEntry first = buildEntry(
            tenantId,
            UUID.fromString("30000000-0000-4000-8000-000000000001"),
            "AUTH_LOGIN_SUCCESS",
            1L,
            "GENESIS",
            Instant.parse("2026-03-01T08:00:00Z"),
            "{\"result\":\"ok\"}"
        );
        PersistentAuditLogEntry tampered = new PersistentAuditLogEntry(
            UUID.fromString("40000000-0000-4000-8000-000000000002"),
            tenantId,
            UUID.fromString("30000000-0000-4000-8000-000000000002"),
            "AUTH_REFRESH_SUCCESS",
            null,
            "OPS",
            "AUTH_SESSION",
            "session-2",
            null,
            "{\"result\":\"ok\"}",
            2L,
            first.hashCurr(),
            "tampered_hash_value",
            "SHA-256",
            Instant.parse("2026-03-01T08:05:00Z")
        );

        when(auditLogService.search(eq(tenantId), any(), any(), any(), any(), any(), anyInt(), eq(0)))
            .thenReturn(List.of(first, tampered));

        AuditChainVerifierService.AuditChainVerificationResult result = auditChainVerifierService.verify(
            tenantId,
            Instant.parse("2026-03-01T00:00:00Z"),
            Instant.parse("2026-03-01T23:59:59Z"),
            500
        );

        assertThat(result.passed()).isFalse();
        assertThat(result.failureCount()).isGreaterThan(0);
        assertThat(result.failureSamples()).anyMatch(sample -> sample.contains("hash_curr_mismatch"));

        ArgumentCaptor<Map<String, Object>> dimensionsCaptor = ArgumentCaptor.forClass(Map.class);
        verify(opsEventService).append(
            eq(tenantId),
            eq("AUDIT_CHAIN_VERIFY_FAILED"),
            eq("audit_chain_verify_failed"),
            eq((long) result.failureCount()),
            dimensionsCaptor.capture()
        );
        assertThat(dimensionsCaptor.getValue()).containsKey("checked_rows");
    }

    private PersistentAuditLogEntry buildEntry(
        UUID tenantId,
        UUID traceId,
        String actionType,
        long chainSeq,
        String prevHash,
        Instant createdAt,
        String afterJson
    ) {
        String hash = computeHash(
            tenantId,
            traceId,
            actionType,
            "AUTH_SESSION",
            "session-" + chainSeq,
            null,
            afterJson,
            chainSeq,
            prevHash,
            createdAt
        );
        return new PersistentAuditLogEntry(
            UUID.fromString(String.format("40000000-0000-4000-8000-%012d", chainSeq)),
            tenantId,
            traceId,
            actionType,
            null,
            "OPS",
            "AUTH_SESSION",
            "session-" + chainSeq,
            null,
            afterJson,
            chainSeq,
            prevHash,
            hash,
            "SHA-256",
            createdAt
        );
    }

    private String computeHash(
        UUID tenantId,
        UUID traceId,
        String actionType,
        String targetType,
        String targetId,
        String beforeJson,
        String afterJson,
        long chainSeq,
        String prevHash,
        Instant createdAt
    ) {
        try {
            String payload = String.join("|",
                tenantId.toString(),
                traceId.toString(),
                safe(actionType),
                safe(targetType),
                safe(targetId),
                safe(beforeJson),
                safe(afterJson),
                String.valueOf(chainSeq),
                safe(prevHash),
                String.valueOf(createdAt.toEpochMilli())
            );
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(payload.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(digest);
        } catch (Exception exception) {
            throw new IllegalStateException(exception);
        }
    }

    private String safe(String value) {
        return value == null ? "" : value;
    }
}
