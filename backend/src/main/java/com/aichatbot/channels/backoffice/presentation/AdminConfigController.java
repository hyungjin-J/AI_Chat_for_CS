package com.aichatbot.channels.backoffice.presentation;

import com.aichatbot.contexts.identity.security.PrincipalUtils;
import com.aichatbot.contexts.identity.security.UserPrincipal;
import com.aichatbot.contexts.operations.application.BackofficeAdminService;
import com.aichatbot.contexts.operations.audit.AuditLogService;
import com.aichatbot.platform.observability.TraceGuard;
import com.aichatbot.platform.tenancy.TenantContext;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/admin")
public class AdminConfigController {

    private final BackofficeAdminService backofficeAdminService;
    private final AuditLogService auditLogService;

    public AdminConfigController(BackofficeAdminService backofficeAdminService, AuditLogService auditLogService) {
        this.backofficeAdminService = backofficeAdminService;
        this.auditLogService = auditLogService;
    }

    @GetMapping("/templates")
    public ResourceListResponse listTemplates(
        @RequestParam(value = "limit", defaultValue = "50") int limit,
        @RequestParam(value = "offset", defaultValue = "0") int offset
    ) {
        UUID tenantId = currentTenantId();
        List<ResourceResponse> items = backofficeAdminService.listTemplates(tenantId, limit, offset).stream()
            .map(this::toResourceResponse)
            .toList();
        return new ResourceListResponse(items, TraceGuard.requireTraceId());
    }

    @PostMapping("/templates")
    public ResponseEntity<ResourceResponse> createTemplate(@Valid @RequestBody TemplateCreateRequest request) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView created = backofficeAdminService.createTemplate(
            tenantId,
            actorUserId,
            request.name(),
            request.body()
        );
        writeAudit(tenantId, actorUserId, "TEMPLATE_CREATED", "TEMPLATE", created.resourceKey(), request);
        return ResponseEntity.status(HttpStatus.CREATED).body(toResourceResponse(created));
    }

    @PostMapping("/templates/{template_id}/approve")
    public ResourceResponse approveTemplate(@PathVariable("template_id") String templateId) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.approveTemplate(tenantId, actorUserId, templateId);
        writeAudit(tenantId, actorUserId, "TEMPLATE_APPROVED", "TEMPLATE", templateId, null);
        return toResourceResponse(updated);
    }

    @PostMapping("/templates/{template_id}/deploy")
    public ResourceResponse deployTemplate(@PathVariable("template_id") String templateId) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.deployTemplate(tenantId, actorUserId, templateId);
        writeAudit(tenantId, actorUserId, "TEMPLATE_DEPLOYED", "TEMPLATE", templateId, null);
        return toResourceResponse(updated);
    }

    @PostMapping("/templates/{template_id}/rollback")
    public ResourceResponse rollbackTemplate(@PathVariable("template_id") String templateId) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.rollbackTemplate(tenantId, actorUserId, templateId);
        writeAudit(tenantId, actorUserId, "TEMPLATE_ROLLBACK", "TEMPLATE", templateId, null);
        return toResourceResponse(updated);
    }

    @PutMapping("/policies/{policy_id}")
    public ResourceResponse updatePolicy(
        @PathVariable("policy_id") String policyId,
        @RequestBody(required = false) Map<String, Object> payload
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.updatePolicy(
            tenantId,
            actorUserId,
            policyId,
            payload == null ? Map.of() : payload
        );
        writeAudit(tenantId, actorUserId, "POLICY_UPDATED", "POLICY", policyId, payload);
        return toResourceResponse(updated);
    }

    @GetMapping("/models")
    public ResourceListResponse listModels(
        @RequestParam(value = "limit", defaultValue = "50") int limit,
        @RequestParam(value = "offset", defaultValue = "0") int offset
    ) {
        UUID tenantId = currentTenantId();
        List<ResourceResponse> items = backofficeAdminService.listModels(tenantId, limit, offset).stream()
            .map(this::toResourceResponse)
            .toList();
        return new ResourceListResponse(items, TraceGuard.requireTraceId());
    }

    @PostMapping("/models")
    public ResponseEntity<ResourceResponse> createModel(@Valid @RequestBody ModelCreateRequest request) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView created = backofficeAdminService.createModel(
            tenantId,
            actorUserId,
            request.provider(),
            request.modelName()
        );
        writeAudit(tenantId, actorUserId, "MODEL_CREATED", "MODEL", created.resourceKey(), request);
        return ResponseEntity.status(HttpStatus.CREATED).body(toResourceResponse(created));
    }

    @PostMapping("/models/{model_id}/activate")
    public ResourceResponse activateModel(@PathVariable("model_id") String modelId) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.activateModel(tenantId, actorUserId, modelId);
        writeAudit(tenantId, actorUserId, "MODEL_ACTIVATED", "MODEL", modelId, null);
        return toResourceResponse(updated);
    }

    @PostMapping("/models/{model_id}/rollback")
    public ResourceResponse rollbackModel(@PathVariable("model_id") String modelId) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.rollbackModel(tenantId, actorUserId, modelId);
        writeAudit(tenantId, actorUserId, "MODEL_ROLLBACK", "MODEL", modelId, null);
        return toResourceResponse(updated);
    }

    @PutMapping("/routing-rules/{rule_id}")
    public ResourceResponse upsertRoutingRule(
        @PathVariable("rule_id") String ruleId,
        @RequestBody(required = false) Map<String, Object> payload
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.upsertRoutingRule(
            tenantId,
            actorUserId,
            ruleId,
            payload == null ? Map.of() : payload
        );
        writeAudit(tenantId, actorUserId, "ROUTING_RULE_UPSERT", "ROUTING_RULE", ruleId, payload);
        return toResourceResponse(updated);
    }

    @PostMapping("/routing-rules/test")
    public RoutingRuleTestResponse testRoutingRule(@RequestBody(required = false) RoutingRuleTestRequest request) {
        UUID tenantId = currentTenantId();
        BackofficeAdminService.RoutingRuleTestView result = backofficeAdminService.testRoutingRule(
            tenantId,
            request == null ? null : request.prompt(),
            request == null ? null : request.ruleId()
        );
        return new RoutingRuleTestResponse(
            result.result(),
            result.matchedRuleId(),
            result.normalizedPrompt(),
            TraceGuard.requireTraceId()
        );
    }

    @PutMapping("/provider-keys/{provider}")
    public ResourceResponse upsertProviderKey(
        @PathVariable("provider") String provider,
        @RequestBody(required = false) ProviderKeyRequest request
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.upsertProviderKey(
            tenantId,
            actorUserId,
            provider,
            request == null ? null : request.secretRef()
        );
        writeAudit(tenantId, actorUserId, "PROVIDER_KEY_UPSERT", "PROVIDER_KEY", provider, request);
        return toResourceResponse(updated);
    }

    @PostMapping("/provider-keys/{provider}/rotate")
    public ResourceResponse rotateProviderKey(@PathVariable("provider") String provider) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.rotateProviderKey(tenantId, actorUserId, provider);
        writeAudit(tenantId, actorUserId, "PROVIDER_KEY_ROTATE", "PROVIDER_KEY", provider, null);
        return toResourceResponse(updated);
    }

    @PostMapping("/providers/{provider_id}/secret-ref")
    public ResourceResponse bindProviderSecretRef(
        @PathVariable("provider_id") String providerId,
        @RequestBody(required = false) ProviderKeyRequest request
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.bindProviderSecretRef(
            tenantId,
            actorUserId,
            providerId,
            request == null ? null : request.secretRef()
        );
        writeAudit(tenantId, actorUserId, "PROVIDER_SECRET_REF_BIND", "PROVIDER_CONFIG", providerId, request);
        return toResourceResponse(updated);
    }

    @GetMapping("/version-bundles")
    public ResourceListResponse listVersionBundles(
        @RequestParam(value = "limit", defaultValue = "50") int limit,
        @RequestParam(value = "offset", defaultValue = "0") int offset
    ) {
        UUID tenantId = currentTenantId();
        List<ResourceResponse> items = backofficeAdminService.listVersionBundles(tenantId, limit, offset).stream()
            .map(this::toResourceResponse)
            .toList();
        return new ResourceListResponse(items, TraceGuard.requireTraceId());
    }

    @PostMapping("/version-bundles/{bundle_id}/activate")
    public ResourceResponse activateVersionBundle(@PathVariable("bundle_id") String bundleId) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.activateVersionBundle(tenantId, actorUserId, bundleId);
        writeAudit(tenantId, actorUserId, "VERSION_BUNDLE_ACTIVATE", "VERSION_BUNDLE", bundleId, null);
        return toResourceResponse(updated);
    }

    @PostMapping("/version-bundles/{bundle_id}/rollback")
    public ResourceResponse rollbackVersionBundle(@PathVariable("bundle_id") String bundleId) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.rollbackVersionBundle(tenantId, actorUserId, bundleId);
        writeAudit(tenantId, actorUserId, "VERSION_BUNDLE_ROLLBACK", "VERSION_BUNDLE", bundleId, null);
        return toResourceResponse(updated);
    }

    @PutMapping("/tools/allowlist/{tool_name}")
    public ResourceResponse upsertToolAllowlist(
        @PathVariable("tool_name") String toolName,
        @RequestBody(required = false) ToolAllowlistRequest request
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.upsertToolAllowlist(
            tenantId,
            actorUserId,
            toolName,
            request != null && request.allowed()
        );
        writeAudit(tenantId, actorUserId, "TOOL_ALLOWLIST_UPDATE", "TOOL_ALLOWLIST", toolName, request);
        return toResourceResponse(updated);
    }

    @PutMapping("/errors/catalog/{error_code}")
    public ResourceResponse upsertErrorCatalog(
        @PathVariable("error_code") String errorCode,
        @RequestBody(required = false) ErrorCatalogRequest request
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.upsertErrorCatalog(
            tenantId,
            actorUserId,
            errorCode,
            request == null ? null : request.message(),
            request == null ? null : request.severity()
        );
        writeAudit(tenantId, actorUserId, "ERROR_CATALOG_UPSERT", "ERROR_CATALOG", errorCode, request);
        return toResourceResponse(updated);
    }

    @PostMapping("/deploy-approvals")
    public ResponseEntity<ResourceResponse> createDeployApproval(
        @RequestBody(required = false) DeployApprovalCreateRequest request
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView created = backofficeAdminService.createDeployApproval(
            tenantId,
            actorUserId,
            request == null ? null : request.bundleId(),
            request == null ? null : request.reason()
        );
        writeAudit(tenantId, actorUserId, "DEPLOY_APPROVAL_CREATE", "DEPLOY_APPROVAL", created.resourceKey(), request);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(toResourceResponse(created));
    }

    @PostMapping("/deploy-approvals/{approval_id}/actions/{action}")
    public ResourceResponse actDeployApproval(
        @PathVariable("approval_id") String approvalId,
        @PathVariable("action") String action
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.actDeployApproval(
            tenantId,
            actorUserId,
            approvalId,
            action
        );
        writeAudit(tenantId, actorUserId, "DEPLOY_APPROVAL_ACTION", "DEPLOY_APPROVAL", approvalId, Map.of("action", action));
        return toResourceResponse(updated);
    }

    @PostMapping("/change-notices/{notice_id}/publish")
    public ResourceResponse publishChangeNotice(
        @PathVariable("notice_id") String noticeId,
        @RequestBody(required = false) ChangeNoticePublishRequest request
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.publishChangeNotice(
            tenantId,
            actorUserId,
            noticeId,
            request == null ? null : request.title(),
            request == null ? null : request.body()
        );
        writeAudit(tenantId, actorUserId, "CHANGE_NOTICE_PUBLISH", "CHANGE_NOTICE", noticeId, request);
        return toResourceResponse(updated);
    }

    private ResourceResponse toResourceResponse(BackofficeAdminService.AdminResourceView view) {
        return new ResourceResponse(
            view.resourceKey(),
            view.status(),
            view.activeFlag(),
            view.payloadJson(),
            view.lastRotatedAt(),
            view.updatedAt(),
            TraceGuard.requireTraceId()
        );
    }

    private void writeAudit(
        UUID tenantId,
        UUID actorUserId,
        String actionType,
        String targetType,
        String targetId,
        Object payload
    ) {
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        auditLogService.write(
            tenantId,
            actionType,
            actorUserId,
            String.join(",", principal.roles()),
            targetType,
            targetId,
            null,
            payload
        );
    }

    private UUID currentTenantId() {
        return UUID.fromString(TenantContext.getTenantId());
    }

    private UUID currentActorUserId() {
        return AuditLogService.toUuidOrNull(PrincipalUtils.currentPrincipal().userId());
    }

    public record ResourceResponse(
        String resourceKey,
        String status,
        boolean activeFlag,
        String payloadJson,
        Instant lastRotatedAt,
        Instant updatedAt,
        String traceId
    ) {
    }

    public record ResourceListResponse(
        List<ResourceResponse> items,
        String traceId
    ) {
    }

    public record TemplateCreateRequest(
        @NotBlank
        String name,
        String body
    ) {
    }

    public record ModelCreateRequest(
        @NotBlank
        String provider,
        @NotBlank
        String modelName
    ) {
    }

    public record RoutingRuleTestRequest(
        String ruleId,
        String prompt
    ) {
    }

    public record RoutingRuleTestResponse(
        String result,
        String matchedRuleId,
        String normalizedPrompt,
        String traceId
    ) {
    }

    public record ProviderKeyRequest(
        String secretRef
    ) {
    }

    public record ToolAllowlistRequest(
        boolean allowed
    ) {
    }

    public record ErrorCatalogRequest(
        String message,
        String severity
    ) {
    }

    public record DeployApprovalCreateRequest(
        String bundleId,
        String reason
    ) {
    }

    public record ChangeNoticePublishRequest(
        String title,
        String body
    ) {
    }
}
