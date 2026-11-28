package com.example.domain;

import java.time.LocalDateTime;
import java.util.Objects;

public record Claim(
    String claimNo,
    String reserveNo,
    Money claimAmount,
    Money cancelFee,
    Money paidAmount,
    ClaimStatus status,
    LocalDateTime createdAt,
    String createdBy,
    LocalDateTime updatedAt,
    String updatedBy
) {
    public Claim {
        Objects.requireNonNull(claimNo);
        Objects.requireNonNull(reserveNo);
        Objects.requireNonNull(claimAmount);
        Objects.requireNonNull(cancelFee);
        Objects.requireNonNull(paidAmount);
        Objects.requireNonNull(status);
        Objects.requireNonNull(createdAt);
        Objects.requireNonNull(createdBy);
        Objects.requireNonNull(updatedAt);
        Objects.requireNonNull(updatedBy);
        if (claimAmount.equals(Money.zero()) || cancelFee.equals(Money.zero())) {
            throw new IllegalArgumentException("請求額と取消料は0円より大きくしてください");
        }
    }
}
