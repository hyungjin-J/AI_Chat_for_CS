package com.aichatbot.global.tenant;

public final class TenantContext {

    private static final ThreadLocal<String> TENANT_KEY_HOLDER = new ThreadLocal<>();
    private static final ThreadLocal<String> TENANT_ID_HOLDER = new ThreadLocal<>();

    private TenantContext() {
    }

    public static void setTenantKey(String tenantKey) {
        TENANT_KEY_HOLDER.set(tenantKey);
    }

    public static String getTenantKey() {
        return TENANT_KEY_HOLDER.get();
    }

    public static void setTenantId(String tenantId) {
        TENANT_ID_HOLDER.set(tenantId);
    }

    public static String getTenantId() {
        return TENANT_ID_HOLDER.get();
    }

    public static void clear() {
        TENANT_KEY_HOLDER.remove();
        TENANT_ID_HOLDER.remove();
    }
}
