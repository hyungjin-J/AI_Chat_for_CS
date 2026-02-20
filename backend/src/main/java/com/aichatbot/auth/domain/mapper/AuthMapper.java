package com.aichatbot.auth.domain.mapper;

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

    int saveAuthSession(@Param("id") UUID id,
                        @Param("tenantId") UUID tenantId,
                        @Param("userId") UUID userId,
                        @Param("tokenHash") String tokenHash,
                        @Param("expiresAt") Instant expiresAt);

    Integer countValidSessionByTokenHash(@Param("tokenHash") String tokenHash);

    int deleteSessionByTokenHash(@Param("tokenHash") String tokenHash);
}
