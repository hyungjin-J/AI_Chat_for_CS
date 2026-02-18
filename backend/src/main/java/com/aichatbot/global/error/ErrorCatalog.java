package com.aichatbot.global.error;

import java.util.Map;

public final class ErrorCatalog {

    private static final Map<String, String> MESSAGES = Map.ofEntries(
        Map.entry("SEC-001-401", "인증이 만료되었습니다. 다시 로그인해 주세요."),
        Map.entry("SEC-002-403", "해당 기능에 접근 권한이 없습니다."),
        Map.entry("SYS-002-403", "허용되지 않은 테넌트 또는 도메인입니다."),
        Map.entry("API-003-409", "동일 요청이 이미 처리 중입니다."),
        Map.entry("API-003-422", "입력값 형식이 올바르지 않습니다."),
        Map.entry("API-008-429-BUDGET", "요청 한도를 초과했습니다. 잠시 후 재시도해 주세요."),
        Map.entry("API-008-429-SSE", "동시 스트리밍 연결 수를 초과했습니다."),
        Map.entry("AI-009-422-SCHEMA", "응답 형식 검증에 실패하여 전송할 수 없습니다."),
        Map.entry("AI-009-409-CITATION", "근거 인용이 누락되어 전송할 수 없습니다."),
        Map.entry("AI-009-409-EVIDENCE", "근거 점수가 기준에 미달하여 전송할 수 없습니다."),
        Map.entry("AI-009-200-SAFE", "추가 확인이 필요하여 안전 응답으로 전환했습니다."),
        Map.entry("RAG-002-422-POLICY", "정책 위반으로 전송이 차단되었습니다."),
        Map.entry("SYS-004-409-TRACE", "요청 추적 정보가 누락되어 처리할 수 없습니다."),
        Map.entry("SYS-003-500", "일시적인 시스템 오류가 발생했습니다."),
        Map.entry("SYS-003-503", "외부 연동 서비스가 일시적으로 불안정합니다.")
    );

    private ErrorCatalog() {
    }

    public static String messageOf(String code) {
        return MESSAGES.getOrDefault(code, "요청 처리 중 오류가 발생했습니다.");
    }
}
