package com.aichatbot.contexts.operations.presentation;

import com.aichatbot.contexts.operations.application.BackofficeAdminService;
import com.aichatbot.platform.observability.TraceGuard;
import com.aichatbot.platform.tenancy.TenantContext;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/internal")
public class InternalOpsController {

    private final BackofficeAdminService backofficeAdminService;

    public InternalOpsController(BackofficeAdminService backofficeAdminService) {
        this.backofficeAdminService = backofficeAdminService;
    }

    @PostMapping("/events/ingest")
    public ResponseEntity<EventIngestResponse> ingestEvent(@RequestBody(required = false) EventIngestRequest request) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        backofficeAdminService.ingestEvent(
            tenantId,
            request == null ? null : request.eventType(),
            request == null ? null : request.metricKey(),
            request == null ? 1L : request.metricValue(),
            request == null ? Map.of() : (request.dimensions() == null ? Map.of() : request.dimensions())
        );
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(new EventIngestResponse("accepted", TraceGuard.requireTraceId()));
    }

    @PostMapping("/tools/execute")
    public ToolExecuteResponse executeTool(@RequestBody(required = false) ToolExecuteRequest request) {
        String toolName = request == null || request.toolName() == null ? "unknown_tool" : request.toolName();
        return new ToolExecuteResponse("ok", toolName, "executed", TraceGuard.requireTraceId());
    }

    @PostMapping("/tools/validate")
    public ToolValidateResponse validateTool(@RequestBody(required = false) ToolValidateRequest request) {
        boolean valid = request != null && request.toolName() != null && !request.toolName().isBlank();
        return new ToolValidateResponse(valid ? "ok" : "invalid", valid, TraceGuard.requireTraceId());
    }

    public record EventIngestRequest(
        String eventType,
        String metricKey,
        long metricValue,
        Map<String, Object> dimensions
    ) {
    }

    public record EventIngestResponse(
        String result,
        String traceId
    ) {
    }

    public record ToolExecuteRequest(
        String toolName,
        Map<String, Object> payload
    ) {
    }

    public record ToolExecuteResponse(
        String result,
        String toolName,
        String status,
        String traceId
    ) {
    }

    public record ToolValidateRequest(
        String toolName
    ) {
    }

    public record ToolValidateResponse(
        String result,
        boolean valid,
        String traceId
    ) {
    }
}
