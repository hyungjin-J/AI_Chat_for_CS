package com.aichatbot.global.idempotency;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class IdempotencyServiceTest {

    @Test
    void shouldReturn409WhenDuplicateRequestArrivesDuringProcessing() throws Exception {
        IdempotencyService idempotencyService = new IdempotencyService(
            new InMemoryIdempotencyRecordStore(),
            new AppProperties()
        );
        CountDownLatch started = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);

        ExecutorService executor = Executors.newFixedThreadPool(2);
        Future<String> first = executor.submit(() -> idempotencyService.execute("scope", "same-key", () -> {
            started.countDown();
            try {
                release.await();
            } catch (InterruptedException interruptedException) {
                throw new RuntimeException(interruptedException);
            }
            return "ok";
        }));

        started.await();

        assertThatThrownBy(() -> idempotencyService.execute("scope", "same-key", () -> "second"))
            .isInstanceOf(ApiException.class)
            .satisfies(exception -> assertThat(((ApiException) exception).errorCode()).isEqualTo("API-003-409"));

        release.countDown();
        assertThat(first.get()).isEqualTo("ok");
        executor.shutdownNow();
    }

    @Test
    void shouldReturn409WhenDuplicateRequestArrivesAfterCompletion() {
        IdempotencyService idempotencyService = new IdempotencyService(
            new InMemoryIdempotencyRecordStore(),
            new AppProperties()
        );

        String first = idempotencyService.execute("scope", "same-key", () -> "first");

        assertThat(first).isEqualTo("first");
        assertThatThrownBy(() -> idempotencyService.execute("scope", "same-key", () -> "second"))
            .isInstanceOf(ApiException.class)
            .satisfies(exception -> assertThat(((ApiException) exception).errorCode()).isEqualTo("API-003-409"));
    }
}
