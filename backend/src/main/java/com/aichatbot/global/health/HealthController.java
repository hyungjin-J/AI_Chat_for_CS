package com.aichatbot.global.health;

import com.aichatbot.global.observability.TraceContext;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

    @GetMapping("/health")
    public Map<String, String> health() {
        // 왜 필요한가: 인프라/모니터링이 빠르게 헬스체크를 할 수 있어야 장애를 조기에 탐지한다.
        return Map.of(
            "status", "UP",
            "trace_id", TraceContext.getTraceId() == null ? "N/A" : TraceContext.getTraceId()
        );
    }
}
