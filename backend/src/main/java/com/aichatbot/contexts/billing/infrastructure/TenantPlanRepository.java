package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.domain.mapper.TenantPlanMapper;
import com.aichatbot.contexts.billing.domain.model.TenantPlan;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

@Repository
public class TenantPlanRepository {

    private final TenantPlanMapper tenantPlanMapper;
    private final String persistenceMode;
    private final Map<String, TenantPlan> planMap = new ConcurrentHashMap<>();

    public TenantPlanRepository() {
        this.tenantPlanMapper = null;
        this.persistenceMode = "memory";
    }

    @Autowired
    public TenantPlanRepository(
        @Autowired(required = false) TenantPlanMapper tenantPlanMapper,
        @Value("${app.billing.persistence.mode:mybatis}") String persistenceMode
    ) {
        this.tenantPlanMapper = tenantPlanMapper;
        this.persistenceMode = persistenceMode;
    }

    public void save(TenantPlan tenantPlan) {
        if (useMapperPersistence()) {
            tenantPlanMapper.deleteByCode(tenantPlan.planCode());
            tenantPlanMapper.insert(tenantPlan.planCode(), tenantPlan.name(), tenantPlan.description());
            return;
        }
        planMap.put(tenantPlan.planCode(), tenantPlan);
    }

    public Optional<TenantPlan> findByCode(String planCode) {
        if (useMapperPersistence()) {
            return Optional.ofNullable(tenantPlanMapper.findByCode(planCode));
        }
        return Optional.ofNullable(planMap.get(planCode));
    }

    public void clear() {
        if (useMapperPersistence()) {
            tenantPlanMapper.deleteAll();
            return;
        }
        planMap.clear();
    }

    private boolean useMapperPersistence() {
        return tenantPlanMapper != null && "mybatis".equalsIgnoreCase(persistenceMode);
    }
}


