package com.aichatbot.global.audit;

import com.aichatbot.global.audit.domain.PersistentAuditLogEntry;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.ops.application.OpsEventService;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class AuditChainVerifierService {

    private static final int MAX_FAILURE_SAMPLES = 20;
    private static final String FAIL_EVENT_TYPE = "AUDIT_CHAIN_VERIFY_FAILED";
    private static final String FAIL_METRIC_KEY = "audit_chain_verify_failed";

    private final AuditLogService auditLogService;
    private final OpsEventService opsEventService;
    private final Clock clock;

    @Autowired
    public AuditChainVerifierService(AuditLogService auditLogService, OpsEventService opsEventService) {
        this(auditLogService, opsEventService, Clock.systemUTC());
    }

    AuditChainVerifierService(AuditLogService auditLogService, OpsEventService opsEventService, Clock clock) {
        this.auditLogService = auditLogService;
        this.opsEventService = opsEventService;
        this.clock = clock;
    }

    public AuditChainVerificationResult verify(UUID tenantId, Instant fromUtc, Instant toUtc, int limit) {
        int safeLimit = Math.max(1, Math.min(5000, limit));
        List<PersistentAuditLogEntry> entries = auditLogService.search(
            tenantId,
            fromUtc,
            toUtc,
            null,
            null,
            null,
            safeLimit,
            0
        );
        List<PersistentAuditLogEntry> ordered = entries.stream()
            .sorted(Comparator
                .comparing(PersistentAuditLogEntry::chainSeq, Comparator.nullsLast(Long::compareTo))
                .thenComparing(PersistentAuditLogEntry::createdAt))
            .toList();

        List<String> failures = new ArrayList<>();
        PersistentAuditLogEntry previous = null;
        for (PersistentAuditLogEntry entry : ordered) {
            validateEntry(entry, previous, failures);
            previous = entry;
        }

        boolean passed = failures.isEmpty();
        if (!passed) {
            opsEventService.append(
                tenantId,
                FAIL_EVENT_TYPE,
                FAIL_METRIC_KEY,
                failures.size(),
                Map.of(
                    "from_utc", safeInstant(fromUtc),
                    "to_utc", safeInstant(toUtc),
                    "checked_rows", ordered.size()
                )
            );
        }

        List<String> samples = failures.size() > MAX_FAILURE_SAMPLES
            ? failures.subList(0, MAX_FAILURE_SAMPLES)
            : failures;
        return new AuditChainVerificationResult(
            passed,
            ordered.size(),
            failures.size(),
            samples,
            TraceGuard.requireTraceId(),
            Instant.now(clock)
        );
    }

    private void validateEntry(
        PersistentAuditLogEntry current,
        PersistentAuditLogEntry previous,
        List<String> failures
    ) {
        if (current.chainSeq() == null || current.hashPrev() == null || current.hashCurr() == null) {
            failures.add("missing_chain_fields:audit_id=" + current.id());
            return;
        }
        if (previous != null) {
            long expectedSeq = previous.chainSeq() + 1L;
            if (current.chainSeq() != expectedSeq) {
                failures.add("chain_seq_gap:audit_id=" + current.id() + ",expected=" + expectedSeq + ",actual=" + current.chainSeq());
            }
            if (!Objects.equals(current.hashPrev(), previous.hashCurr())) {
                failures.add("hash_link_mismatch:audit_id=" + current.id());
            }
        }
        String expectedHash = computeHash(
            current.tenantId(),
            current.traceId(),
            current.actionType(),
            current.targetType(),
            current.targetId(),
            current.beforeJson(),
            current.afterJson(),
            current.chainSeq(),
            current.hashPrev(),
            current.createdAt()
        );
        if (!Objects.equals(expectedHash, current.hashCurr())) {
            failures.add("hash_curr_mismatch:audit_id=" + current.id());
        }
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
            throw new IllegalStateException("Failed to verify audit hash chain", exception);
        }
    }

    private String safe(String value) {
        return value == null ? "" : value;
    }

    private String safeInstant(Instant value) {
        return value == null ? "" : value.toString();
    }

    public record AuditChainVerificationResult(
        boolean passed,
        int checkedRows,
        int failureCount,
        List<String> failureSamples,
        String traceId,
        Instant verifiedAt
    ) {
    }
}
