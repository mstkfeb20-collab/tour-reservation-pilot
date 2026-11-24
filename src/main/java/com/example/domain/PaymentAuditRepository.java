package com.example.domain;

public interface PaymentAuditRepository {

    void record(String operator, String inquiryNo, Money amount);
}
