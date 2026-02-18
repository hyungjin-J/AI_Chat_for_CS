package com.aichatbot.rag.application;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class RetrievalService {

    private final List<KnowledgeChunk> knowledgeBase = List.of(
        new KnowledgeChunk(
            UUID.fromString("30000000-0000-0000-0000-000000000001"),
            "배송 지연 보상은 주문 상태와 지연 일수에 따라 환불 또는 쿠폰으로 처리합니다."
        ),
        new KnowledgeChunk(
            UUID.fromString("30000000-0000-0000-0000-000000000002"),
            "환불 접수 후 영업일 기준 3~5일 내 원결제 수단으로 환불됩니다."
        ),
        new KnowledgeChunk(
            UUID.fromString("30000000-0000-0000-0000-000000000003"),
            "상담원은 답변 전 최신 운영 가이드 버전과 정책 금지 문구를 확인해야 합니다."
        ),
        new KnowledgeChunk(
            UUID.fromString("30000000-0000-0000-0000-000000000004"),
            "개인정보는 응답 생성 전에 마스킹해야 하며 로그에 원문 저장이 금지됩니다."
        ),
        new KnowledgeChunk(
            UUID.fromString("30000000-0000-0000-0000-000000000005"),
            "Refund policy: approved refunds are returned to original payment method within 3-5 business days. 문의 이메일 refund-team@example.com"
        )
    );

    public RetrievalResult retrieve(String queryTextMasked, UUID tenantId, int topK) {
        String[] keywords = normalize(queryTextMasked).split("\\s+");
        List<EvidenceChunk> ranked = new ArrayList<>();

        for (KnowledgeChunk chunk : knowledgeBase) {
            double score = scoreChunk(keywords, normalize(chunk.text()));
            if (score > 0.0d) {
                ranked.add(new EvidenceChunk(chunk.chunkId(), chunk.text(), 0, score));
            }
        }

        ranked.sort(Comparator.comparing(EvidenceChunk::score).reversed());
        List<EvidenceChunk> selected = ranked.stream()
            .limit(Math.max(1, topK))
            .toList();

        List<EvidenceChunk> withRank = new ArrayList<>();
        for (int index = 0; index < selected.size(); index++) {
            EvidenceChunk chunk = selected.get(index);
            withRank.add(new EvidenceChunk(chunk.chunkId(), chunk.chunkTextMasked(), index + 1, chunk.score()));
        }

        double evidenceScore = withRank.isEmpty() ? 0.0d : withRank.get(0).score();
        return new RetrievalResult(withRank, "keyword_fallback", evidenceScore);
    }

    private double scoreChunk(String[] keywords, String chunkText) {
        int hits = 0;
        int nonBlankKeywords = 0;
        for (String keyword : keywords) {
            if (keyword.isBlank()) {
                continue;
            }
            nonBlankKeywords++;
            if (chunkText.contains(keyword)) {
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
            .replaceAll("[^a-z0-9가-힣\\s]", " ")
            .replaceAll("\\s+", " ")
            .trim();
    }

    private record KnowledgeChunk(UUID chunkId, String text) {
    }
}
