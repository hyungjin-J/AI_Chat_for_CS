package com.aichatbot.global.audit;

import com.aichatbot.global.audit.domain.AuditChainState;
import com.aichatbot.global.audit.domain.PersistentAuditLogEntry;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.security.PrincipalUtils;
import com.aichatbot.global.security.UserPrincipal;
import com.aichatbot.global.tenant.TenantContext;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuditLogService {

    private final PersistentAuditLogRepository auditLogRepository;
    private final AuditSanitizer auditSanitizer;
    private final Clock clock;

    @Autowired
    public AuditLogService(PersistentAuditLogRepository auditLogRepository, AuditSanitizer auditSanitizer) {
        this(auditLogRepository, auditSanitizer, Clock.systemUTC());
    }

    AuditLogService(PersistentAuditLogRepository auditLogRepository, AuditSanitizer auditSanitizer, Clock clock) {
        this.auditLogRepository = auditLogRepository;
        this.auditSanitizer = auditSanitizer;
        this.clock = clock;
    }

    @Transactional
    public void write(
        UUID tenantId,
        String actionType,
        UUID actorUserId,
        String actorRole,
        String targetType,
        String targetId,
        Object beforePayload,
        Object afterPayload
    ) {
        UUID traceId = UUID.fromString(TraceGuard.requireTraceId());
        Instant createdAt = Instant.now(clock);
        String sanitizedBefore = auditSanitizer.sanitize(beforePayload);
        String sanitizedAfter = auditSanitizer.sanitize(afterPayload);
        AuditChainState chainState = auditLogRepository.lockChainState(tenantId)
            .orElseGet(() -> {
                auditLogRepository.insertChainState(tenantId, 0L, "GENESIS", createdAt);
                return new AuditChainState(tenantId, 0L, "GENESIS");
            });
        long nextSeq = chainState.lastSeq() + 1L;
        String prevHash = chainState.lastHash() == null ? "GENESIS" : chainState.lastHash();
        String nextHash = computeHash(tenantId, traceId, actionType, targetType, targetId, sanitizedBefore, sanitizedAfter, nextSeq, prevHash, createdAt);

        PersistentAuditLogEntry entry = new PersistentAuditLogEntry(
            UUID.randomUUID(),
            tenantId,
            traceId,
            actionType,
            actorUserId,
            actorRole,
            targetType,
            targetId,
            sanitizedBefore,
            sanitizedAfter,
            nextSeq,
            prevHash,
            nextHash,
            "SHA-256",
            createdAt
        );
        auditLogRepository.insert(entry);
        auditLogRepository.updateChainState(tenantId, nextSeq, nextHash, createdAt);
    }

    public void writeForCurrentUser(
        UUID tenantId,
        String actionType,
        String targetType,
        String targetId,
        Object beforePayload,
        Object afterPayload
    ) {
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID actorUserId = toUuidOrNull(principal.userId());
        write(
            tenantId,
            actionType,
            actorUserId,
            String.join(",", principal.roles()),
            targetType,
            targetId,
            beforePayload,
            afterPayload
        );
    }

    public List<PersistentAuditLogEntry> search(
        UUID tenantId,
        Instant fromUtc,
        Instant toUtc,
        UUID actorUserId,
        String actionType,
        UUID traceId,
        int limit,
        int offset
    ) {
        return auditLogRepository.search(tenantId, fromUtc, toUtc, actorUserId, actionType, traceId, limit, offset);
    }

    public Optional<PersistentAuditLogEntry> findById(UUID auditId) {
        return auditLogRepository.findById(auditId);
    }

    public void writeExportLog(UUID tenantId, UUID requestedBy, String format, Instant fromUtc, Instant toUtc, int rowCount) {
        UUID traceId = UUID.fromString(TraceGuard.requireTraceId());
        auditLogRepository.insertExportLog(UUID.randomUUID(), tenantId, requestedBy, format, fromUtc, toUtc, rowCount, traceId);
    }

    public UUID tenantIdFromContext() {
        return UUID.fromString(TenantContext.getTenantId());
    }

    public static UUID toUuidOrNull(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return null;
        }
        try {
            return UUID.fromString(rawValue);
        } catch (IllegalArgumentException ignored) {
            return null;
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
            throw new IllegalStateException("Failed to compute audit hash chain", exception);
        }
    }

    private String safe(String value) {
        return value == null ? "" : value;
    }
}
