package com.aichatbot.billing.domain.model;

public record TenantPlan(
    String planCode,
    String name,
    String description
) {
}

