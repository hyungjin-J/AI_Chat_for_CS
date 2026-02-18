package com.aichatbot.rag.presentation;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.tenant.TenantContext;
import com.aichatbot.rag.application.CitationView;
import com.aichatbot.rag.infrastructure.CitationRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
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
    public ResponseEntity<CitationListResponse> getCitations(@PathVariable("answer_id") String answerId) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UUID messageId = parseUuid(answerId);

        List<CitationView> citations = citationRepository.findByMessageId(tenantId, messageId);
        List<CitationListResponse.CitationItem> items = citations.stream()
            .map(citation -> new CitationListResponse.CitationItem(
                citation.id().toString(),
                citation.messageId().toString(),
                citation.chunkId() == null ? null : citation.chunkId().toString(),
                citation.rankNo(),
                citation.excerptMasked()
            ))
            .toList();

        CitationListResponse response = new CitationListResponse("ok", items, TraceGuard.requireTraceId());
        return ResponseEntity.ok(response);
    }

    private UUID parseUuid(String raw) {
        try {
            return UUID.fromString(raw);
        } catch (IllegalArgumentException exception) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of("answer_id_invalid")
            );
        }
    }
}
