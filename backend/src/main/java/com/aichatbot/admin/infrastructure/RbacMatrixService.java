package com.aichatbot.admin.infrastructure;

import com.aichatbot.auth.infrastructure.AuthRepository;
import java.time.Clock;
import java.time.Instant;
import java.util.Locale;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class RbacMatrixService {

    private final RbacMatrixRepository rbacMatrixRepository;
    private final AuthRepository authRepository;
    private final Clock clock;

    @Autowired
    public RbacMatrixService(RbacMatrixRepository rbacMatrixRepository, AuthRepository authRepository) {
        this(rbacMatrixRepository, authRepository, Clock.systemUTC());
    }

    RbacMatrixService(RbacMatrixRepository rbacMatrixRepository, AuthRepository authRepository, Clock clock) {
        this.rbacMatrixRepository = rbacMatrixRepository;
        this.authRepository = authRepository;
        this.clock = clock;
    }

    public long upsertAndBumpPermissionVersion(
        UUID tenantId,
        String resourceKey,
        String roleCode,
        String adminLevel,
        boolean allowed,
        UUID updatedBy
    ) {
        long nextPermissionVersion = Instant.now(clock).toEpochMilli();
        rbacMatrixRepository.upsert(
            tenantId,
            normalize(resourceKey),
            normalize(roleCode),
            normalize(adminLevel),
            allowed,
            nextPermissionVersion,
            updatedBy,
            Instant.now(clock)
        );
        authRepository.incrementPermissionVersionByTenant(tenantId);
        return nextPermissionVersion;
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toUpperCase(Locale.ROOT);
    }
}
