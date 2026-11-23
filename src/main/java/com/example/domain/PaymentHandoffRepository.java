package com.example.domain;

import java.time.LocalDate;

public interface PaymentHandoffRepository {

    void enqueue(String reserveNo, LocalDate paidDate);
}
