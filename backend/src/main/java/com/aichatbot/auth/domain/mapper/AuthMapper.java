package com.aichatbot.auth.domain.mapper;

import com.aichatbot.auth.domain.AuthUserProjection;
import java.time.Instant;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface AuthMapper {

    AuthUserProjection findActiveUserByTenantAndLoginId(@Param("tenantKey") String tenantKey,
                                                         @Param("loginId") String loginId);

    AuthUserProjection findActiveUserById(@Param("userId") String userId);

    List<String> findRolesByUserId(@Param("userId") String userId);

    int saveAuthSession(@Param("id") String id,
                        @Param("tenantId") String tenantId,
                        @Param("userId") String userId,
                        @Param("tokenHash") String tokenHash,
                        @Param("expiresAt") Instant expiresAt);

    Integer countValidSessionByTokenHash(@Param("tokenHash") String tokenHash);

    int deleteSessionByTokenHash(@Param("tokenHash") String tokenHash);
}
