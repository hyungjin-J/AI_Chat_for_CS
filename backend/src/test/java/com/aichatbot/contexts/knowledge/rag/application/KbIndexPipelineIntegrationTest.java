package com.aichatbot.contexts.knowledge.rag.application;

import com.aichatbot.contexts.knowledge.rag.domain.model.KbDocumentAdminRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbReindexJobRow;
import com.aichatbot.contexts.knowledge.rag.infrastructure.KbAdminRepository;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockReset;
import org.springframework.boot.test.mock.mockito.SpyBean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0"
})
class KbIndexPipelineIntegrationTest {

    private static final UUID TENANT_ID = UUID.fromString("00000000-0000-0000-0000-000000000001");

    @Autowired
    private KbAdminService kbAdminService;

    @Autowired
    private KbAdminRepository kbAdminRepository;

    @Autowired
    private KbIndexPipelineService kbIndexPipelineService;

    @SpyBean(reset = MockReset.AFTER)
    private DefaultKbDocumentParser kbDocumentParser;

    @SpyBean(reset = MockReset.AFTER)
    private DeterministicKbEmbeddingGenerator kbEmbeddingGenerator;

    @SpyBean(reset = MockReset.AFTER)
    private NoopKbSearchIndexer kbSearchIndexer;

    @Test
    void shouldProcessLargeDocumentVersionAndPersistChunks() {
        String raw = buildLargeContent();
        KbAdminService.KbDocumentView created = createQueuedDocument(raw, "idem-kb-pipeline-success");

        int processed = kbIndexPipelineService.processPendingJobs(20);
        assertThat(processed).isGreaterThan(0);

        KbReindexJobRow job = kbAdminRepository.findReindexJobById(TENANT_ID, created.indexJobId()).orElseThrow();
        assertThat(job.status()).isEqualTo(KbAdminRepository.JOB_STATUS_DONE);
        assertThat(job.resultMessage()).contains("indexed_chunks=");

        KbDocumentAdminRow document = kbAdminRepository.findDocumentById(TENANT_ID, created.documentId()).orElseThrow();
        assertThat(document.pipelineStatus()).isEqualTo("INDEXED");
        assertThat(document.pipelineErrorCode()).isNull();

        int chunkCount = kbAdminRepository.countChunksByDocumentVersion(TENANT_ID, created.documentVersionId());
        assertThat(chunkCount).isGreaterThan(1);
    }

    @Test
    void shouldReuseReindexJobForSameIdempotencyKey() {
        KbAdminService.KbReindexJobView first = kbAdminService.requestReindex(
            TENANT_ID,
            null,
            "nightly_reindex",
            "idem-kb-reindex-stable",
            UUID.randomUUID()
        );
        KbAdminService.KbReindexJobView second = kbAdminService.requestReindex(
            TENANT_ID,
            null,
            "nightly_reindex_retry",
            "idem-kb-reindex-stable",
            UUID.randomUUID()
        );

        assertThat(second.jobId()).isEqualTo(first.jobId());
        assertThat(second.idempotencyKey()).isEqualTo("idem-kb-reindex-stable");
    }

    @Test
    void shouldMoveJobToDeadLetterAfterParserFailures() {
        doThrow(new KbIndexingStageException("KB-INDEX-PARSER-422", "parser_failed", true))
            .when(kbDocumentParser)
            .parseMaskedContent(anyString());

        KbAdminService.KbDocumentView created = createQueuedDocument("parser failure content", "idem-kb-parser-fail");
        runAttemptUntilDeadLetter(created.indexJobId());

        KbReindexJobRow job = kbAdminRepository.findReindexJobById(TENANT_ID, created.indexJobId()).orElseThrow();
        assertThat(job.status()).isEqualTo(KbAdminRepository.JOB_STATUS_DEAD_LETTER);
        assertThat(job.errorCode()).isEqualTo("KB-INDEX-PARSER-422");

        KbDocumentAdminRow document = kbAdminRepository.findDocumentById(TENANT_ID, created.documentId()).orElseThrow();
        assertThat(document.pipelineStatus()).isEqualTo("FAILED");
        assertThat(document.pipelineErrorCode()).isEqualTo("KB-INDEX-PARSER-422");
    }

    @Test
    void shouldMoveJobToDeadLetterAfterEmbeddingFailures() {
        doThrow(new KbIndexingStageException("KB-INDEX-EMBED-500", "embedding_failed", false))
            .when(kbEmbeddingGenerator)
            .generateEmbeddingVector(anyString());

        KbAdminService.KbDocumentView created = createQueuedDocument("embedding failure content", "idem-kb-embed-fail");
        runAttemptUntilDeadLetter(created.indexJobId());

        KbReindexJobRow job = kbAdminRepository.findReindexJobById(TENANT_ID, created.indexJobId()).orElseThrow();
        assertThat(job.status()).isEqualTo(KbAdminRepository.JOB_STATUS_DEAD_LETTER);
        assertThat(job.errorCode()).isEqualTo("KB-INDEX-EMBED-500");
    }

    @Test
    void shouldMoveJobToDeadLetterAfterSearchIndexerFailures() {
        doThrow(new KbIndexingStageException("KB-INDEX-SEARCH-503", "search_unavailable", false))
            .when(kbSearchIndexer)
            .verifyWritable(any(UUID.class), any(UUID.class));

        KbAdminService.KbDocumentView created = createQueuedDocument("search failure content", "idem-kb-search-fail");
        runAttemptUntilDeadLetter(created.indexJobId());

        KbReindexJobRow job = kbAdminRepository.findReindexJobById(TENANT_ID, created.indexJobId()).orElseThrow();
        assertThat(job.status()).isEqualTo(KbAdminRepository.JOB_STATUS_DEAD_LETTER);
        assertThat(job.errorCode()).isEqualTo("KB-INDEX-SEARCH-503");
    }

    private KbAdminService.KbDocumentView createQueuedDocument(String rawContent, String idempotencyKey) {
        return kbAdminService.createDocument(
            TENANT_ID,
            "kb_pipeline_document",
            "manual",
            "cs",
            LocalDate.of(2026, 3, 2),
            "ops-team",
            rawContent,
            idempotencyKey,
            UUID.randomUUID()
        );
    }

    private void runAttemptUntilDeadLetter(UUID jobId) {
        for (int attempt = 1; attempt <= KbAdminRepository.DEFAULT_MAX_ATTEMPTS; attempt++) {
            UUID traceId = UUID.randomUUID();
            boolean claimed = kbAdminRepository.claimIndexJob(
                TENANT_ID,
                jobId,
                Instant.now().plusSeconds(attempt * 300L),
                traceId
            );
            assertThat(claimed).isTrue();
            kbIndexPipelineService.processClaimedJob(TENANT_ID, jobId, traceId);
        }
    }

    private String buildLargeContent() {
        String paragraph = "refund policy details remain grounded in approved evidence and masked customer context. ";
        return (paragraph.repeat(20) + "\n\n" + paragraph.repeat(20)).trim();
    }
}
