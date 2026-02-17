package com.aichatbot.billing.infrastructure;

import com.aichatbot.billing.domain.model.TenantPlan;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Repository;

@Repository
public class TenantPlanRepository {

    private final Map<String, TenantPlan> planMap = new ConcurrentHashMap<>();

    public void save(TenantPlan tenantPlan) {
        planMap.put(tenantPlan.planCode(), tenantPlan);
    }

    public Optional<TenantPlan> findByCode(String planCode) {
        return Optional.ofNullable(planMap.get(planCode));
    }

    public void clear() {
        planMap.clear();
    }
}

