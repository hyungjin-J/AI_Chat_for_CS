package com.aichatbot.contexts.billing.domain.mapper;

import com.aichatbot.contexts.billing.domain.model.CostRateCard;
import java.time.Instant;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface RateCardMapper {

    int insert(@Param("rateCardCode") String rateCardCode,
               @Param("providerCode") String providerCode,
               @Param("modelCode") String modelCode,
               @Param("inputTokenCostPer1k") java.math.BigDecimal inputTokenCostPer1k,
               @Param("outputTokenCostPer1k") java.math.BigDecimal outputTokenCostPer1k,
               @Param("toolCallCost") java.math.BigDecimal toolCallCost,
               @Param("effectiveFrom") Instant effectiveFrom,
               @Param("effectiveTo") Instant effectiveTo);

    CostRateCard findApplicable(@Param("providerCode") String providerCode,
                                @Param("modelCode") String modelCode,
                                @Param("at") Instant at);

    List<CostRateCard> findAll();

    int deleteAll();
}
