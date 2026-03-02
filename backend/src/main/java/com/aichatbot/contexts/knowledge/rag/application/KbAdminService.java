package com.aichatbot.contexts.knowledge.rag.application;

import com.aichatbot.contexts.knowledge.rag.domain.model.KbDocumentAdminRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbReindexJobRow;
import com.aichatbot.platform.error.ApiException;
import com.aichatbot.platform.error.ErrorCatalog;
import com.aichatbot.platform.privacy.PiiMaskingService;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class KbAdminService {

    private static final String PIPELINE_INDEXED = "INDEXED";

    private final KbAdminPort kbAdminRepository;
    private final PiiMaskingService piiMaskingService;
    private final Clock clock;

    @Autowired
    public KbAdminService(KbAdminPort kbAdminRepository, PiiMaskingService piiMaskingService) {
        this(kbAdminRepository, piiMaskingService, Clock.systemUTC());
    }

    KbAdminService(KbAdminPort kbAdminRepository, PiiMaskingService piiMaskingService, Clock clock) {
        this.kbAdminRepository = kbAdminRepository;
        this.piiMaskingService = piiMaskingService;
        this.clock = clock;
    }

    public KbDocumentView createDocument(
        UUID tenantId,
        String title,
        String sourceType,
        String category,
        LocalDate effectiveDate,
        String owner,
        String rawContent,
        String idempotencyKey,
        UUID traceId
    ) {
        Instant nowUtc = Instant.now(clock);
        String safeTitle = piiMaskingService.mask(normalize(title, "untitled_document"));
        String safeOwner = piiMaskingService.mask(normalize(owner, "unknown_owner"));
        String safeSourceType = normalize(sourceType, "manual");
        String safeCategory = normalize(category, "general");
        String safeRawContent = piiMaskingService.mask(normalize(
            rawContent,
            safeTitle + "\n" + safeSourceType + "\n" + safeCategory
        ));

        KbAdminPort.DocumentCreateResult created = kbAdminRepository.createDocument(
            tenantId,
            safeTitle,
            safeSourceType,
            safeCategory,
            effectiveDate,
            safeOwner,
            safeRawContent,
            normalizeNullable(idempotencyKey),
            traceId,
            nowUtc
        );

        return kbAdminRepository.findDocumentById(tenantId, created.documentId())
            .map(row -> toDocumentView(row, created.jobId()))
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Document was not found"));
    }

    public List<KbDocumentView> listDocuments(UUID tenantId, String status, int limit, int offset) {
        int safeLimit = Math.max(1, Math.min(200, limit));
        int safeOffset = Math.max(0, offset);
        return kbAdminRepository.findLatestDocuments(tenantId, normalizeNullable(status), safeLimit, safeOffset)
            .stream()
            .map(row -> toDocumentView(row, null))
            .toList();
    }

    public KbDocumentView approveDocument(UUID tenantId, UUID documentId) {
        KbDocumentAdminRow latestVersion = kbAdminRepository.findDocumentById(tenantId, documentId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Document was not found"));
        assertIndexedVersionOrFail(latestVersion);

        int updated = kbAdminRepository.approveLatestVersion(tenantId, documentId, Instant.now(clock));
        if (updated == 0) {
            throw new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Document was not found");
        }
        return kbAdminRepository.findDocumentById(tenantId, documentId)
            .map(row -> toDocumentView(row, null))
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Document was not found"));
    }

    public KbDocumentView rollbackDocument(UUID tenantId, UUID documentId, int versionNo) {
        KbDocumentAdminRow targetVersion = kbAdminRepository.findDocumentVersionByNo(tenantId, documentId, versionNo)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Document version was not found"));
        assertIndexedVersionOrFail(targetVersion);

        int updated = kbAdminRepository.rollbackToVersion(tenantId, documentId, versionNo, Instant.now(clock));
        if (updated == 0) {
            throw new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Document version was not found");
        }
        return kbAdminRepository.findDocumentById(tenantId, documentId)
            .map(row -> toDocumentView(row, null))
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Document was not found"));
    }

    public KbReindexJobView requestReindex(
        UUID tenantId,
        UUID actorUserId,
        String note,
        String idempotencyKey,
        UUID traceId
    ) {
        Instant nowUtc = Instant.now(clock);
        String safeNote = piiMaskingService.mask(normalize(note, "manual_reindex"));
        KbReindexJobRow job = kbAdminRepository.createOrGetReindexJob(
            tenantId,
            actorUserId,
            safeNote,
            normalizeNullable(idempotencyKey),
            traceId,
            nowUtc
        );
        return toReindexJobView(job);
    }

    public KbReindexJobView getReindexStatus(UUID tenantId, UUID jobId) {
        return kbAdminRepository.findReindexJobById(tenantId, jobId)
            .map(this::toReindexJobView)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Reindex job was not found"));
    }

    public List<KbReindexJobView> listIndexOperations(UUID tenantId, int limit) {
        int safeLimit = Math.max(1, Math.min(200, limit));
        return kbAdminRepository.findRecentReindexJobs(tenantId, safeLimit)
            .stream()
            .map(this::toReindexJobView)
            .toList();
    }

    private void assertIndexedVersionOrFail(KbDocumentAdminRow row) {
        if (!PIPELINE_INDEXED.equalsIgnoreCase(normalize(row.pipelineStatus(), ""))) {
            throw new ApiException(
                HttpStatus.CONFLICT,
                "API-003-409",
                ErrorCatalog.messageOf("API-003-409"),
                List.of("document_version_not_indexed")
            );
        }
    }

    private KbDocumentView toDocumentView(KbDocumentAdminRow row, UUID indexJobId) {
        return new KbDocumentView(
            row.documentId(),
            row.documentVersionId(),
            row.title(),
            row.sourceType(),
            row.category(),
            row.effectiveDate(),
            row.owner(),
            row.versionNo(),
            row.status(),
            row.pipelineStatus(),
            row.pipelineErrorCode(),
            row.pipelineErrorExcerpt(),
            row.approvedAt(),
            row.updatedAt(),
            indexJobId
        );
    }

    private KbReindexJobView toReindexJobView(KbReindexJobRow row) {
        return new KbReindexJobView(
            row.id(),
            row.jobType(),
            row.documentVersionId(),
            row.idempotencyKey(),
            row.status(),
            row.attemptCount(),
            row.maxAttempts(),
            row.nextRetryAt(),
            row.errorCode(),
            row.errorExcerpt(),
            row.requestedBy(),
            row.requestedAt(),
            row.startedAt(),
            row.completedAt(),
            row.resultMessage(),
            row.lastTraceId()
        );
    }

    private String normalize(String rawValue, String fallback) {
        if (rawValue == null || rawValue.isBlank()) {
            return fallback;
        }
        return rawValue.trim();
    }

    private String normalizeNullable(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return null;
        }
        return rawValue.trim();
    }

    public record KbDocumentView(
        UUID documentId,
        UUID documentVersionId,
        String title,
        String sourceType,
        String category,
        LocalDate effectiveDate,
        String owner,
        int versionNo,
        String status,
        String pipelineStatus,
        String pipelineErrorCode,
        String pipelineErrorExcerpt,
        Instant approvedAt,
        Instant updatedAt,
        UUID indexJobId
    ) {
    }

    public record KbReindexJobView(
        UUID jobId,
        String jobType,
        UUID documentVersionId,
        String idempotencyKey,
        String status,
        Integer attemptCount,
        Integer maxAttempts,
        Instant nextRetryAt,
        String errorCode,
        String errorExcerpt,
        UUID requestedBy,
        Instant requestedAt,
        Instant startedAt,
        Instant completedAt,
        String resultMessage,
        UUID lastTraceId
    ) {
    }
}
