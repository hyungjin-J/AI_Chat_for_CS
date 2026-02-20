package com.aichatbot.rag.presentation;

import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.tenant.TenantContext;
import com.aichatbot.global.util.UuidParser;
import com.aichatbot.rag.application.CitationView;
import com.aichatbot.rag.infrastructure.CitationRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/rag/answers")
public class CitationController {

    private final CitationRepository citationRepository;

    public CitationController(CitationRepository citationRepository) {
        this.citationRepository = citationRepository;
    }

    @GetMapping("/{answer_id}/citations")
    public ResponseEntity<CitationListResponse> getCitations(
        @PathVariable("answer_id") String answerId,
        @RequestParam(value = "cursor", required = false) Integer cursor,
        @RequestParam(value = "limit", required = false) Integer limit
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UUID messageId = UuidParser.parseRequired(answerId, "answer_id");
        int safeLimit = limit == null ? 20 : Math.max(1, Math.min(limit, 100));

        List<CitationView> citations = citationRepository.findByMessageId(tenantId, messageId, cursor, safeLimit);
        List<CitationListResponse.CitationItem> items = citations.stream()
            .map(citation -> new CitationListResponse.CitationItem(
                citation.id().toString(),
                citation.messageId().toString(),
                citation.chunkId() == null ? null : citation.chunkId().toString(),
                citation.rankNo(),
                citation.excerptMasked()
            ))
            .toList();

        String nextCursor = citations.size() == safeLimit
            ? String.valueOf(citations.get(citations.size() - 1).rankNo())
            : null;
        CitationListResponse response = new CitationListResponse("ok", items, nextCursor, TraceGuard.requireTraceId());
        return ResponseEntity.ok(response);
    }
}
