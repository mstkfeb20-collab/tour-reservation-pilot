package com.example.domain;

import java.util.Objects;

public record CancellationAudit(String reserveNo, String operator, Money fee, Money paid, Money refund, Money claim) {
    public CancellationAudit {
        Objects.requireNonNull(reserveNo);
        Objects.requireNonNull(operator);
        Objects.requireNonNull(fee);
        Objects.requireNonNull(paid);
        Objects.requireNonNull(refund);
        Objects.requireNonNull(claim);
    }
}
