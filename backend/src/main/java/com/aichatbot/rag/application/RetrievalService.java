package com.aichatbot.rag.application;

import com.aichatbot.global.privacy.PiiMaskingService;
import com.aichatbot.rag.infrastructure.ChunkSearchRow;
import com.aichatbot.rag.infrastructure.KbSearchRepository;
import java.time.Instant;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class RetrievalService {

    private final KbSearchRepository kbSearchRepository;
    private final RrfFusion rrfFusion;
    private final NoopReranker reranker;
    private final EvidenceSelector evidenceSelector;
    private final ChunkContextHeaderBuilder chunkContextHeaderBuilder;
    private final ExtractiveChunkSummarizer chunkSummarizer;
    private final PiiMaskingService piiMaskingService;
    private final RagRetrievalMetrics ragRetrievalMetrics;

    public RetrievalService(
        KbSearchRepository kbSearchRepository,
        RrfFusion rrfFusion,
        NoopReranker reranker,
        EvidenceSelector evidenceSelector,
        ChunkContextHeaderBuilder chunkContextHeaderBuilder,
        ExtractiveChunkSummarizer chunkSummarizer,
        PiiMaskingService piiMaskingService,
        RagRetrievalMetrics ragRetrievalMetrics
    ) {
        this.kbSearchRepository = kbSearchRepository;
        this.rrfFusion = rrfFusion;
        this.reranker = reranker;
        this.evidenceSelector = evidenceSelector;
        this.chunkContextHeaderBuilder = chunkContextHeaderBuilder;
        this.chunkSummarizer = chunkSummarizer;
        this.piiMaskingService = piiMaskingService;
        this.ragRetrievalMetrics = ragRetrievalMetrics;
    }

    public RetrievalResult retrieve(String queryTextMasked, UUID tenantId, int topK) {
        RagRetrievalRequest request = new RagRetrievalRequest(
            tenantId,
            null,
            queryTextMasked,
            topK,
            Map.of(),
            Instant.now().toString()
        );
        return retrieve(request);
    }

    public RetrievalResult retrieve(RagRetrievalRequest request) {
        long startedAt = System.currentTimeMillis();
        List<ChunkSearchRow> chunks = kbSearchRepository.findApprovedChunksByTenant(request.tenantId());
        Map<UUID, ChunkSearchRow> byChunkId = new HashMap<>();
        for (ChunkSearchRow row : chunks) {
            byChunkId.put(UUID.fromString(row.chunkId()), row);
        }

        long vectorStart = System.currentTimeMillis();
        List<RrfFusion.ScoredChunk> vectorRanked = scoreVector(request.queryMasked(), chunks);
        ragRetrievalMetrics.recordVector(System.currentTimeMillis() - vectorStart);

        long bm25Start = System.currentTimeMillis();
        List<RrfFusion.ScoredChunk> bm25Ranked = scoreBm25(request.queryMasked(), chunks);
        ragRetrievalMetrics.recordBm25(System.currentTimeMillis() - bm25Start);

        long rrfStart = System.currentTimeMillis();
        List<RrfFusion.ScoredChunk> fused = rrfFusion.fuse(vectorRanked, bm25Ranked, 60);
        ragRetrievalMetrics.recordRrf(System.currentTimeMillis() - rrfStart);

        long rerankStart = System.currentTimeMillis();
        List<RrfFusion.ScoredChunk> reranked = reranker.rerank(request.queryMasked(), fused);
        ragRetrievalMetrics.recordRerank(System.currentTimeMillis() - rerankStart);

        List<RrfFusion.ScoredChunk> selected = evidenceSelector.select(
            reranked,
            request.topK(),
            0.0d
        );
        boolean zeroEvidence = selected.isEmpty();
        ragRetrievalMetrics.recordOutcome(zeroEvidence);
        ragRetrievalMetrics.recordRagSearch(System.currentTimeMillis() - startedAt);

        List<EvidenceChunk> evidence = selected.stream()
            .map(item -> toEvidence(item, byChunkId, chunks.size()))
            .sorted(Comparator.comparing(EvidenceChunk::score).reversed())
            .toList();
        List<EvidenceChunk> ranked = rank(evidence);
        double evidenceScore = ranked.isEmpty() ? 0.0d : ranked.get(0).score();
        return new RetrievalResult(ranked, "hybrid_summary_first", evidenceScore, zeroEvidence);
    }

    private List<EvidenceChunk> rank(List<EvidenceChunk> chunks) {
        return java.util.stream.IntStream.range(0, chunks.size())
            .mapToObj(i -> {
                EvidenceChunk row = chunks.get(i);
                return new EvidenceChunk(
                    row.chunkId(),
                    row.documentId(),
                    row.title(),
                    row.versionNo(),
                    i + 1,
                    row.score(),
                    row.excerptMasked(),
                    row.originalChunkText()
                );
            }).toList();
    }

    private EvidenceChunk toEvidence(RrfFusion.ScoredChunk item, Map<UUID, ChunkSearchRow> byChunkId, int totalChunks) {
        ChunkSearchRow row = byChunkId.get(item.chunkId());
        if (row == null) {
            return new EvidenceChunk(item.chunkId(), null, "unknown", 0, 0, normalizeRrfScore(item.score()), "", "");
        }
        String contextHeader = chunkContextHeaderBuilder.build(row, totalChunks);
        String summary = chunkSummarizer.summarize(row.chunkText(), 2);
        String excerpt = piiMaskingService.mask((contextHeader + "\n" + summary).trim());
        String original = row.chunkText() == null ? "" : row.chunkText();
        return new EvidenceChunk(
            UUID.fromString(row.chunkId()),
            UUID.fromString(row.documentId()),
            row.title(),
            row.versionNo() == null ? 0 : row.versionNo(),
            0,
            normalizeRrfScore(item.score()),
            excerpt,
            original
        );
    }

    private List<RrfFusion.ScoredChunk> scoreVector(String queryMasked, List<ChunkSearchRow> chunks) {
        String[] keywords = normalize(queryMasked).split("\\s+");
        return chunks.stream()
            .map(chunk -> {
                String text = normalize(chunk.embeddingInputText());
                double score = scoreChunk(keywords, text);
                return new RrfFusion.ScoredChunk(UUID.fromString(chunk.chunkId()), score, text);
            })
            .filter(item -> item.score() > 0.0d)
            .sorted(Comparator.comparing(RrfFusion.ScoredChunk::score).reversed())
            .toList();
    }

    private List<RrfFusion.ScoredChunk> scoreBm25(String queryMasked, List<ChunkSearchRow> chunks) {
        String[] keywords = normalize(queryMasked).split("\\s+");
        return chunks.stream()
            .map(chunk -> {
                String contextHeader = chunk.contextHeader();
                if (contextHeader == null || contextHeader.isBlank()) {
                    contextHeader = chunkContextHeaderBuilder.build(chunk, chunks.size());
                }
                String summary = chunk.summaryText();
                if (summary == null || summary.isBlank()) {
                    summary = chunkSummarizer.summarize(chunk.chunkText(), 2);
                }
                String indexText = normalize(contextHeader + "\n" + summary);
                double score = scoreChunk(keywords, indexText);
                return new RrfFusion.ScoredChunk(UUID.fromString(chunk.chunkId()), score, indexText);
            })
            .filter(item -> item.score() > 0.0d)
            .sorted(Comparator.comparing(RrfFusion.ScoredChunk::score).reversed())
            .toList();
    }

    private double scoreChunk(String[] keywords, String text) {
        int hits = 0;
        int nonBlankKeywords = 0;
        for (String keyword : keywords) {
            if (keyword.isBlank()) {
                continue;
            }
            nonBlankKeywords++;
            if (text.contains(keyword)) {
                hits++;
            }
        }
        if (nonBlankKeywords == 0) {
            return 0.0d;
        }
        int effectiveDenominator = Math.max(1, Math.min(nonBlankKeywords, 5));
        return Math.min(1.0d, (double) hits / (double) effectiveDenominator);
    }

    private String normalize(String value) {
        if (value == null) {
            return "";
        }
        return value
            .toLowerCase(Locale.ROOT)
            .replaceAll("[^a-z0-9\\p{IsHangul}\\s]", " ")
            .replaceAll("\\s+", " ")
            .trim();
    }

    private double normalizeRrfScore(double rawRrfScore) {
        return Math.min(1.0d, rawRrfScore * 30.0d);
    }
}
