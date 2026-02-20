package com.aichatbot.rag.presentation;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.privacy.PiiMaskingService;
import com.aichatbot.global.tenant.TenantContext;
import com.aichatbot.rag.application.RagAnswerService;
import com.aichatbot.rag.application.RagIdempotencyRegistry;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/rag")
public class RagController {

    private final RagIdempotencyRegistry ragIdempotencyRegistry;
    private final RagAnswerService ragAnswerService;
    private final AppProperties appProperties;
    private final PiiMaskingService piiMaskingService;

    public RagController(
        RagIdempotencyRegistry ragIdempotencyRegistry,
        RagAnswerService ragAnswerService,
        AppProperties appProperties,
        PiiMaskingService piiMaskingService
    ) {
        this.ragIdempotencyRegistry = ragIdempotencyRegistry;
        this.ragAnswerService = ragAnswerService;
        this.appProperties = appProperties;
        this.piiMaskingService = piiMaskingService;
    }

    @PostMapping("/retrieve")
    public ResponseEntity<RagAcceptedResponse> retrieve(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody RagRetrieveRequest request
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        String traceId = TraceGuard.requireTraceId();
        String key = requireIdempotencyKey(idempotencyKey);
        validateQuery(request.query());
        UUID retrieveId = UUID.fromString(ragIdempotencyRegistry.getOrCreate(
            "rag:retrieve:" + tenantId,
            key,
            () -> UUID.randomUUID().toString()
        ));
        ragAnswerService.retrieveAndStore(
            retrieveId,
            tenantId,
            null,
            request.query(),
            sanitizeTopK(request.topK()),
            request.filters() == null ? Map.of() : request.filters(),
            traceId
        );

        RagAcceptedResponse response = new RagAcceptedResponse("accepted", retrieveId.toString(), traceId);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/answer")
    public ResponseEntity<?> answer(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody RagAnswerRequest request
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        String traceId = TraceGuard.requireTraceId();
        String key = requireIdempotencyKey(idempotencyKey);
        validateQuery(request.query());
        UUID answerId = UUID.fromString(ragIdempotencyRegistry.getOrCreate(
            "rag:answer:" + tenantId,
            key,
            () -> UUID.randomUUID().toString()
        ));

        RagAnswerService.RagAnswerOutcome outcome = ragAnswerService.answer(
            answerId,
            tenantId,
            null,
            request.query(),
            sanitizeTopK(request.topK()),
            request.filters() == null ? Map.of() : request.filters(),
            traceId
        );

        if (outcome.safeResponse()) {
            return ResponseEntity.ok(new RagSafeResponse(
                "safe",
                answerId.toString(),
                outcome.safeMessage(),
                traceId
            ));
        }
        return ResponseEntity.status(HttpStatus.ACCEPTED)
            .body(new RagAcceptedResponse("accepted", answerId.toString(), traceId));
    }

    private String requireIdempotencyKey(String idempotencyKey) {
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of("idempotency_key_required")
            );
        }
        return idempotencyKey.trim();
    }

    private int sanitizeTopK(Integer requestedTopK) {
        int defaultTopK = appProperties.getRag().getTopKDefault();
        int maxTopK = appProperties.getRag().getTopKMax();
        int value = requestedTopK == null ? defaultTopK : requestedTopK;
        return Math.max(1, Math.min(maxTopK, value));
    }

    private void validateQuery(String rawQuery) {
        String masked = piiMaskingService.mask(rawQuery);
        if (masked == null || masked.isBlank()) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of("query_required")
            );
        }
        if (masked.length() > 1000) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of("query_too_long")
            );
        }
    }
}
