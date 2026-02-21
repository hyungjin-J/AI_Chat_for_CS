package com.aichatbot.global.audit;

import com.aichatbot.global.audit.domain.AuditExportChunkRecord;
import com.aichatbot.global.audit.domain.AuditExportJobRecord;
import com.aichatbot.global.audit.domain.PersistentAuditLogEntry;
import com.aichatbot.global.audit.export.ExportStorage;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.observability.TraceContext;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.ops.application.OpsEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuditExportJobService {

    private static final int DEFAULT_TTL_HOURS = 24;
    private static final int DEFAULT_ROW_LIMIT = 1000;
    private static final int MAX_ROW_LIMIT = 5000;
    private static final int DEFAULT_MAX_BYTES = 3 * 1024 * 1024;
    private static final int MAX_MAX_BYTES = 10 * 1024 * 1024;
    private static final int DEFAULT_MAX_DURATION_SECONDS = 30;
    private static final int MAX_MAX_DURATION_SECONDS = 120;

    private final PersistentAuditLogRepository auditLogRepository;
    private final AuditLogService auditLogService;
    private final AuditSanitizer auditSanitizer;
    private final ExportStorage exportStorage;
    private final OpsEventService opsEventService;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Autowired
    public AuditExportJobService(
        PersistentAuditLogRepository auditLogRepository,
        AuditLogService auditLogService,
        AuditSanitizer auditSanitizer,
        ExportStorage exportStorage,
        OpsEventService opsEventService,
        ObjectMapper objectMapper
    ) {
        this(
            auditLogRepository,
            auditLogService,
            auditSanitizer,
            exportStorage,
            opsEventService,
            objectMapper,
            Clock.systemUTC()
        );
    }

    AuditExportJobService(
        PersistentAuditLogRepository auditLogRepository,
        AuditLogService auditLogService,
        AuditSanitizer auditSanitizer,
        ExportStorage exportStorage,
        OpsEventService opsEventService,
        ObjectMapper objectMapper,
        Clock clock
    ) {
        this.auditLogRepository = auditLogRepository;
        this.auditLogService = auditLogService;
        this.auditSanitizer = auditSanitizer;
        this.exportStorage = exportStorage;
        this.opsEventService = opsEventService;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    @Transactional
    public AuditExportJobRecord createJob(
        UUID tenantId,
        UUID requestedBy,
        String format,
        Instant fromUtc,
        Instant toUtc,
        Integer rowLimit,
        Integer maxBytes,
        Integer maxDurationSec
    ) {
        validateRange(fromUtc, toUtc);
        String normalizedFormat = normalizeFormat(format);
        int safeRowLimit = normalizeBounded(rowLimit, DEFAULT_ROW_LIMIT, 1, MAX_ROW_LIMIT);
        int safeMaxBytes = normalizeBounded(maxBytes, DEFAULT_MAX_BYTES, 1024, MAX_MAX_BYTES);
        int safeMaxDuration = normalizeBounded(maxDurationSec, DEFAULT_MAX_DURATION_SECONDS, 5, MAX_MAX_DURATION_SECONDS);

        UUID jobId = UUID.randomUUID();
        Instant now = Instant.now(clock);
        Instant expiresAt = now.plus(DEFAULT_TTL_HOURS, ChronoUnit.HOURS);
        UUID traceId = UUID.fromString(TraceGuard.requireTraceId());
        auditLogRepository.insertExportJob(
            jobId,
            tenantId,
            requestedBy,
            "PENDING",
            normalizedFormat,
            fromUtc,
            toUtc,
            safeRowLimit,
            safeMaxBytes,
            safeMaxDuration,
            expiresAt,
            traceId,
            now
        );

        opsEventService.append(
            tenantId,
            "AUDIT_EXPORT_REQUESTED",
            "audit_export_requested",
            1L,
            Map.of("job_id", jobId.toString(), "format", normalizedFormat)
        );
        auditLogService.write(
            tenantId,
            "AUDIT_EXPORT_REQUESTED",
            requestedBy,
            "OPS",
            "AUDIT_EXPORT_JOB",
            jobId.toString(),
            null,
            Map.of(
                "format", normalizedFormat,
                "from_utc", safeInstant(fromUtc),
                "to_utc", safeInstant(toUtc),
                "row_limit", safeRowLimit
            )
        );

        return findById(tenantId, jobId);
    }

    public AuditExportJobRecord findById(UUID tenantId, UUID jobId) {
        return auditLogRepository.findExportJobById(tenantId, jobId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Audit export job not found"));
    }

    public DownloadPayload download(UUID tenantId, UUID jobId, UUID requestedBy) {
        AuditExportJobRecord job = findById(tenantId, jobId);
        Instant now = Instant.now(clock);
        if (job.expiresAt() != null && job.expiresAt().isBefore(now)) {
            expire(job, now);
            throw new ApiException(
                HttpStatus.CONFLICT,
                "AUDIT_EXPORT_JOB_EXPIRED",
                "Audit export job has expired",
                List.of("job_expired")
            );
        }
        if (!"DONE".equals(job.status())) {
            throw new ApiException(
                HttpStatus.CONFLICT,
                "AUDIT_EXPORT_JOB_NOT_READY",
                "Audit export job is not ready",
                List.of("job_not_ready")
            );
        }

        List<AuditExportChunkRecord> chunks = exportStorage.readChunks(job.id());
        if (chunks.isEmpty()) {
            throw new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Audit export payload not found");
        }
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        for (AuditExportChunkRecord chunk : chunks) {
            output.writeBytes(chunk.payloadBytes());
        }
        byte[] payload = output.toByteArray();

        opsEventService.append(
            tenantId,
            "AUDIT_EXPORT_DOWNLOADED",
            "audit_export_downloaded",
            1L,
            Map.of("job_id", job.id().toString(), "bytes", payload.length)
        );
        auditLogService.write(
            tenantId,
            "AUDIT_EXPORT_DOWNLOADED",
            requestedBy,
            "OPS",
            "AUDIT_EXPORT_JOB",
            job.id().toString(),
            null,
            Map.of("bytes", payload.length)
        );

        return new DownloadPayload(job, payload);
    }

    @Transactional
    public int processPendingJobs(int limit) {
        Instant now = Instant.now(clock);
        List<AuditExportJobRecord> jobs = auditLogRepository.findPendingExportJobs(now, Math.max(1, limit));
        int processed = 0;
        for (AuditExportJobRecord job : jobs) {
            if (!auditLogRepository.claimExportJob(job.id(), now)) {
                continue;
            }
            processed++;
            processClaimedJob(job.id());
        }
        return processed;
    }

    @Transactional
    public int cleanupExpiredJobs(int limit) {
        Instant now = Instant.now(clock);
        List<AuditExportJobRecord> jobs = auditLogRepository.findJobsToExpire(now, Math.max(1, limit));
        int expiredCount = 0;
        String previousTraceId = TraceContext.getTraceId();
        if (previousTraceId == null || previousTraceId.isBlank()) {
            TraceContext.setTraceId(UUID.randomUUID().toString());
        }
        for (AuditExportJobRecord job : jobs) {
            if (expire(job, now)) {
                expiredCount++;
            }
        }
        if (previousTraceId == null || previousTraceId.isBlank()) {
            TraceContext.clear();
        } else {
            TraceContext.setTraceId(previousTraceId);
        }
        return expiredCount;
    }

    @Transactional
    public void processClaimedJob(UUID jobId) {
        AuditExportJobRecord fresh = auditLogRepository.findExportJobByIdForAnyTenant(jobId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Audit export job not found"));
        String previousTraceId = TraceContext.getTraceId();
        TraceContext.setTraceId(UUID.randomUUID().toString());
        Instant started = Instant.now(clock);
        try {
            List<PersistentAuditLogEntry> entries = auditLogService.search(
                fresh.tenantId(),
                fresh.fromUtc(),
                fresh.toUtc(),
                null,
                null,
                null,
                fresh.rowLimit(),
                0
            );
            String payload = "csv".equals(fresh.exportFormat())
                ? toCsv(entries)
                : toJson(entries);
            byte[] bytes = payload.getBytes(StandardCharsets.UTF_8);
            if (bytes.length > fresh.maxBytes()) {
                recordExportFailure(
                    fresh,
                    "AUDIT_EXPORT_RANGE_EXCEEDED",
                    "Export payload size exceeds max_bytes",
                    "max_bytes_exceeded"
                );
                return;
            }
            if (ChronoUnit.SECONDS.between(started, Instant.now(clock)) > fresh.maxDurationSec()) {
                recordExportFailure(
                    fresh,
                    "AUDIT_EXPORT_TIMEOUT",
                    "Export processing exceeded max_duration_sec",
                    "max_duration_exceeded"
                );
                return;
            }

            exportStorage.storeChunk(fresh.id(), 1, bytes, sha256Hex(bytes), Instant.now(clock));
            auditLogRepository.markExportJobDone(fresh.id(), entries.size(), bytes.length, Instant.now(clock));
            opsEventService.append(
                fresh.tenantId(),
                "AUDIT_EXPORT_COMPLETED",
                "audit_export_completed",
                1L,
                Map.of("job_id", fresh.id().toString(), "rows", entries.size(), "bytes", bytes.length)
            );
            auditLogService.write(
                fresh.tenantId(),
                "AUDIT_EXPORT_COMPLETED",
                null,
                "SYSTEM",
                "AUDIT_EXPORT_JOB",
                fresh.id().toString(),
                null,
                Map.of("row_count", entries.size(), "total_bytes", bytes.length)
            );
        } catch (Exception exception) {
            recordExportFailure(
                fresh,
                "AUDIT_EXPORT_PROCESSING_FAILED",
                truncate(exception.getMessage(), 400),
                "exception"
            );
        } finally {
            if (previousTraceId == null || previousTraceId.isBlank()) {
                TraceContext.clear();
            } else {
                TraceContext.setTraceId(previousTraceId);
            }
        }
    }

    private boolean expire(AuditExportJobRecord job, Instant now) {
        boolean updated = auditLogRepository.markExportJobExpired(job.id(), now);
        if (!updated) {
            return false;
        }
        exportStorage.expireJobPayload(job.id());
        opsEventService.append(
            job.tenantId(),
            "AUDIT_EXPORT_EXPIRED",
            "audit_export_expired",
            1L,
            Map.of("job_id", job.id().toString())
        );
        auditLogService.write(
            job.tenantId(),
            "AUDIT_EXPORT_EXPIRED",
            null,
            "SYSTEM",
            "AUDIT_EXPORT_JOB",
            job.id().toString(),
            null,
            Map.of("expired_at", now.toString())
        );
        return true;
    }

    private void recordExportFailure(
        AuditExportJobRecord job,
        String errorCode,
        String errorMessage,
        String reason
    ) {
        auditLogRepository.markExportJobFailed(
            job.id(),
            errorCode,
            errorMessage,
            Instant.now(clock)
        );
        opsEventService.append(
            job.tenantId(),
            "AUDIT_EXPORT_FAILED",
            "audit_export_failed",
            1L,
            Map.of("job_id", job.id().toString(), "reason", reason, "error_code", errorCode)
        );
        auditLogService.write(
            job.tenantId(),
            "AUDIT_EXPORT_FAILED",
            job.requestedBy(),
            "OPS",
            "AUDIT_EXPORT_JOB",
            job.id().toString(),
            null,
            Map.of("error_code", errorCode, "reason", reason)
        );
    }

    private void validateRange(Instant fromUtc, Instant toUtc) {
        if (fromUtc != null && toUtc != null && fromUtc.isAfter(toUtc)) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "AUDIT_EXPORT_RANGE_EXCEEDED",
                "from_utc must be before to_utc",
                List.of("invalid_time_range")
            );
        }
        if (fromUtc != null && toUtc != null && ChronoUnit.DAYS.between(fromUtc, toUtc) > 31) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "AUDIT_EXPORT_RANGE_EXCEEDED",
                "Audit export range must be 31 days or less",
                List.of("range_exceeded")
            );
        }
    }

    private int normalizeBounded(Integer raw, int fallback, int min, int max) {
        int value = raw == null ? fallback : raw;
        return Math.max(min, Math.min(max, value));
    }

    private String normalizeFormat(String format) {
        String normalized = format == null ? "json" : format.trim().toLowerCase();
        if (!normalized.equals("json") && !normalized.equals("csv")) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                "format must be json or csv",
                List.of("invalid_format")
            );
        }
        return normalized;
    }

    private String toJson(List<PersistentAuditLogEntry> entries) {
        ArrayNode arrayNode = objectMapper.createArrayNode();
        for (PersistentAuditLogEntry entry : entries) {
            ObjectNode item = objectMapper.createObjectNode();
            item.put("audit_id", entry.id().toString());
            item.put("action_type", entry.actionType());
            item.put("trace_id", entry.traceId().toString());
            item.put("created_at", entry.createdAt().toString());
            item.put("target_type", entry.targetType());
            item.put("target_id", entry.targetId());
            item.put("chain_seq", entry.chainSeq() == null ? 0 : entry.chainSeq());
            item.put("before_json", reSanitize(entry.beforeJson()));
            item.put("after_json", reSanitize(entry.afterJson()));
            arrayNode.add(item);
        }
        return arrayNode.toString();
    }

    private String toCsv(List<PersistentAuditLogEntry> entries) {
        StringBuilder builder = new StringBuilder();
        builder.append("audit_id,action_type,actor_user_id,trace_id,created_at,target_type,target_id,chain_seq").append("\n");
        for (PersistentAuditLogEntry entry : entries) {
            builder.append(entry.id()).append(",")
                .append(csv(entry.actionType())).append(",")
                .append(entry.actorUserId() == null ? "" : entry.actorUserId()).append(",")
                .append(entry.traceId()).append(",")
                .append(entry.createdAt()).append(",")
                .append(csv(entry.targetType())).append(",")
                .append(csv(entry.targetId())).append(",")
                .append(entry.chainSeq() == null ? "" : entry.chainSeq())
                .append("\n");
        }
        return builder.toString();
    }

    private String reSanitize(String rawJson) {
        if (rawJson == null || rawJson.isBlank()) {
            return "{}";
        }
        try {
            Object parsed = objectMapper.readValue(rawJson, Object.class);
            return auditSanitizer.sanitize(parsed);
        } catch (Exception ignored) {
            return auditSanitizer.sanitize(rawJson);
        }
    }

    private String csv(String value) {
        if (value == null) {
            return "";
        }
        String escaped = value.replace("\"", "\"\"");
        return "\"" + escaped + "\"";
    }

    private String sha256Hex(byte[] bytes) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder builder = new StringBuilder(digest.length * 2);
            for (byte single : digest) {
                builder.append(String.format("%02x", single));
            }
            return builder.toString();
        } catch (Exception exception) {
            throw new IllegalStateException("Failed to hash export payload", exception);
        }
    }

    private String truncate(String value, int maxLength) {
        if (value == null) {
            return "";
        }
        if (value.length() <= maxLength) {
            return value;
        }
        return value.substring(0, maxLength);
    }

    private String safeInstant(Instant instant) {
        return instant == null ? "" : instant.toString();
    }

    public record DownloadPayload(
        AuditExportJobRecord job,
        byte[] payload
    ) {
    }
}
