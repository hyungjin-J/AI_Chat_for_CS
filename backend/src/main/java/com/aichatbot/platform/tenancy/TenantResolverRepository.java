package com.aichatbot.platform.tenancy;

import com.aichatbot.platform.tenancy.domain.mapper.TenantResolverMapper;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class TenantResolverRepository {

    private final TenantResolverMapper tenantResolverMapper;

    public TenantResolverRepository(TenantResolverMapper tenantResolverMapper) {
        this.tenantResolverMapper = tenantResolverMapper;
    }

    public Optional<UUID> findTenantIdByKey(String tenantKey) {
        String tenantId = tenantResolverMapper.findTenantIdByKey(tenantKey);
        if (tenantId == null) {
            return Optional.empty();
        }
        return Optional.of(UUID.fromString(tenantId));
    }
}

