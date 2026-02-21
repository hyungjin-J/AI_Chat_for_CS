package com.aichatbot.auth.domain.mapper;

import com.aichatbot.auth.domain.AuthSessionRecord;
import com.aichatbot.auth.domain.AuthSessionOverview;
import com.aichatbot.auth.domain.AuthUserProjection;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface AuthMapper {

    AuthUserProjection findActiveUserByTenantAndLoginId(@Param("tenantKey") String tenantKey,
                                                         @Param("loginId") String loginId);

    AuthUserProjection findActiveUserById(@Param("userId") UUID userId);

    List<String> findRolesByUserId(@Param("userId") UUID userId);

    int insertAuthSession(@Param("id") UUID id,
                          @Param("tenantId") UUID tenantId,
                          @Param("userId") UUID userId,
                          @Param("sessionFamilyId") UUID sessionFamilyId,
                          @Param("tokenHash") String tokenHash,
                          @Param("refreshJtiHash") String refreshJtiHash,
                          @Param("parentRefreshJtiHash") String parentRefreshJtiHash,
                          @Param("expiresAt") Instant expiresAt,
                          @Param("clientType") String clientType,
                          @Param("createdIp") String createdIp,
                          @Param("traceId") UUID traceId);

    AuthSessionRecord findSessionByTokenHash(@Param("tokenHash") String tokenHash);

    int consumeRefreshSessionByTokenHash(@Param("tokenHash") String tokenHash,
                                         @Param("consumedAt") Instant consumedAt,
                                         @Param("consumedIp") String consumedIp);

    int revokeSessionFamily(@Param("sessionFamilyId") UUID sessionFamilyId,
                            @Param("revokedAt") Instant revokedAt,
                            @Param("reason") String reason);

    int revokeSessionByTokenHash(@Param("tokenHash") String tokenHash,
                                 @Param("revokedAt") Instant revokedAt,
                                 @Param("reason") String reason);

    List<AuthSessionOverview> findActiveSessionsByUser(@Param("tenantId") UUID tenantId,
                                                       @Param("userId") UUID userId,
                                                       @Param("nowUtc") Instant nowUtc);

    int revokeSessionFamilyByUser(@Param("tenantId") UUID tenantId,
                                  @Param("userId") UUID userId,
                                  @Param("sessionFamilyId") UUID sessionFamilyId,
                                  @Param("revokedAt") Instant revokedAt,
                                  @Param("reason") String reason,
                                  @Param("revokedBySessionId") UUID revokedBySessionId);

    int revokeOtherSessionFamiliesByUser(@Param("tenantId") UUID tenantId,
                                         @Param("userId") UUID userId,
                                         @Param("currentSessionFamilyId") UUID currentSessionFamilyId,
                                         @Param("revokedAt") Instant revokedAt,
                                         @Param("reason") String reason,
                                         @Param("revokedBySessionId") UUID revokedBySessionId);

    int incrementFailedLogin(@Param("userId") UUID userId,
                             @Param("failedAt") Instant failedAt,
                             @Param("lockUntil") Instant lockUntil,
                             @Param("lockoutThreshold") int lockoutThreshold);

    int resetFailedLogin(@Param("userId") UUID userId);

    int clearExpiredLock(@Param("userId") UUID userId);

    int incrementPermissionVersionByTenant(@Param("tenantId") UUID tenantId);

    Long findPermissionVersionByUserId(@Param("userId") UUID userId);
}
