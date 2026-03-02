package com.aichatbot.contexts.operations.presentation;

import com.aichatbot.platform.observability.TraceGuard;
import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/integrations/crm")
public class IntegrationController {

    @PostMapping("/handoffs")
    public ResponseEntity<HandoffSyncResponse> syncHandoff(@RequestBody(required = false) HandoffSyncRequest request) {
        HandoffSyncResponse response = new HandoffSyncResponse(
            UUID.randomUUID().toString(),
            request == null ? null : request.externalCaseId(),
            "accepted",
            Instant.now(),
            TraceGuard.requireTraceId()
        );
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(response);
    }

    public record HandoffSyncRequest(
        @NotBlank
        String externalCaseId,
        String payload
    ) {
    }

    public record HandoffSyncResponse(
        String handoffId,
        String externalCaseId,
        String status,
        Instant acceptedAt,
        String traceId
    ) {
    }
}
