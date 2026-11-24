package com.example.domain;

import java.util.Objects;

public record CancellationAudit(String reserveNo, String operator, Money fee, Money refund) {
    public CancellationAudit {
        Objects.requireNonNull(reserveNo);
        Objects.requireNonNull(operator);
        Objects.requireNonNull(fee);
        Objects.requireNonNull(refund);
    }
}
