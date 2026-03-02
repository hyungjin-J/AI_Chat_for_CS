package com.aichatbot.contexts.knowledge.rag.application;

import com.aichatbot.contexts.knowledge.rag.domain.model.ChunkSearchRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbDocumentVersionSourceRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbReindexJobRow;
import com.aichatbot.contexts.operations.application.OpsEventService;
import com.aichatbot.contexts.operations.audit.AuditLogService;
import com.aichatbot.platform.observability.TraceContext;
import com.aichatbot.platform.privacy.PiiMaskingService;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class KbIndexPipelineService {

    private static final Logger log = LoggerFactory.getLogger(KbIndexPipelineService.class);

    private static final String PIPELINE_RUNNING = "RUNNING";
    private static final String PIPELINE_INDEXED = "INDEXED";
    private static final String PIPELINE_RETRY_WAIT = "RETRY_WAIT";
    private static final String PIPELINE_FAILED = "FAILED";
    private static final int RETRY_BACKOFF_BASE_SECONDS = 5;
    private static final int RETRY_BACKOFF_MAX_SECONDS = 300;

    private final KbAdminPort kbAdminRepository;
    private final DefaultKbDocumentParser kbDocumentParser;
    private final DeterministicKbEmbeddingGenerator kbEmbeddingGenerator;
    private final NoopKbSearchIndexer kbSearchIndexer;
    private final ChunkContextHeaderBuilder chunkContextHeaderBuilder;
    private final ExtractiveChunkSummarizer extractiveChunkSummarizer;
    private final PiiMaskingService piiMaskingService;
    private final KbIndexPipelineMetrics kbIndexPipelineMetrics;
    private final OpsEventService opsEventService;
    private final AuditLogService auditLogService;
    private final Clock clock;

    @Autowired
    public KbIndexPipelineService(
        KbAdminPort kbAdminRepository,
        DefaultKbDocumentParser kbDocumentParser,
        DeterministicKbEmbeddingGenerator kbEmbeddingGenerator,
        NoopKbSearchIndexer kbSearchIndexer,
        ChunkContextHeaderBuilder chunkContextHeaderBuilder,
        ExtractiveChunkSummarizer extractiveChunkSummarizer,
        PiiMaskingService piiMaskingService,
        KbIndexPipelineMetrics kbIndexPipelineMetrics,
        OpsEventService opsEventService,
        AuditLogService auditLogService
    ) {
        this(
            kbAdminRepository,
            kbDocumentParser,
            kbEmbeddingGenerator,
            kbSearchIndexer,
            chunkContextHeaderBuilder,
            extractiveChunkSummarizer,
            piiMaskingService,
            kbIndexPipelineMetrics,
            opsEventService,
            auditLogService,
            Clock.systemUTC()
        );
    }

    KbIndexPipelineService(
        KbAdminPort kbAdminRepository,
        DefaultKbDocumentParser kbDocumentParser,
        DeterministicKbEmbeddingGenerator kbEmbeddingGenerator,
        NoopKbSearchIndexer kbSearchIndexer,
        ChunkContextHeaderBuilder chunkContextHeaderBuilder,
        ExtractiveChunkSummarizer extractiveChunkSummarizer,
        PiiMaskingService piiMaskingService,
        KbIndexPipelineMetrics kbIndexPipelineMetrics,
        OpsEventService opsEventService,
        AuditLogService auditLogService,
        Clock clock
    ) {
        this.kbAdminRepository = kbAdminRepository;
        this.kbDocumentParser = kbDocumentParser;
        this.kbEmbeddingGenerator = kbEmbeddingGenerator;
        this.kbSearchIndexer = kbSearchIndexer;
        this.chunkContextHeaderBuilder = chunkContextHeaderBuilder;
        this.extractiveChunkSummarizer = extractiveChunkSummarizer;
        this.piiMaskingService = piiMaskingService;
        this.kbIndexPipelineMetrics = kbIndexPipelineMetrics;
        this.opsEventService = opsEventService;
        this.auditLogService = auditLogService;
        this.clock = clock;
    }

    @Transactional
    public int processPendingJobs(int limit) {
        Instant nowUtc = Instant.now(clock);
        List<KbReindexJobRow> jobs = kbAdminRepository.findPendingIndexJobs(nowUtc, Math.max(1, limit));
        int processed = 0;
        for (KbReindexJobRow job : jobs) {
            UUID traceId = UUID.randomUUID();
            boolean claimed = kbAdminRepository.claimIndexJob(job.tenantId(), job.id(), nowUtc, traceId);
            if (!claimed) {
                continue;
            }
            processed++;
            processClaimedJob(job.tenantId(), job.id(), traceId);
        }
        return processed;
    }

    @Transactional
    public void processClaimedJob(UUID tenantId, UUID jobId, UUID traceId) {
        KbReindexJobRow job = kbAdminRepository.findReindexJobById(tenantId, jobId).orElse(null);
        if (job == null || !KbAdminPort.JOB_STATUS_RUNNING.equalsIgnoreCase(job.status())) {
            return;
        }

        long startedAt = System.currentTimeMillis();
        String previousTraceId = TraceContext.getTraceId();
        TraceContext.setTraceId(traceId.toString());
        try {
            String resultMessage = processByJobType(job);
            Instant completedAt = Instant.now(clock);
            kbAdminRepository.markIndexJobDone(tenantId, jobId, completedAt, truncate(resultMessage, 400));
            kbIndexPipelineMetrics.recordSuccess(System.currentTimeMillis() - startedAt);

            Map<String, Object> dimensions = new HashMap<>();
            dimensions.put("job_id", job.id().toString());
            dimensions.put("job_type", job.jobType());
            dimensions.put("status", KbAdminPort.JOB_STATUS_DONE);
            opsEventService.append(
                tenantId,
                "KB_INDEX_JOB_DONE",
                "kb_index_latency_ms",
                Math.max(0L, System.currentTimeMillis() - startedAt),
                dimensions
            );
            auditLogService.write(
                tenantId,
                "KB_INDEX_JOB_DONE",
                null,
                "SYSTEM",
                "KB_INDEX_JOB",
                job.id().toString(),
                null,
                Map.of(
                    "job_type", job.jobType(),
                    "attempt_count", safeInt(job.attemptCount(), 0),
                    "result", truncate(resultMessage, 200)
                )
            );
        } catch (Exception exception) {
            handleFailure(job, traceId, startedAt, exception);
        } finally {
            restoreTraceContext(previousTraceId);
        }
    }

    private String processByJobType(KbReindexJobRow job) {
        if (KbAdminPort.JOB_TYPE_REINDEX_ALL.equalsIgnoreCase(job.jobType())) {
            return processReindexAll(job.tenantId());
        }
        if (KbAdminPort.JOB_TYPE_DOCUMENT_VERSION.equalsIgnoreCase(job.jobType())) {
            if (job.documentVersionId() == null) {
                throw new KbIndexingStageException("KB-INDEX-JOB-422", "document_version_id is required", false);
            }
            return processDocumentVersion(job.tenantId(), job.documentVersionId());
        }
        throw new KbIndexingStageException("KB-INDEX-JOB-422", "unsupported job type: " + job.jobType(), false);
    }

    private String processReindexAll(UUID tenantId) {
        List<UUID> approvedVersionIds = kbAdminRepository.findApprovedDocumentVersionIds(tenantId);
        if (approvedVersionIds.isEmpty()) {
            return "reindex_skipped_no_approved_versions";
        }

        int succeeded = 0;
        int failed = 0;
        int totalChunks = 0;
        Exception firstFailure = null;
        for (UUID documentVersionId : approvedVersionIds) {
            try {
                String result = processDocumentVersion(tenantId, documentVersionId);
                int chunks = parseChunkCount(result);
                totalChunks += Math.max(0, chunks);
                succeeded++;
            } catch (Exception exception) {
                failed++;
                if (firstFailure == null) {
                    firstFailure = exception;
                }
            }
        }
        if (succeeded == 0 && firstFailure != null) {
            throw new KbIndexingStageException(
                resolveErrorCode(firstFailure),
                "reindex_all_failed_for_all_versions",
                firstFailure instanceof KbIndexingStageException stageException && stageException.parserError(),
                firstFailure
            );
        }
        return "reindexed_versions=" + succeeded + ";failed_versions=" + failed + ";chunks=" + totalChunks;
    }

    private String processDocumentVersion(UUID tenantId, UUID documentVersionId) {
        KbDocumentVersionSourceRow source = kbAdminRepository.findDocumentVersionSourceForIndexing(tenantId, documentVersionId)
            .orElseThrow(() -> new KbIndexingStageException("KB-INDEX-DOC-404", "document version not found", false));

        Instant nowUtc = Instant.now(clock);
        kbAdminRepository.updateDocumentVersionPipelineState(
            tenantId,
            documentVersionId,
            PIPELINE_RUNNING,
            null,
            null,
            nowUtc
        );
        try {
            kbSearchIndexer.verifyWritable(tenantId, documentVersionId);

            List<String> parsedChunks = kbDocumentParser.parseMaskedContent(source.rawContentMasked());
            kbAdminRepository.deleteChunksAndEmbeddings(tenantId, documentVersionId);

            int totalChunks = parsedChunks.size();
            for (int index = 0; index < totalChunks; index++) {
                int chunkNo = index + 1;
                String maskedChunk = piiMaskingService.mask(parsedChunks.get(index));
                String contextHeader = buildContextHeader(source, chunkNo, totalChunks, maskedChunk);
                String summary = extractiveChunkSummarizer.summarize(maskedChunk, 2);
                String embeddingInput = piiMaskingService.mask((contextHeader + "\n" + summary).trim());
                String embeddingVector = kbEmbeddingGenerator.generateEmbeddingVector(embeddingInput);
                UUID chunkId = kbAdminRepository.insertChunk(
                    tenantId,
                    documentVersionId,
                    chunkNo,
                    sha256Hex(maskedChunk),
                    maskedChunk,
                    tokenCount(maskedChunk),
                    contextHeader,
                    summary,
                    nowUtc
                );
                kbAdminRepository.insertChunkEmbedding(
                    tenantId,
                    chunkId,
                    embeddingVector,
                    1536,
                    "kb-indexer-v1",
                    embeddingInput,
                    nowUtc
                );
            }

            kbAdminRepository.updateDocumentVersionPipelineState(
                tenantId,
                documentVersionId,
                PIPELINE_INDEXED,
                null,
                null,
                Instant.now(clock)
            );
            return "indexed_chunks=" + totalChunks + ";document_version_id=" + documentVersionId;
        } catch (Exception exception) {
            kbAdminRepository.updateDocumentVersionPipelineState(
                tenantId,
                documentVersionId,
                PIPELINE_FAILED,
                resolveErrorCode(exception),
                sanitizeErrorExcerpt(exception.getMessage()),
                Instant.now(clock)
            );
            throw exception;
        }
    }

    private void handleFailure(KbReindexJobRow job, UUID traceId, long startedAt, Exception exception) {
        Instant nowUtc = Instant.now(clock);
        String errorCode = resolveErrorCode(exception);
        String errorExcerpt = sanitizeErrorExcerpt(exception.getMessage());
        int attemptCount = safeInt(job.attemptCount(), 1);
        int maxAttempts = safeInt(job.maxAttempts(), KbAdminPort.DEFAULT_MAX_ATTEMPTS);
        boolean parserError = exception instanceof KbIndexingStageException stageException && stageException.parserError();

        if (attemptCount < maxAttempts) {
            Instant nextRetryAt = nowUtc.plusSeconds(computeBackoffSeconds(attemptCount));
            kbAdminRepository.markIndexJobRetry(
                job.tenantId(),
                job.id(),
                nextRetryAt,
                errorCode,
                errorExcerpt,
                nowUtc,
                traceId
            );
            if (job.documentVersionId() != null) {
                kbAdminRepository.updateDocumentVersionPipelineState(
                    job.tenantId(),
                    job.documentVersionId(),
                    PIPELINE_RETRY_WAIT,
                    errorCode,
                    errorExcerpt,
                    nowUtc
                );
            }
            auditLogService.write(
                job.tenantId(),
                "KB_INDEX_JOB_RETRY_SCHEDULED",
                null,
                "SYSTEM",
                "KB_INDEX_JOB",
                job.id().toString(),
                null,
                Map.of(
                    "error_code", errorCode,
                    "attempt_count", attemptCount,
                    "next_retry_at", nextRetryAt.toString()
                )
            );
        } else {
            kbAdminRepository.markIndexJobDeadLetter(
                job.tenantId(),
                job.id(),
                errorCode,
                errorExcerpt,
                nowUtc,
                traceId
            );
            if (job.documentVersionId() != null) {
                kbAdminRepository.updateDocumentVersionPipelineState(
                    job.tenantId(),
                    job.documentVersionId(),
                    PIPELINE_FAILED,
                    errorCode,
                    errorExcerpt,
                    nowUtc
                );
            }
            auditLogService.write(
                job.tenantId(),
                "KB_INDEX_JOB_DEAD_LETTER",
                null,
                "SYSTEM",
                "KB_INDEX_JOB",
                job.id().toString(),
                null,
                Map.of(
                    "error_code", errorCode,
                    "attempt_count", attemptCount
                )
            );
        }

        kbIndexPipelineMetrics.recordFailure(System.currentTimeMillis() - startedAt, parserError);
        Map<String, Object> dimensions = new HashMap<>();
        dimensions.put("job_id", job.id().toString());
        dimensions.put("job_type", job.jobType());
        dimensions.put("error_code", errorCode);
        dimensions.put("attempt_count", attemptCount);
        opsEventService.append(
            job.tenantId(),
            "KB_INDEX_JOB_FAILED",
            "kb_index_fail_rate",
            1L,
            dimensions
        );
        if (parserError) {
            opsEventService.append(
                job.tenantId(),
                "KB_INDEX_PARSER_FAILED",
                "parser_error_rate",
                1L,
                Map.of("job_id", job.id().toString(), "error_code", errorCode)
            );
        }

        log.warn(
            "kb index job failed tenant_id={} job_id={} job_type={} error_code={} attempt_count={} max_attempts={} trace_id={}",
            job.tenantId(),
            job.id(),
            job.jobType(),
            errorCode,
            attemptCount,
            maxAttempts,
            traceId
        );
    }

    private String buildContextHeader(
        KbDocumentVersionSourceRow source,
        int chunkNo,
        int totalChunks,
        String chunkText
    ) {
        ChunkSearchRow row = new ChunkSearchRow(
            UUID.randomUUID().toString(),
            source.documentId().toString(),
            source.documentVersionId().toString(),
            source.versionNo(),
            chunkNo,
            source.title(),
            source.sourceType(),
            source.category(),
            source.effectiveDate() == null ? "" : source.effectiveDate().toString(),
            source.owner(),
            null,
            null,
            chunkText,
            null
        );
        return chunkContextHeaderBuilder.build(row, totalChunks);
    }

    private int parseChunkCount(String resultMessage) {
        if (resultMessage == null || resultMessage.isBlank()) {
            return 0;
        }
        int index = resultMessage.indexOf("indexed_chunks=");
        if (index < 0) {
            return 0;
        }
        int start = index + "indexed_chunks=".length();
        int end = resultMessage.indexOf(';', start);
        String token = end < 0 ? resultMessage.substring(start) : resultMessage.substring(start, end);
        try {
            return Integer.parseInt(token.trim());
        } catch (NumberFormatException ignored) {
            return 0;
        }
    }

    private void restoreTraceContext(String previousTraceId) {
        if (previousTraceId == null || previousTraceId.isBlank()) {
            TraceContext.clear();
        } else {
            TraceContext.setTraceId(previousTraceId);
        }
    }

    private String resolveErrorCode(Exception exception) {
        if (exception instanceof KbIndexingStageException stageException) {
            return stageException.errorCode();
        }
        return "KB-INDEX-500";
    }

    private int safeInt(Integer value, int fallback) {
        if (value == null || value < 0) {
            return fallback;
        }
        return value;
    }

    private long computeBackoffSeconds(int attemptCount) {
        int safeAttempt = Math.max(1, attemptCount);
        long value = (long) RETRY_BACKOFF_BASE_SECONDS * (1L << Math.min(10, safeAttempt - 1));
        return Math.min(RETRY_BACKOFF_MAX_SECONDS, value);
    }

    private int tokenCount(String value) {
        if (value == null || value.isBlank()) {
            return 0;
        }
        return value.trim().split("\\s+").length;
    }

    private String sanitizeErrorExcerpt(String rawValue) {
        String masked = piiMaskingService.mask(rawValue == null ? "" : rawValue);
        return truncate(masked.replaceAll("\\s+", " ").trim(), 480);
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

    private String sha256Hex(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                .digest((value == null ? "" : value).getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(digest.length * 2);
            for (byte item : digest) {
                builder.append(String.format("%02x", item));
            }
            return builder.toString();
        } catch (Exception exception) {
            throw new KbIndexingStageException("KB-INDEX-HASH-500", "hash generation failed", false, exception);
        }
    }
}
