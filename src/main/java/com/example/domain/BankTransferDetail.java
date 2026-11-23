package com.example.domain;

import java.time.LocalDate;
import java.util.Objects;

public record BankTransferDetail(
    String inquiryNo,
    LocalDate accountDate,
    LocalDate startDate,
    Money amount,
    String payerName,
    String cancellationCode,
    String ediInformation
) {
    public BankTransferDetail {
        Objects.requireNonNull(inquiryNo);
        Objects.requireNonNull(accountDate);
        Objects.requireNonNull(startDate);
        Objects.requireNonNull(amount);
        Objects.requireNonNull(payerName);
        Objects.requireNonNull(cancellationCode);
        Objects.requireNonNull(ediInformation);
    }
}
