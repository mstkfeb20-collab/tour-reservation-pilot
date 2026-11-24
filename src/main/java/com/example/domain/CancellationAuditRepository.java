package com.example.domain;

public interface CancellationAuditRepository {

    void record(CancellationAudit entry);

    void remove(CancellationAudit entry);
}
