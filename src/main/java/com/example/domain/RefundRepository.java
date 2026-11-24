package com.example.domain;

import java.time.LocalDate;

public interface RefundRepository {

    Refund register(
        String reserveNo,
        LocalDate cancelDate,
        Money refundAmount,
        Money cancelFee,
        String operator
    );
}
