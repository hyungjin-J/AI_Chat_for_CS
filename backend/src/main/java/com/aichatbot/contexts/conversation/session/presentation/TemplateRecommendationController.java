package com.aichatbot.contexts.conversation.session.presentation;

import com.aichatbot.contexts.operations.application.BackofficeAdminService;
import com.aichatbot.platform.observability.TraceGuard;
import com.aichatbot.platform.tenancy.TenantContext;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/sessions/{session_id}")
public class TemplateRecommendationController {

    private final BackofficeAdminService backofficeAdminService;

    public TemplateRecommendationController(BackofficeAdminService backofficeAdminService) {
        this.backofficeAdminService = backofficeAdminService;
    }

    @PostMapping("/template-recommendations")
    public TemplateRecommendationResponse recommendTemplates(
        @PathVariable("session_id") String sessionId,
        @RequestBody(required = false) TemplateRecommendationRequest request
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        List<TemplateRecommendationItem> items = backofficeAdminService.listTemplates(tenantId, 3, 0).stream()
            .map(row -> new TemplateRecommendationItem(row.resourceKey(), row.status(), row.activeFlag()))
            .toList();
        return new TemplateRecommendationResponse(
            sessionId,
            request == null ? null : request.query(),
            items,
            TraceGuard.requireTraceId()
        );
    }

    public record TemplateRecommendationRequest(
        String query
    ) {
    }

    public record TemplateRecommendationItem(
        String templateId,
        String status,
        boolean active
    ) {
    }

    public record TemplateRecommendationResponse(
        String sessionId,
        String query,
        List<TemplateRecommendationItem> items,
        String traceId
    ) {
    }
}
