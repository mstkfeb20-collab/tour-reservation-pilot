package com.example.domain;

import java.time.LocalDate;

public interface RefundRepository {

    /** A failed registration must leave no refund for the reservation. */
    Refund register(
        String reserveNo,
        LocalDate cancelDate,
        Money refundAmount,
        Money cancelFee,
        String operator
    );

    void rollbackRegistration(String reserveNo);
}
