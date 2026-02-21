package com.aichatbot.auth.application;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.security.UserPrincipal;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;
import java.util.List;
import java.util.UUID;
import javax.crypto.SecretKey;
import org.springframework.stereotype.Component;

@Component
public class JwtTokenProvider {

    private final AppProperties appProperties;
    private final SecretKey secretKey;

    public JwtTokenProvider(AppProperties appProperties) {
        this.appProperties = appProperties;
        this.secretKey = Keys.hmacShaKeyFor(normalizeSecret(appProperties.getJwt().getSecret()));
    }

    public String generateAccessToken(UserPrincipal principal, String traceId) {
        return generateAccessToken(principal, traceId, null);
    }

    public String generateAccessToken(UserPrincipal principal, String traceId, UUID sessionFamilyId) {
        Instant now = Instant.now();
        Instant expiry = now.plusSeconds(appProperties.getJwt().getAccessExpirationSec());
        io.jsonwebtoken.JwtBuilder builder = Jwts.builder()
            .setSubject(principal.userId())
            .claim("tenant_id", principal.tenantId())
            .claim("login_id", principal.loginId())
            .claim("roles", principal.roles())
            .claim("permission_version", principal.permissionVersion())
            .claim("admin_level", principal.adminLevel())
            .claim("token_type", "access")
            .claim("trace_id", traceId)
            .setIssuedAt(Date.from(now))
            .setExpiration(Date.from(expiry));
        if (sessionFamilyId != null) {
            builder.claim("session_family_id", sessionFamilyId.toString());
        }
        return builder.signWith(secretKey, SignatureAlgorithm.HS256).compact();
    }

    public String generateRefreshToken(
        UserPrincipal principal,
        String traceId,
        UUID refreshJti,
        UUID sessionFamilyId
    ) {
        Instant now = Instant.now();
        Instant expiry = now.plusSeconds(appProperties.getJwt().getRefreshExpirationSec());
        return Jwts.builder()
            .setSubject(principal.userId())
            .setId(refreshJti.toString())
            .claim("tenant_id", principal.tenantId())
            .claim("login_id", principal.loginId())
            .claim("roles", principal.roles())
            .claim("permission_version", principal.permissionVersion())
            .claim("admin_level", principal.adminLevel())
            .claim("token_type", "refresh")
            .claim("trace_id", traceId)
            .claim("session_family_id", sessionFamilyId.toString())
            .setIssuedAt(Date.from(now))
            .setExpiration(Date.from(expiry))
            .signWith(secretKey, SignatureAlgorithm.HS256)
            .compact();
    }

    public Claims parseClaims(String token) {
        return Jwts.parser()
            .setSigningKey(secretKey)
            .build()
            .parseClaimsJws(token)
            .getBody();
    }

    @SuppressWarnings("unchecked")
    public UserPrincipal toPrincipal(Claims claims) {
        String userId = claims.getSubject();
        String tenantId = claims.get("tenant_id", String.class);
        String loginId = claims.get("login_id", String.class);
        List<String> roles = claims.get("roles", List.class);
        Number permissionVersion = claims.get("permission_version", Number.class);
        String adminLevel = claims.get("admin_level", String.class);
        return new UserPrincipal(
            userId,
            tenantId,
            loginId,
            roles == null ? List.of() : List.copyOf(roles),
            permissionVersion == null ? 1L : permissionVersion.longValue(),
            adminLevel == null ? "MANAGER" : adminLevel
        );
    }

    public String hashToken(String rawToken) {
        return sha256(rawToken);
    }

    public String hashJti(String rawJti) {
        return sha256(rawJti);
    }

    private String sha256(String raw) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest((raw == null ? "" : raw).getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(hash);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 not available", exception);
        }
    }

    private byte[] normalizeSecret(String rawSecret) {
        String secret = rawSecret == null ? "" : rawSecret;
        if (secret.length() < 32) {
            StringBuilder builder = new StringBuilder(secret);
            while (builder.length() < 32) {
                builder.append('x');
            }
            secret = builder.toString();
        }
        return secret.getBytes(StandardCharsets.UTF_8);
    }
}
