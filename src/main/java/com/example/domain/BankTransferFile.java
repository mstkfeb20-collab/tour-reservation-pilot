package com.example.domain;

import java.time.LocalDate;
import java.util.List;
import java.util.Objects;

public record BankTransferFile(
    LocalDate creationDate,
    String accountNumber,
    List<BankTransferDetail> details,
    Money totalAmount
) {
    public BankTransferFile {
        Objects.requireNonNull(creationDate);
        Objects.requireNonNull(accountNumber);
        details = List.copyOf(details);
        Objects.requireNonNull(totalAmount);
    }
}
