package com.example.domain;

import java.time.LocalDateTime;
import java.util.Objects;

public record Refund(
    String refundNo,
    String reserveNo,
    Money refundAmount,
    Money cancelFee,
    RefundStatus status,
    LocalDateTime createdAt,
    String createdBy,
    LocalDateTime updatedAt,
    String updatedBy
) {
    public Refund {
        Objects.requireNonNull(refundNo);
        Objects.requireNonNull(reserveNo);
        Objects.requireNonNull(refundAmount);
        Objects.requireNonNull(cancelFee);
        Objects.requireNonNull(status);
        Objects.requireNonNull(createdAt);
        Objects.requireNonNull(createdBy);
        Objects.requireNonNull(updatedAt);
        Objects.requireNonNull(updatedBy);
    }
}
