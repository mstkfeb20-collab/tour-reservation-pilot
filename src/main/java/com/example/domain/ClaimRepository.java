package com.example.domain;

import java.time.LocalDate;

public interface ClaimRepository {
    /** A failed registration must leave no claim for the reservation. */
    Claim register(String reserveNo, LocalDate cancelDate, Money claimAmount, Money cancelFee, Money paidAmount, String operator);

    void rollbackRegistration(String reserveNo);
}
